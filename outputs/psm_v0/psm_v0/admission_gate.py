from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_THRESHOLDS = {
    "exact_match": 0.95,
    "micro_f1": 0.98,
    "critical_false_negatives": 0,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check V1 admission thresholds for B_sigma risk prediction.")
    parser.add_argument("--stem", default="psm_v0.20")
    parser.add_argument("--version-tag", default="V0.20")
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("state_dataset_out"))
    parser.add_argument("--candidate", default="trainable_state_encoder_candidate")
    args = parser.parse_args()
    if args.metrics is None:
        args.metrics = Path(f"state_dataset_out/{args.stem}_state_encoder_candidate_bsigma_metrics.json")
    if args.predictions is None:
        args.predictions = Path(f"state_dataset_out/{args.stem}_state_encoder_candidate_bsigma_predictions.jsonl")

    args.outdir.mkdir(parents=True, exist_ok=True)
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    predictions = load_jsonl(args.predictions)
    result = evaluate_admission(metrics, predictions, args.candidate)
    json_path = args.outdir / f"{args.stem}_v1_admission_gate.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = args.outdir / f"PSM_{args.version_tag}_V1_Admission_Gate_Report.md"
    report_path.write_text(build_report(result, args.metrics, args.predictions, args.version_tag), encoding="utf-8")
    print(f"candidate: {args.candidate}")
    print(f"passed: {result['passed']}")
    print(f"exact_match: {result['observed']['exact_match']}")
    print(f"micro_f1: {result['observed']['micro_f1']}")
    print(f"critical_false_negatives: {result['observed']['critical_false_negatives']}")
    print(f"report: {report_path}")
    if not result["passed"]:
        raise SystemExit(1)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_admission(metrics: dict, predictions: list[dict], candidate: str) -> dict:
    critical_false_negatives = find_critical_false_negatives(predictions)
    observed = {
        "exact_match": metrics["overall"]["exact_match"],
        "micro_f1": metrics["overall"]["micro_f1"],
        "critical_false_negatives": len(critical_false_negatives),
    }
    checks = {
        "exact_match": observed["exact_match"] >= DEFAULT_THRESHOLDS["exact_match"],
        "micro_f1": observed["micro_f1"] >= DEFAULT_THRESHOLDS["micro_f1"],
        "critical_false_negatives": observed["critical_false_negatives"] <= DEFAULT_THRESHOLDS["critical_false_negatives"],
    }
    return {
        "candidate": candidate,
        "passed": all(checks.values()),
        "thresholds": DEFAULT_THRESHOLDS,
        "observed": observed,
        "checks": checks,
        "critical_false_negative_items": critical_false_negatives,
    }


def find_critical_false_negatives(predictions: list[dict]) -> list[dict]:
    misses = []
    for item in predictions:
        truth = set(item["truth"])
        pred = set(item["prediction"])
        if item.get("risk_level") != "critical":
            continue
        for label in sorted(truth - pred):
            misses.append(
                {
                    "record_id": item["record_id"],
                    "domain": item["domain"],
                    "label": label,
                    "truth": item["truth"],
                    "prediction": item["prediction"],
                }
            )
    return misses


def build_report(result: dict, metrics_path: Path, predictions_path: Path, version_tag: str) -> str:
    checks = result["checks"]
    observed = result["observed"]
    thresholds = result["thresholds"]
    lines = [
        f"# PSM {version_tag} V1 Admission Gate Report",
        "",
        "## Summary",
        "",
        f"- Candidate: `{result['candidate']}`",
        f"- Passed: {result['passed']}",
        f"- Metrics: `{metrics_path}`",
        f"- Predictions: `{predictions_path}`",
        "",
        "## Thresholds",
        "",
        f"- Exact match >= {thresholds['exact_match']}",
        f"- Micro F1 >= {thresholds['micro_f1']}",
        f"- Critical false negatives <= {thresholds['critical_false_negatives']}",
        "",
        "## Observed",
        "",
        f"- Exact match: {observed['exact_match']} ({'PASS' if checks['exact_match'] else 'FAIL'})",
        f"- Micro F1: {observed['micro_f1']} ({'PASS' if checks['micro_f1'] else 'FAIL'})",
        f"- Critical false negatives: {observed['critical_false_negatives']} ({'PASS' if checks['critical_false_negatives'] else 'FAIL'})",
        "",
        "## Boundary",
        "",
        "- This gate only covers B_sigma risk-set prediction.",
        "- Passing this gate does not make the system a trained V1 state encoder.",
        "- A trained V1 candidate must meet or exceed this gate before replacing rule-derived labels.",
    ]
    if result["critical_false_negative_items"]:
        lines.extend(["", "## Critical False Negatives", ""])
        for item in result["critical_false_negative_items"]:
            lines.append(f"- {item['record_id']}: missed `{item['label']}` truth={item['truth']} prediction={item['prediction']}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
