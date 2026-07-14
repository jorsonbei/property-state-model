from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .shadow_runner import compare_rule_and_candidate, load_jsonl
from .state_encoder_candidate import TARGETS, extract_signals, predict_record, train_candidate


VERSION_TAG = "V0.20"
DATASET_STEM = "psm_v0.20"
REFERENCE_STEM = "psm_v0.14"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run no-retrain blind holdout stress checks for the state-encoder candidate.")
    parser.add_argument("--stem", default=DATASET_STEM)
    parser.add_argument("--version-tag", default=VERSION_TAG)
    parser.add_argument("--reference-stem", default=REFERENCE_STEM)
    parser.add_argument("--reference-dataset", type=Path, default=None)
    parser.add_argument("--full-dataset", type=Path, default=None)
    parser.add_argument("--holdout-prefix", default="v15_")
    parser.add_argument("--outdir", type=Path, default=Path("holdout_out"))
    parser.add_argument("--fail-on-holdout-drift", action="store_true")
    args = parser.parse_args()
    if args.reference_dataset is None:
        args.reference_dataset = Path(f"holdout_out/{args.reference_stem}_reference_state_encoder.jsonl")
    if args.full_dataset is None:
        args.full_dataset = Path(f"state_dataset_out/{args.stem}_state_encoder.jsonl")

    args.outdir.mkdir(parents=True, exist_ok=True)
    reference_records = load_jsonl(args.reference_dataset)
    full_records = load_jsonl(args.full_dataset)
    holdout_records = [record for record in full_records if record["record_id"].startswith(args.holdout_prefix)]
    if not holdout_records:
        raise SystemExit(f"no holdout records found with prefix {args.holdout_prefix!r}")

    no_retrain_model = train_candidate(reference_records, args.reference_stem)
    post_retrain_model = train_candidate(full_records, args.stem)
    no_retrain_rows, no_retrain_events = evaluate_model(no_retrain_model, holdout_records, stage="no_retrain_holdout")
    post_retrain_rows, post_retrain_events = evaluate_model(post_retrain_model, holdout_records, stage="post_retrain_holdout")
    queue = build_active_learning_queue(no_retrain_rows, no_retrain_events)

    metrics = {
        "version": args.stem,
        "reference_dataset": str(args.reference_dataset),
        "full_dataset": str(args.full_dataset),
        "reference_records": len(reference_records),
        "full_records": len(full_records),
        "holdout_prefix": args.holdout_prefix,
        "holdout_records": len(holdout_records),
        "no_retrain": build_metrics(no_retrain_rows, no_retrain_events),
        "post_retrain": build_metrics(post_retrain_rows, post_retrain_events),
        "active_learning_queue_items": len(queue),
        "rule_replacement_allowed": False,
    }

    no_rows_path = args.outdir / f"{args.stem}_holdout_no_retrain_predictions.jsonl"
    post_rows_path = args.outdir / f"{args.stem}_holdout_post_retrain_predictions.jsonl"
    ledger_path = args.outdir / f"{args.stem}_holdout_no_retrain_drift_ledger.jsonl"
    queue_path = args.outdir / f"{args.stem}_active_learning_queue.jsonl"
    metrics_path = args.outdir / f"{args.stem}_holdout_stress_metrics.json"
    report_path = args.outdir / f"PSM_{args.version_tag}_Holdout_Stress_Report.md"

    no_rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in no_retrain_rows), encoding="utf-8")
    post_rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in post_retrain_rows), encoding="utf-8")
    ledger_path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in no_retrain_events), encoding="utf-8")
    queue_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in queue), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(
        build_report(metrics, no_rows_path, post_rows_path, ledger_path, queue_path, args.version_tag),
        encoding="utf-8",
    )

    print(f"reference_records: {metrics['reference_records']}")
    print(f"full_records: {metrics['full_records']}")
    print(f"holdout_records: {metrics['holdout_records']}")
    print(f"no_retrain_ledger_events: {metrics['no_retrain']['ledger_events']}")
    print(f"post_retrain_ledger_events: {metrics['post_retrain']['ledger_events']}")
    print(f"active_learning_queue_items: {metrics['active_learning_queue_items']}")
    print(f"rule_replacement_allowed: {metrics['rule_replacement_allowed']}")
    print(f"report: {report_path}")
    if args.fail_on_holdout_drift and metrics["no_retrain"]["ledger_events"]:
        raise SystemExit(1)


def evaluate_model(model: dict, records: list[dict], stage: str) -> tuple[list[dict], list[dict]]:
    rows = []
    events = []
    for record in records:
        prediction_item = predict_record(model, record)
        prediction = prediction_item["prediction"]
        row_events = [with_stage(event, stage) for event in compare_rule_and_candidate(record, prediction)]
        rows.append(
            {
                "stage": stage,
                "record_id": record["record_id"],
                "split": record["split"],
                "domain": record["input"]["domain"],
                "signature": prediction_item["signature"],
                "signals": extract_signals(record),
                "rule": record["labels"],
                "candidate": prediction,
                "events": row_events,
            }
        )
        events.extend(row_events)
    return rows, events


def with_stage(event: dict, stage: str) -> dict:
    result = dict(event)
    result["stage"] = stage
    result["final_source"] = "rule_pipeline"
    result["candidate_source"] = "state_encoder_candidate"
    return result


def build_metrics(rows: list[dict], events: list[dict]) -> dict:
    records = len(rows)
    event_types = Counter(event["event_type"] for event in events)
    severities = Counter(event["severity"] for event in events)
    records_with_events = len({event["record_id"] for event in events})
    records_by_domain = Counter(row["domain"] for row in rows)
    events_by_domain = Counter(event["domain"] for event in events)
    events_by_signal = Counter()
    rows_by_id = {row["record_id"]: row for row in rows}
    for event in events:
        for signal in rows_by_id[event["record_id"]]["signals"]:
            events_by_signal[f"{signal}:{event['event_type']}"] += 1
    target_match_rates = {
        target: round(sum(1 for row in rows if row["rule"][target] == row["candidate"][target]) / records, 3) if records else 0.0
        for target in TARGETS
    }
    bsigma_exact_match = (
        round(sum(1 for row in rows if set(row["rule"]["bsigma_risks"]) == set(row["candidate"]["bsigma_risks"])) / records, 3)
        if records
        else 0.0
    )
    return {
        "records": records,
        "clean_records": records - records_with_events,
        "records_with_events": records_with_events,
        "ledger_events": len(events),
        "blocking_events": severities.get("blocking", 0),
        "review_events": severities.get("review", 0),
        "unsafe_lower_predictions": sum(1 for event in events if event.get("unsafe_lower")),
        "missing_bsigma_labels": event_types.get("missing_bsigma_label", 0),
        "extra_bsigma_labels": event_types.get("extra_bsigma_label", 0),
        "target_mismatches": event_types.get("target_mismatch", 0),
        "target_match_rates": target_match_rates,
        "bsigma_exact_match": bsigma_exact_match,
        "event_types": dict(sorted(event_types.items())),
        "records_by_domain": dict(sorted(records_by_domain.items())),
        "events_by_domain": dict(sorted(events_by_domain.items())),
        "events_by_signal": dict(sorted(events_by_signal.items())),
        "holdout_boundary_passed": len(events) == 0,
    }


def build_active_learning_queue(rows: list[dict], events: list[dict]) -> list[dict]:
    rows_by_id = {row["record_id"]: row for row in rows}
    queue = []
    for event in events:
        row = rows_by_id[event["record_id"]]
        queue.append(
            {
                "record_id": event["record_id"],
                "priority": "P0" if event["severity"] == "blocking" else "P1",
                "reason": event["event_type"],
                "domain": event["domain"],
                "target": event["target"],
                "signals": row["signals"],
                "rule": event.get("rule"),
                "candidate": event.get("candidate"),
                "label": event.get("label"),
                "required_action": "add targeted case or feature; keep rule-only final labels",
            }
        )
    return queue


def build_report(metrics: dict, no_rows_path: Path, post_rows_path: Path, ledger_path: Path, queue_path: Path, version_tag: str = VERSION_TAG) -> str:
    no_retrain = metrics["no_retrain"]
    post_retrain = metrics["post_retrain"]
    lines = [
        f"# PSM {version_tag} Holdout Stress Report",
        "",
        "## Summary",
        "",
        f"- Reference dataset: `{metrics['reference_dataset']}`",
        f"- Full dataset: `{metrics['full_dataset']}`",
        f"- Reference records: {metrics['reference_records']}",
        f"- Full records: {metrics['full_records']}",
        f"- Holdout prefix: `{metrics['holdout_prefix']}`",
        f"- Holdout records: {metrics['holdout_records']}",
        f"- Active-learning queue items: {metrics['active_learning_queue_items']}",
        f"- Rule replacement allowed: {metrics['rule_replacement_allowed']}",
        "",
        "## No-Retrain Holdout",
        "",
        f"- Clean records: {no_retrain['clean_records']}",
        f"- Ledger events: {no_retrain['ledger_events']}",
        f"- Blocking events: {no_retrain['blocking_events']}",
        f"- Review events: {no_retrain['review_events']}",
        f"- Unsafe lower predictions: {no_retrain['unsafe_lower_predictions']}",
        f"- Target match rates: {no_retrain['target_match_rates']}",
        f"- B_sigma exact match: {no_retrain['bsigma_exact_match']}",
        f"- Boundary passed: {no_retrain['holdout_boundary_passed']}",
        f"- Predictions: `{no_rows_path}`",
        f"- Drift ledger: `{ledger_path}`",
        "",
        "## Post-Retrain Holdout",
        "",
        f"- Clean records: {post_retrain['clean_records']}",
        f"- Ledger events: {post_retrain['ledger_events']}",
        f"- Blocking events: {post_retrain['blocking_events']}",
        f"- Review events: {post_retrain['review_events']}",
        f"- Unsafe lower predictions: {post_retrain['unsafe_lower_predictions']}",
        f"- Target match rates: {post_retrain['target_match_rates']}",
        f"- B_sigma exact match: {post_retrain['bsigma_exact_match']}",
        f"- Boundary passed: {post_retrain['holdout_boundary_passed']}",
        f"- Predictions: `{post_rows_path}`",
        "",
        "## Active Learning",
        "",
        f"- Queue: `{queue_path}`",
        f"- No-retrain event types: {no_retrain['event_types']}",
        f"- No-retrain events by domain: {no_retrain['events_by_domain']}",
        f"- No-retrain events by signal: {no_retrain['events_by_signal']}",
        "",
        "## Boundary",
        "",
        "- No-retrain holdout is the promotion-relevant stress check.",
        "- Post-retrain numbers are diagnostic only.",
        "- A clean holdout does not permit rule replacement in V0.x.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
