from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


TARGETS = ["q_status", "risk_level", "route", "bsigma_status"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a majority-by-domain baseline for PSM state-encoder labels.")
    parser.add_argument("--dataset", type=Path, default=Path("state_dataset_out/psm_v0.20_state_encoder.jsonl"))
    parser.add_argument("--outdir", type=Path, default=Path("state_dataset_out"))
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    model = train_baseline(records)
    predictions = [predict_record(model, record) for record in records]
    metrics = evaluate(records, predictions)
    predictions_path = args.outdir / "psm_v0.20_state_baseline_predictions.jsonl"
    predictions_path.write_text(
        "".join(json.dumps(prediction, ensure_ascii=False) + "\n" for prediction in predictions),
        encoding="utf-8",
    )
    metrics_path = args.outdir / "psm_v0.20_state_baseline_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = args.outdir / "PSM_V0.20_State_Encoder_Baseline_Report.md"
    report_path.write_text(build_report(metrics, predictions_path), encoding="utf-8")
    print(f"records: {len(records)}")
    print(f"predictions: {predictions_path}")
    print(f"metrics: {metrics_path}")
    print(f"report: {report_path}")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def train_baseline(records: list[dict]) -> dict:
    train_records = [record for record in records if record["split"] == "train"]
    if not train_records:
        train_records = records
    global_targets = {target: majority(record["labels"][target] for record in train_records) for target in TARGETS}
    domain_targets: dict[str, dict[str, str]] = defaultdict(dict)
    domains = sorted({record["input"]["domain"] for record in train_records})
    for domain in domains:
        domain_records = [record for record in train_records if record["input"]["domain"] == domain]
        for target in TARGETS:
            domain_targets[domain][target] = majority(record["labels"][target] for record in domain_records)
    global_risks = majority_risk_set(train_records)
    domain_risks = {domain: majority_risk_set([record for record in train_records if record["input"]["domain"] == domain]) for domain in domains}
    return {
        "global_targets": global_targets,
        "domain_targets": dict(domain_targets),
        "global_bsigma_risks": global_risks,
        "domain_bsigma_risks": domain_risks,
    }


def predict_record(model: dict, record: dict) -> dict:
    domain = record["input"]["domain"]
    domain_targets = model["domain_targets"].get(domain, {})
    predicted = {
        target: domain_targets.get(target, model["global_targets"][target])
        for target in TARGETS
    }
    predicted["bsigma_risks"] = model["domain_bsigma_risks"].get(domain, model["global_bsigma_risks"])
    return {
        "record_id": record["record_id"],
        "split": record["split"],
        "domain": domain,
        "truth": {target: record["labels"][target] for target in TARGETS} | {"bsigma_risks": record["labels"]["bsigma_risks"]},
        "prediction": predicted,
    }


def evaluate(records: list[dict], predictions: list[dict]) -> dict:
    by_id = {record["record_id"]: record for record in records}
    metrics = {"overall": score_subset(records, predictions), "splits": {}}
    for split in sorted({record["split"] for record in records}):
        split_records = [record for record in records if record["split"] == split]
        split_predictions = [prediction for prediction in predictions if by_id[prediction["record_id"]]["split"] == split]
        metrics["splits"][split] = score_subset(split_records, split_predictions)
    return metrics


def score_subset(records: list[dict], predictions: list[dict]) -> dict:
    if not records:
        return {"records": 0}
    truth_by_id = {record["record_id"]: record["labels"] for record in records}
    result = {"records": len(records)}
    for target in TARGETS:
        correct = sum(1 for prediction in predictions if prediction["prediction"][target] == truth_by_id[prediction["record_id"]][target])
        result[f"{target}_accuracy"] = round(correct / len(records), 3)
    exact = sum(1 for prediction in predictions if set(prediction["prediction"]["bsigma_risks"]) == set(truth_by_id[prediction["record_id"]]["bsigma_risks"]))
    result["bsigma_risks_exact_match"] = round(exact / len(records), 3)
    result["bsigma_risks_micro_f1"] = round(micro_f1(truth_by_id, predictions), 3)
    return result


def micro_f1(truth_by_id: dict, predictions: list[dict]) -> float:
    tp = fp = fn = 0
    for prediction in predictions:
        truth = set(truth_by_id[prediction["record_id"]]["bsigma_risks"])
        pred = set(prediction["prediction"]["bsigma_risks"])
        tp += len(truth & pred)
        fp += len(pred - truth)
        fn += len(truth - pred)
    if tp == 0 and fp == 0 and fn == 0:
        return 1.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def majority(values) -> str:
    counter = Counter(values)
    return sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))[0][0]


def majority_risk_set(records: list[dict]) -> list[str]:
    if not records:
        return []
    risk_sets = [tuple(record["labels"]["bsigma_risks"]) for record in records]
    return list(majority(risk_sets))


def build_report(metrics: dict, predictions_path: Path) -> str:
    lines = [
        "# PSM V0.20 State Encoder Baseline Report",
        "",
        "## Summary",
        "",
        f"- Predictions: `{predictions_path}`",
        f"- Overall records: {metrics['overall']['records']}",
        f"- Q status accuracy: {metrics['overall']['q_status_accuracy']}",
        f"- Risk level accuracy: {metrics['overall']['risk_level_accuracy']}",
        f"- Route accuracy: {metrics['overall']['route_accuracy']}",
        f"- B_sigma status accuracy: {metrics['overall']['bsigma_status_accuracy']}",
        f"- B_sigma risks exact match: {metrics['overall']['bsigma_risks_exact_match']}",
        f"- B_sigma risks micro F1: {metrics['overall']['bsigma_risks_micro_f1']}",
        "",
        "## Split Metrics",
        "",
    ]
    for split, split_metrics in metrics["splits"].items():
        lines.extend(
            [
                f"### {split}",
                "",
                f"- Records: {split_metrics['records']}",
                f"- Q status accuracy: {split_metrics.get('q_status_accuracy')}",
                f"- Risk level accuracy: {split_metrics.get('risk_level_accuracy')}",
                f"- Route accuracy: {split_metrics.get('route_accuracy')}",
                f"- B_sigma status accuracy: {split_metrics.get('bsigma_status_accuracy')}",
                f"- B_sigma risks exact match: {split_metrics.get('bsigma_risks_exact_match')}",
                f"- B_sigma risks micro F1: {split_metrics.get('bsigma_risks_micro_f1')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- This is a majority-by-domain baseline, not a trained neural state encoder.",
            "- Its purpose is to expose which labels are easy from domain/risk priors and which require richer state features.",
            "- V1 should beat this baseline on validation/test before replacing rule-derived routing.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
