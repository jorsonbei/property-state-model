from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .shadow_runner import build_fresh_rule_record, compare_rule_and_candidate, load_jsonl
from .state_encoder_candidate import TARGETS, extract_signals, predict_record, train_candidate


VERSION_TAG = "V0.20"
DATASET_STEM = "psm_v0.20"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled candidate-assisted mode with rule hard override.")
    parser.add_argument("--stem", default=DATASET_STEM)
    parser.add_argument("--version-tag", default=VERSION_TAG)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("assist_out"))
    parser.add_argument("--shadow-metrics", type=Path, default=None)
    parser.add_argument("--fail-on-override", action="store_true")
    args = parser.parse_args()
    if args.dataset is None:
        args.dataset = Path(f"state_dataset_out/{args.stem}_state_encoder.jsonl")
    if args.shadow_metrics is None:
        args.shadow_metrics = Path(f"shadow_out/{args.stem}_shadow_metrics.json")

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    model = train_candidate(records, args.stem)
    rows = []
    ledger_events = []
    for record in records:
        fresh_record = build_fresh_rule_record(record)
        prediction_item = predict_record(model, fresh_record)
        candidate = prediction_item["prediction"]
        events = compare_rule_and_candidate(fresh_record, candidate)
        final_labels = dict(fresh_record["labels"])
        override_applied = bool(events)
        signals = extract_signals(fresh_record)
        abstention_evidence = build_abstention_evidence(fresh_record, candidate, signals, events)
        row = {
            "record_id": fresh_record["record_id"],
            "split": fresh_record["split"],
            "domain": fresh_record["input"]["domain"],
            "signature": prediction_item["signature"],
            "signals": signals,
            "rule": fresh_record["labels"],
            "candidate": candidate,
            "final": final_labels,
            "override_applied": override_applied,
            "assist_mode": "rule_only" if abstention_evidence["rule_only_mode"] else "candidate_assisted_guarded",
            "abstention_evidence": abstention_evidence,
            "policy": "rule_hard_override_with_abstention",
            "events": [with_override_context(event) for event in events],
        }
        rows.append(row)
        ledger_events.extend(row["events"])

    metrics = build_metrics(rows, ledger_events)
    drift_metrics = build_drift_metrics(rows, ledger_events)
    shadow_metrics = load_shadow_metrics(args.shadow_metrics)
    promotion = build_promotion_decision(metrics, drift_metrics, shadow_metrics, args.shadow_metrics, args.stem)

    rows_path = args.outdir / f"{args.stem}_candidate_assisted_predictions.jsonl"
    ledger_path = args.outdir / f"{args.stem}_candidate_assisted_override_ledger.jsonl"
    metrics_path = args.outdir / f"{args.stem}_candidate_assisted_metrics.json"
    drift_path = args.outdir / f"{args.stem}_candidate_assisted_drift_metrics.json"
    promotion_path = args.outdir / f"{args.stem}_promotion_decision.json"
    report_path = args.outdir / f"PSM_{args.version_tag}_Candidate_Assisted_Report.md"
    drift_report_path = args.outdir / f"PSM_{args.version_tag}_Candidate_Assisted_Drift_Report.md"
    promotion_report_path = args.outdir / f"PSM_{args.version_tag}_Promotion_Report.md"

    rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    ledger_path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in ledger_events), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    drift_path.write_text(json.dumps(drift_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    promotion_path.write_text(json.dumps(promotion, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(metrics, rows_path, ledger_path, drift_path, args.version_tag), encoding="utf-8")
    drift_report_path.write_text(build_drift_report(drift_metrics, rows_path, ledger_path, args.version_tag), encoding="utf-8")
    promotion_report_path.write_text(
        build_promotion_report(promotion, metrics_path, drift_path, args.shadow_metrics, args.version_tag),
        encoding="utf-8",
    )

    print(f"records: {metrics['records']}")
    print(f"override_events: {metrics['override_events']}")
    print(f"blocking_events: {metrics['blocking_events']}")
    print(f"rule_only_records: {metrics['rule_only_records']}")
    print(f"drift_present: {drift_metrics['drift_present']}")
    print(f"candidate_assisted_clean: {metrics['candidate_assisted_clean']}")
    print(f"rule_replacement_allowed: {promotion['rule_replacement_allowed']}")
    print(f"ledger: {ledger_path}")
    print(f"report: {report_path}")
    print(f"drift_report: {drift_report_path}")
    print(f"promotion_report: {promotion_report_path}")
    if args.fail_on_override and not metrics["candidate_assisted_clean"]:
        raise SystemExit(1)


def with_override_context(event: dict) -> dict:
    result = dict(event)
    result["override_applied"] = True
    result["final_source"] = "rule_pipeline"
    result["candidate_source"] = "state_encoder_candidate"
    return result


def build_abstention_evidence(record: dict, candidate: dict, signals: list[str], events: list[dict]) -> dict:
    labels = record["labels"]
    input_data = record["input"]
    missing_evidence = collect_missing_evidence(input_data)
    external_judges = list(input_data.get("external_judges_observed", []))
    reasons: list[str] = []

    if labels["q_status"] != "pass":
        reasons.append("q_status_not_pass")
    if labels["risk_level"] in {"high", "critical"}:
        reasons.append("high_or_critical_risk")
    if labels["bsigma_status"] == "suspect":
        reasons.append("bsigma_suspect")
    if external_judges and labels["risk_level"] in {"high", "critical"}:
        reasons.append("external_judge_required")
    if missing_evidence and labels["risk_level"] in {"high", "critical"}:
        reasons.append("critical_missing_evidence")
    if events:
        reasons.append("candidate_disagreement")

    rule_only_mode = bool(reasons)
    return {
        "rule_only_mode": rule_only_mode,
        "mode_reason": sorted(set(reasons)) or ["guarded_candidate_allowed"],
        "missing_evidence_count": len(missing_evidence),
        "missing_evidence_sample": missing_evidence[:8],
        "external_judges": external_judges,
        "signals": signals,
        "candidate_targets_present": sorted(candidate),
    }


def collect_missing_evidence(input_data: dict) -> list[str]:
    values: list[str] = []
    phi_state = input_data.get("phi_state", {})
    delta_sigma = input_data.get("delta_sigma", {})
    eta = input_data.get("eta", {})
    values.extend(str(item) for item in phi_state.get("unknowns", []))
    values.extend(str(item) for item in delta_sigma.get("missing_pressure_data", []))
    values.extend(str(item) for item in eta.get("uncertainties", []))
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def build_metrics(rows: list[dict], events: list[dict]) -> dict:
    event_types = Counter(event["event_type"] for event in events)
    severities = Counter(event["severity"] for event in events)
    split_events = Counter(event["split"] for event in events)
    domain_events = Counter(event["domain"] for event in events)
    unsafe_lower = sum(1 for event in events if event.get("unsafe_lower"))
    records_with_overrides = len({event["record_id"] for event in events})
    rule_only_records = sum(1 for row in rows if row["abstention_evidence"]["rule_only_mode"])
    missing_evidence_records = sum(1 for row in rows if row["abstention_evidence"]["missing_evidence_count"] > 0)
    abstention_reasons = Counter(
        reason
        for row in rows
        for reason in row["abstention_evidence"]["mode_reason"]
        if reason != "guarded_candidate_allowed"
    )
    rule_only_by_domain = Counter(row["domain"] for row in rows if row["abstention_evidence"]["rule_only_mode"])
    return {
        "records": len(rows),
        "clean_records": len(rows) - records_with_overrides,
        "records_with_overrides": records_with_overrides,
        "override_events": len(events),
        "blocking_events": severities.get("blocking", 0),
        "review_events": severities.get("review", 0),
        "unsafe_lower_predictions": unsafe_lower,
        "missing_bsigma_labels": event_types.get("missing_bsigma_label", 0),
        "extra_bsigma_labels": event_types.get("extra_bsigma_label", 0),
        "target_mismatches": event_types.get("target_mismatch", 0),
        "event_types": dict(sorted(event_types.items())),
        "events_by_split": dict(sorted(split_events.items())),
        "events_by_domain": dict(sorted(domain_events.items())),
        "candidate_assisted_clean": len(events) == 0,
        "rule_hard_override_enabled": True,
        "rule_labels_authoritative": True,
        "final_rule_overrides": records_with_overrides,
        "rule_only_records": rule_only_records,
        "candidate_assisted_guarded_records": len(rows) - rule_only_records,
        "records_with_missing_evidence": missing_evidence_records,
        "abstention_reasons": dict(sorted(abstention_reasons.items())),
        "rule_only_by_domain": dict(sorted(rule_only_by_domain.items())),
        "rule_replacement_allowed": False,
    }


def build_drift_metrics(rows: list[dict], events: list[dict]) -> dict:
    records = len(rows)
    records_by_domain = Counter(row["domain"] for row in rows)
    records_by_signal = Counter(signal for row in rows for signal in row["signals"])
    rule_bsigma_by_label = Counter(label for row in rows for label in row["rule"]["bsigma_risks"])
    event_types = Counter(event["event_type"] for event in events)
    events_by_domain = Counter(event["domain"] for event in events)
    events_by_domain_target = Counter(f"{event['domain']}:{event['target']}" for event in events)
    target_mismatches_by_target = Counter(event["target"] for event in events if event["event_type"] == "target_mismatch")
    missing_bsigma_by_label = Counter(event["label"] for event in events if event["event_type"] == "missing_bsigma_label")
    extra_bsigma_by_label = Counter(event["label"] for event in events if event["event_type"] == "extra_bsigma_label")
    row_by_id = {row["record_id"]: row for row in rows}
    events_by_signal = Counter()
    for event in events:
        for signal in row_by_id[event["record_id"]]["signals"]:
            events_by_signal[f"{signal}:{event['event_type']}"] += 1

    target_match_rates = {
        target: round(sum(1 for row in rows if row["rule"][target] == row["candidate"][target]) / records, 3) if records else 0.0
        for target in TARGETS
    }
    bsigma_exact_match = (
        round(
            sum(1 for row in rows if set(row["rule"]["bsigma_risks"]) == set(row["candidate"]["bsigma_risks"])) / records,
            3,
        )
        if records
        else 0.0
    )
    return {
        "records": records,
        "ledger_events": len(events),
        "drift_present": bool(events),
        "target_match_rates": target_match_rates,
        "bsigma_exact_match": bsigma_exact_match,
        "records_by_domain": dict(sorted(records_by_domain.items())),
        "records_by_signal": dict(sorted(records_by_signal.items())),
        "rule_bsigma_by_label": dict(sorted(rule_bsigma_by_label.items())),
        "event_types": dict(sorted(event_types.items())),
        "events_by_domain": dict(sorted(events_by_domain.items())),
        "events_by_domain_target": dict(sorted(events_by_domain_target.items())),
        "events_by_signal": dict(sorted(events_by_signal.items())),
        "target_mismatches_by_target": dict(sorted(target_mismatches_by_target.items())),
        "missing_bsigma_by_label": dict(sorted(missing_bsigma_by_label.items())),
        "extra_bsigma_by_label": dict(sorted(extra_bsigma_by_label.items())),
    }


def load_shadow_metrics(path: Path) -> dict:
    if not path.exists():
        return {"available": False, "replacement_boundary_passed": False, "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["available"] = True
    data["path"] = str(path)
    return data


def build_promotion_decision(metrics: dict, drift_metrics: dict, shadow_metrics: dict, shadow_path: Path, dataset_stem: str = DATASET_STEM) -> dict:
    shadow_clean = bool(shadow_metrics.get("available") and shadow_metrics.get("replacement_boundary_passed"))
    candidate_assisted_clean = bool(metrics["candidate_assisted_clean"])
    drift_clean = not drift_metrics["drift_present"]
    return {
        "version": dataset_stem,
        "shadow_metrics_path": str(shadow_path),
        "shadow_clean": shadow_clean,
        "candidate_assisted_clean": candidate_assisted_clean,
        "candidate_drift_clean": drift_clean,
        "rule_replacement_allowed": False,
        "candidate_assisted_mode_allowed": shadow_clean and candidate_assisted_clean and drift_clean,
        "next_allowed_stage": "continue candidate-assisted stress and active-learning expansion; do not replace rule pipeline",
        "hard_boundaries": [
            "Rule-derived labels remain authoritative.",
            "A clean shadow or assisted ledger does not permit rule replacement in V0.x.",
            "Any override event must be treated as candidate feedback, not as a user-visible final label.",
            "Records with critical missing evidence route to rule-only mode.",
        ],
    }


def build_report(metrics: dict, rows_path: Path, ledger_path: Path, drift_path: Path, version_tag: str = VERSION_TAG) -> str:
    lines = [
        f"# PSM {version_tag} Candidate-Assisted Report",
        "",
        "## Summary",
        "",
        f"- Records: {metrics['records']}",
        f"- Clean records: {metrics['clean_records']}",
        f"- Records with overrides: {metrics['records_with_overrides']}",
        f"- Override events: {metrics['override_events']}",
        f"- Blocking events: {metrics['blocking_events']}",
        f"- Review events: {metrics['review_events']}",
        f"- Unsafe lower predictions: {metrics['unsafe_lower_predictions']}",
        f"- Missing B_sigma labels: {metrics['missing_bsigma_labels']}",
        f"- Extra B_sigma labels: {metrics['extra_bsigma_labels']}",
        f"- Target mismatches: {metrics['target_mismatches']}",
        f"- Candidate-assisted clean: {metrics['candidate_assisted_clean']}",
        f"- Rule-only records: {metrics['rule_only_records']}",
        f"- Candidate-assisted guarded records: {metrics['candidate_assisted_guarded_records']}",
        f"- Records with missing evidence: {metrics['records_with_missing_evidence']}",
        f"- Rule replacement allowed: {metrics['rule_replacement_allowed']}",
        f"- Predictions: `{rows_path}`",
        f"- Override ledger: `{ledger_path}`",
        f"- Drift metrics: `{drift_path}`",
        "",
        "## Distributions",
        "",
        f"- Event types: {metrics['event_types']}",
        f"- Events by split: {metrics['events_by_split']}",
        f"- Events by domain: {metrics['events_by_domain']}",
        f"- Abstention reasons: {metrics['abstention_reasons']}",
        f"- Rule-only by domain: {metrics['rule_only_by_domain']}",
        "",
        "## Boundary",
        "",
        "- Candidate predictions are allowed only as an internal auxiliary signal.",
        "- Final labels always come from the executable rule pipeline.",
        "- Any candidate disagreement is recorded as an override event.",
        "- High-risk or critically under-evidenced records route to rule-only mode.",
    ]
    return "\n".join(lines)


def build_drift_report(drift_metrics: dict, rows_path: Path, ledger_path: Path, version_tag: str = VERSION_TAG) -> str:
    lines = [
        f"# PSM {version_tag} Candidate-Assisted Drift Report",
        "",
        "## Summary",
        "",
        f"- Records: {drift_metrics['records']}",
        f"- Ledger events: {drift_metrics['ledger_events']}",
        f"- Drift present: {drift_metrics['drift_present']}",
        f"- B_sigma exact match: {drift_metrics['bsigma_exact_match']}",
        f"- Predictions: `{rows_path}`",
        f"- Override ledger: `{ledger_path}`",
        "",
        "## Target Match Rates",
        "",
    ]
    lines.extend(f"- {target}: {rate}" for target, rate in drift_metrics["target_match_rates"].items())
    lines.extend(
        [
            "",
            "## Grouped Distributions",
            "",
            f"- Records by domain: {drift_metrics['records_by_domain']}",
            f"- Records by signal: {drift_metrics['records_by_signal']}",
            f"- Rule B_sigma labels: {drift_metrics['rule_bsigma_by_label']}",
            "",
            "## Drift Groups",
            "",
            f"- Event types: {drift_metrics['event_types']}",
            f"- Events by domain: {drift_metrics['events_by_domain']}",
            f"- Events by domain/target: {drift_metrics['events_by_domain_target']}",
            f"- Events by signal: {drift_metrics['events_by_signal']}",
            f"- Target mismatches by target: {drift_metrics['target_mismatches_by_target']}",
            f"- Missing B_sigma by label: {drift_metrics['missing_bsigma_by_label']}",
            f"- Extra B_sigma by label: {drift_metrics['extra_bsigma_by_label']}",
            "",
            "## Boundary",
            "",
            "- This report is a drift ledger, not permission to replace rule-derived labels.",
            "- Empty drift groups mean the current candidate matched the rule pipeline on this case set only.",
        ]
    )
    return "\n".join(lines)


def build_promotion_report(promotion: dict, metrics_path: Path, drift_path: Path, shadow_path: Path, version_tag: str = VERSION_TAG) -> str:
    lines = [
        f"# PSM {version_tag} Promotion Report",
        "",
        "## Decision",
        "",
        f"- Shadow clean: {promotion['shadow_clean']}",
        f"- Candidate-assisted clean: {promotion['candidate_assisted_clean']}",
        f"- Candidate drift clean: {promotion['candidate_drift_clean']}",
        f"- Rule replacement allowed: {promotion['rule_replacement_allowed']}",
        f"- Candidate-assisted mode allowed: {promotion['candidate_assisted_mode_allowed']}",
        f"- Next allowed stage: {promotion['next_allowed_stage']}",
        "",
        "## Evidence",
        "",
        f"- Shadow metrics: `{shadow_path}`",
        f"- Candidate-assisted metrics: `{metrics_path}`",
        f"- Candidate-assisted drift metrics: `{drift_path}`",
        "",
        "## Hard Boundaries",
        "",
    ]
    lines.extend(f"- {boundary}" for boundary in promotion["hard_boundaries"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
