from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .pipeline import run_pipeline
from .state_encoder_candidate import TARGETS, predict_record, train_candidate


VERSION_TAG = "V0.20"
DATASET_STEM = "psm_v0.20"

TARGET_ORDER = {
    "q_status": {"pass": 0, "review_required": 1, "veto": 2},
    "risk_level": {"low": 0, "medium": 1, "high": 2, "critical": 3},
    "route": {
        "direct_language": 0,
        "retrieval_or_tool_check": 1,
        "audited_generation": 2,
        "external_judge_and_human_confirmation": 3,
    },
    "bsigma_status": {"clean": 0, "review": 1, "suspect": 2},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run shadow replacement-boundary checks for the state-encoder candidate.")
    parser.add_argument("--stem", default=DATASET_STEM)
    parser.add_argument("--version-tag", default=VERSION_TAG)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("shadow_out"))
    parser.add_argument("--fail-on-disagreement", action="store_true")
    args = parser.parse_args()
    if args.dataset is None:
        args.dataset = Path(f"state_dataset_out/{args.stem}_state_encoder.jsonl")

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    model = train_candidate(records, args.stem)
    shadow_rows = []
    ledger_events = []
    for record in records:
        fresh_record = build_fresh_rule_record(record)
        prediction = predict_record(model, fresh_record)["prediction"]
        row_events = compare_rule_and_candidate(fresh_record, prediction)
        shadow_rows.append(
            {
                "record_id": fresh_record["record_id"],
                "split": fresh_record["split"],
                "domain": fresh_record["input"]["domain"],
                "rule": fresh_record["labels"],
                "candidate": prediction,
                "events": row_events,
            }
        )
        ledger_events.extend(row_events)

    metrics = build_metrics(shadow_rows, ledger_events)
    rows_path = args.outdir / f"{args.stem}_shadow_predictions.jsonl"
    ledger_path = args.outdir / f"{args.stem}_replacement_disagreement_ledger.jsonl"
    metrics_path = args.outdir / f"{args.stem}_shadow_metrics.json"
    report_path = args.outdir / f"PSM_{args.version_tag}_Shadow_Run_Report.md"
    rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in shadow_rows), encoding="utf-8")
    ledger_path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in ledger_events), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(metrics, rows_path, ledger_path, args.version_tag), encoding="utf-8")

    print(f"records: {metrics['records']}")
    print(f"ledger_events: {metrics['ledger_events']}")
    print(f"blocking_events: {metrics['blocking_events']}")
    print(f"replacement_boundary_passed: {metrics['replacement_boundary_passed']}")
    print(f"ledger: {ledger_path}")
    print(f"report: {report_path}")
    if args.fail_on_disagreement and not metrics["replacement_boundary_passed"]:
        raise SystemExit(1)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_fresh_rule_record(record: dict) -> dict:
    request = record["input"]["user_request"]
    result = run_pipeline(request)
    packet = result["packet"]
    return {
        "schema_version": record["schema_version"],
        "record_id": record["record_id"],
        "split": record["split"],
        "source": record["source"],
        "input": {
            "user_request": request,
            "domain": packet["domain"],
            "phi_state": packet["phi_state"],
            "q_core": packet["q_core"],
            "omega_observed": packet["omega"],
            "delta_sigma": packet["delta_sigma"],
            "pi_cavity": packet["pi_cavity"],
            "eta": packet["eta"],
            "external_judges_observed": packet["external_judges"],
            "statement_level_observed": packet["statement_level"],
        },
        "labels": {
            "q_status": result["q_audit"]["status"],
            "risk_level": packet["omega"]["risk_level"],
            "route": result["route"]["route"],
            "bsigma_status": result["bsigma_audit"]["status"],
            "bsigma_risks": sorted({item["risk"] for item in packet.get("bsigma_risks", [])}),
            "statement_level": packet["statement_level"],
            "gate_score": record["labels"]["gate_score"],
        },
    }


def compare_rule_and_candidate(record: dict, prediction: dict) -> list[dict]:
    events = []
    labels = record["labels"]
    for target in TARGETS:
        rule_value = labels[target]
        candidate_value = prediction[target]
        if rule_value == candidate_value:
            continue
        unsafe_lower = is_lower(target, candidate_value, rule_value)
        events.append(
            {
                "event_type": "target_mismatch",
                "severity": "blocking" if unsafe_lower else "review",
                "record_id": record["record_id"],
                "split": record["split"],
                "domain": record["input"]["domain"],
                "target": target,
                "rule": rule_value,
                "candidate": candidate_value,
                "unsafe_lower": unsafe_lower,
            }
        )

    rule_risks = set(labels["bsigma_risks"])
    candidate_risks = set(prediction["bsigma_risks"])
    for label in sorted(rule_risks - candidate_risks):
        events.append(
            {
                "event_type": "missing_bsigma_label",
                "severity": "blocking",
                "record_id": record["record_id"],
                "split": record["split"],
                "domain": record["input"]["domain"],
                "target": "bsigma_risks",
                "label": label,
                "rule": sorted(rule_risks),
                "candidate": sorted(candidate_risks),
                "unsafe_lower": True,
            }
        )
    for label in sorted(candidate_risks - rule_risks):
        events.append(
            {
                "event_type": "extra_bsigma_label",
                "severity": "review",
                "record_id": record["record_id"],
                "split": record["split"],
                "domain": record["input"]["domain"],
                "target": "bsigma_risks",
                "label": label,
                "rule": sorted(rule_risks),
                "candidate": sorted(candidate_risks),
                "unsafe_lower": False,
            }
        )
    return events


def is_lower(target: str, candidate_value: str, rule_value: str) -> bool:
    order = TARGET_ORDER[target]
    return order.get(candidate_value, -1) < order.get(rule_value, -1)


def build_metrics(rows: list[dict], events: list[dict]) -> dict:
    event_types = Counter(event["event_type"] for event in events)
    severities = Counter(event["severity"] for event in events)
    split_events = Counter(event["split"] for event in events)
    domain_events = Counter(event["domain"] for event in events)
    unsafe_lower = sum(1 for event in events if event.get("unsafe_lower"))
    records_with_events = len({event["record_id"] for event in events})
    return {
        "records": len(rows),
        "clean_records": len(rows) - records_with_events,
        "records_with_events": records_with_events,
        "ledger_events": len(events),
        "blocking_events": severities.get("blocking", 0),
        "review_events": severities.get("review", 0),
        "unsafe_lower_predictions": unsafe_lower,
        "missing_bsigma_labels": event_types.get("missing_bsigma_label", 0),
        "extra_bsigma_labels": event_types.get("extra_bsigma_label", 0),
        "target_mismatches": event_types.get("target_mismatch", 0),
        "event_types": dict(sorted(event_types.items())),
        "events_by_split": dict(sorted(split_events.items())),
        "events_by_domain": dict(sorted(domain_events.items())),
        "replacement_boundary_passed": len(events) == 0,
        "rule_labels_authoritative": True,
    }


def build_report(metrics: dict, rows_path: Path, ledger_path: Path, version_tag: str = VERSION_TAG) -> str:
    lines = [
        f"# PSM {version_tag} Shadow Run Report",
        "",
        "## Summary",
        "",
        f"- Records: {metrics['records']}",
        f"- Clean records: {metrics['clean_records']}",
        f"- Records with events: {metrics['records_with_events']}",
        f"- Ledger events: {metrics['ledger_events']}",
        f"- Blocking events: {metrics['blocking_events']}",
        f"- Review events: {metrics['review_events']}",
        f"- Unsafe lower predictions: {metrics['unsafe_lower_predictions']}",
        f"- Missing B_sigma labels: {metrics['missing_bsigma_labels']}",
        f"- Extra B_sigma labels: {metrics['extra_bsigma_labels']}",
        f"- Target mismatches: {metrics['target_mismatches']}",
        f"- Replacement boundary passed: {metrics['replacement_boundary_passed']}",
        f"- Shadow predictions: `{rows_path}`",
        f"- Disagreement ledger: `{ledger_path}`",
        "",
        "## Distributions",
        "",
        f"- Event types: {metrics['event_types']}",
        f"- Events by split: {metrics['events_by_split']}",
        f"- Events by domain: {metrics['events_by_domain']}",
        "",
        "## Boundary",
        "",
        "- The executable PSM rule pipeline remains authoritative.",
        "- A clean shadow ledger only permits further shadow rollout; it does not directly replace rule-derived labels.",
        "- Any target mismatch, missing B_sigma label, or unsafe lower-risk prediction blocks replacement.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
