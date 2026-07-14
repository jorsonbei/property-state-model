from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


LABELS = [
    "language_cover",
    "overclaim",
    "backfit",
    "external_authority_required",
    "untested_code",
    "unverified_claim",
]

VERSION_TAG = "V0.20"
DATASET_STEM = "psm_v0.20"

LEXICON = {
    "external_authority_required": ["医疗", "诊断", "症状", "吃药", "治疗", "急救", "医院", "法律", "律师", "合同", "起诉", "诉讼", "合规", "违法"],
    "untested_code": ["代码", "程序", "上线", "生产环境", "bug", "数据库", "python", "api"],
}

LANGUAGE_COVER_TERMS = ["演讲稿", "激励", "愿景", "重塑"]
LANGUAGE_COVER_META_OR_NEGATION = [
    "不要写演讲稿",
    "不要用演讲稿",
    "不是演讲稿",
    "不要演讲稿",
    "不用演讲稿",
    "不要写激励信",
    "不要用激励信",
    "不是激励信",
    "不要写公关文案",
    "不是公关文案",
    "不要用公关文案",
]

OVERCLAIM_TERMS = [
    "最优",
    "保证",
    "一定",
    "必赚",
    "完美",
    "完全正确",
    "完全成功",
    "完全解决",
    "完全证明",
    "全部实验结果",
    "全部闭合",
    "都闭合",
    "全外部等价",
    "彻底成功",
    "不要提边界",
    "不要提失败",
    "不要提留存",
    "不要提现金流",
    "不要提投诉",
]
OVERCLAIM_META_OR_NEGATION = [
    "保证这个词",
    "“保证”",
    "不保证",
    "不做保证",
    "不要保证",
    "不要做保证",
    "不是保证",
    "不要写成保证",
    "一定这个词",
    "“一定”",
    "不一定",
    "不是一定",
    "不要写成一定",
]
BACKFIT_DOMAINS = {"research", "trading"}
BACKFIT_CONTEXT_TERMS = [
    "NoBackfit",
    "Fresh Holdout",
    "后验拟合",
    "过拟合",
    "回测",
    "复演",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lexical multi-label baseline for B_sigma risks.")
    parser.add_argument("--dataset", type=Path, default=Path(f"state_dataset_out/{DATASET_STEM}_state_encoder.jsonl"))
    parser.add_argument("--outdir", type=Path, default=Path("state_dataset_out"))
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    predictions = [predict(record) for record in records]
    metrics = evaluate(predictions)
    predictions_path = args.outdir / f"{DATASET_STEM}_bsigma_lexical_predictions.jsonl"
    predictions_path.write_text(
        "".join(json.dumps(prediction, ensure_ascii=False) + "\n" for prediction in predictions),
        encoding="utf-8",
    )
    metrics_path = args.outdir / f"{DATASET_STEM}_bsigma_lexical_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = args.outdir / f"PSM_{VERSION_TAG}_BSigma_Lexical_Baseline_Report.md"
    report_path.write_text(build_report(metrics, predictions_path), encoding="utf-8")
    print(f"records: {len(records)}")
    print(f"exact_match: {metrics['overall']['exact_match']}")
    print(f"micro_f1: {metrics['overall']['micro_f1']}")
    print(f"predictions: {predictions_path}")
    print(f"metrics: {metrics_path}")
    print(f"report: {report_path}")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def predict(record: dict) -> dict:
    text = record["input"]["user_request"]
    lowered = text.lower()
    domain = record["input"]["domain"]
    predicted = []
    for label, terms in LEXICON.items():
        if any(term.lower() in lowered for term in terms):
            predicted.append(label)
    if is_language_cover(text):
        predicted.append("language_cover")
    if is_overclaim(text):
        predicted.append("overclaim")
    if is_backfit_context(domain, text):
        predicted.append("backfit")
    if not predicted:
        predicted.append("unverified_claim")
    truth = list(record["labels"]["bsigma_risks"])
    return {
        "record_id": record["record_id"],
        "split": record["split"],
        "domain": domain,
        "risk_level": record["labels"]["risk_level"],
        "truth": sorted(truth),
        "prediction": sorted(set(predicted)),
    }


def is_backfit_context(domain: str, text: str) -> bool:
    if domain in BACKFIT_DOMAINS:
        return True
    lowered = text.lower()
    return any(term.lower() in lowered for term in BACKFIT_CONTEXT_TERMS)


def is_language_cover(text: str) -> bool:
    filtered = text
    for phrase in LANGUAGE_COVER_META_OR_NEGATION:
        filtered = filtered.replace(phrase, "")
    lowered = filtered.lower()
    return any(term.lower() in lowered for term in LANGUAGE_COVER_TERMS)


def is_overclaim(text: str) -> bool:
    filtered = text
    for phrase in OVERCLAIM_META_OR_NEGATION:
        filtered = filtered.replace(phrase, "")
    lowered = filtered.lower()
    return any(term.lower() in lowered for term in OVERCLAIM_TERMS)


def evaluate(predictions: list[dict]) -> dict:
    return {
        "overall": score_subset(predictions),
        "splits": {split: score_subset([item for item in predictions if item["split"] == split]) for split in sorted({item["split"] for item in predictions})},
        "per_label": {label: score_label(predictions, label) for label in LABELS},
        "confusions": build_confusions(predictions),
    }


def score_subset(predictions: list[dict]) -> dict:
    if not predictions:
        return {"records": 0}
    exact = sum(1 for item in predictions if set(item["truth"]) == set(item["prediction"]))
    tp = fp = fn = 0
    for item in predictions:
        truth = set(item["truth"])
        pred = set(item["prediction"])
        tp += len(truth & pred)
        fp += len(pred - truth)
        fn += len(truth - pred)
    return {
        "records": len(predictions),
        "exact_match": round(exact / len(predictions), 3),
        "micro_precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
        "micro_recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
        "micro_f1": round(_f1(tp, fp, fn), 3),
    }


def score_label(predictions: list[dict], label: str) -> dict:
    tp = fp = fn = tn = 0
    for item in predictions:
        truth = label in set(item["truth"])
        pred = label in set(item["prediction"])
        if truth and pred:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif truth and not pred:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0,
    }


def build_confusions(predictions: list[dict]) -> dict:
    false_positive_pairs = Counter()
    false_negative_pairs = Counter()
    false_negative_critical = []
    for item in predictions:
        truth = set(item["truth"])
        pred = set(item["prediction"])
        for label in sorted(pred - truth):
            false_positive_pairs[(item["domain"], label)] += 1
        for label in sorted(truth - pred):
            false_negative_pairs[(item["domain"], label)] += 1
            if item.get("risk_level") == "critical":
                false_negative_critical.append(
                    {
                        "record_id": item["record_id"],
                        "domain": item["domain"],
                        "label": label,
                    }
                )
    return {
        "false_positives_by_domain_label": {f"{domain}:{label}": count for (domain, label), count in sorted(false_positive_pairs.items())},
        "false_negatives_by_domain_label": {f"{domain}:{label}": count for (domain, label), count in sorted(false_negative_pairs.items())},
        "critical_false_negatives": false_negative_critical,
    }


def _f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def build_report(metrics: dict, predictions_path: Path) -> str:
    lines = [
        f"# PSM {VERSION_TAG} B_sigma Lexical Baseline Report",
        "",
        "## Summary",
        "",
        f"- Predictions: `{predictions_path}`",
        f"- Records: {metrics['overall']['records']}",
        f"- Exact match: {metrics['overall']['exact_match']}",
        f"- Micro precision: {metrics['overall']['micro_precision']}",
        f"- Micro recall: {metrics['overall']['micro_recall']}",
        f"- Micro F1: {metrics['overall']['micro_f1']}",
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
                f"- Exact match: {split_metrics['exact_match']}",
                f"- Micro precision: {split_metrics['micro_precision']}",
                f"- Micro recall: {split_metrics['micro_recall']}",
                f"- Micro F1: {split_metrics['micro_f1']}",
                "",
            ]
        )
    lines.extend(["## Per-Label Metrics", ""])
    for label, label_metrics in metrics["per_label"].items():
        lines.extend(
            [
                f"### {label}",
                "",
                f"- TP: {label_metrics['tp']}",
                f"- FP: {label_metrics['fp']}",
                f"- FN: {label_metrics['fn']}",
                f"- Precision: {label_metrics['precision']}",
                f"- Recall: {label_metrics['recall']}",
                f"- F1: {label_metrics['f1']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Confusions",
            "",
            f"- False positives by domain/label: {metrics['confusions']['false_positives_by_domain_label']}",
            f"- False negatives by domain/label: {metrics['confusions']['false_negatives_by_domain_label']}",
            f"- Critical false negatives: {metrics['confusions']['critical_false_negatives']}",
            "",
            "## Boundary",
            "",
            "- This baseline is lexical and deterministic; it is not a trained model.",
            "- Its purpose is to set a stronger B_sigma risk-set baseline than domain-majority.",
            "- A V1 state encoder should beat both the V0.20 domain-majority baseline and this lexical baseline on held-out cases before replacing rule-derived labels.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
