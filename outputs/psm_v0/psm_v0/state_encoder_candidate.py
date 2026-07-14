from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


VERSION_TAG = "V0.20"
DATASET_STEM = "psm_v0.20"
TARGETS = ["q_status", "risk_level", "route", "bsigma_status"]
BSIGMA_LABELS = [
    "language_cover",
    "overclaim",
    "backfit",
    "external_authority_required",
    "untested_code",
    "unverified_claim",
]

LANGUAGE_COVER_TERMS = ["演讲稿", "激励", "愿景", "重塑", "内部信"]
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
    "完全正確",
    "完全成功",
    "完全解决",
    "完全证明",
    "完全證明",
    "全部实验结果",
    "全部闭合",
    "全部閉合",
    "都闭合",
    "都閉合",
    "全外部等价",
    "全外部等價",
    "彻底成功",
    "徹底成功",
    "不要提边界",
    "不要提邊界",
    "不要提失败",
    "不要提失敗",
    "删除 B_sigma",
    "刪除 B_sigma",
    "删除外部裁判",
    "刪除外部裁判",
    "不要提留存",
    "不要提现金流",
    "不要提投诉",
    "guarantee",
    "fully proved",
    "complete success",
    "go live",
    "replace doctor",
    "replace lawyer",
    "global equivalence",
    "外部世界等价读取",
    "外部世界等價讀取",
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
    "“guarantee”",
    "“fully proved”",
    "“complete success”",
    "“go live”",
    "“replace doctor”",
    "“replace lawyer”",
    "“global equivalence”",
    "\"guarantee\"",
    "\"fully proved\"",
    "\"complete success\"",
    "\"go live\"",
    "\"replace doctor\"",
    "\"replace lawyer\"",
    "\"global equivalence\"",
    "not guarantee",
    "not a guarantee",
    "not fully proved",
    "not complete success",
    "not go live",
    "not replace doctor",
    "not replace lawyer",
    "not global equivalence",
]
AUTHORITY_TERMS = ["医疗", "醫療", "诊断", "診斷", "症状", "症狀", "吃药", "吃藥", "治疗", "治療", "急救", "医院", "醫院", "法律", "律师", "律師", "合同", "合約", "起诉", "起訴", "诉讼", "訴訟", "合规", "合規", "违法", "違法"]
UNTESTED_CODE_TERMS = ["代码", "代碼", "程序", "程式", "上线", "上線", "生产环境", "生產環境", "bug", "数据库", "資料庫", "python", "api"]
BACKFIT_CONTEXT_TERMS = ["NoBackfit", "Fresh Holdout", "后验拟合", "後驗擬合", "过拟合", "過擬合", "回测", "回測", "复演", "復演", "实验", "實驗", "论文", "論文", "原始数据", "原始數據", "样本", "樣本", "公式", "推导", "推導"]
CRITICAL_TERMS = ["实盘", "實盤", "生产环境", "生產環境", "上线", "上線", "急救", "破产", "破產", "抵押", "高利贷", "高利貸", "绕过登录", "繞過登入", "绕过权限", "繞過權限", "读取用户数据库", "讀取用戶資料庫", "越权", "越權"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate a transparent PSM state-encoder candidate.")
    parser.add_argument("--stem", default=DATASET_STEM)
    parser.add_argument("--version-tag", default=VERSION_TAG)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("state_dataset_out"))
    args = parser.parse_args()
    if args.dataset is None:
        args.dataset = Path(f"state_dataset_out/{args.stem}_state_encoder.jsonl")

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    model = train_candidate(records, args.stem)
    predictions = [predict_record(model, record) for record in records]
    metrics = evaluate(records, predictions)
    bsigma_predictions = build_bsigma_predictions(records, predictions)
    bsigma_metrics = evaluate_bsigma_predictions(bsigma_predictions)

    model_path = args.outdir / f"{args.stem}_state_encoder_candidate_model.json"
    predictions_path = args.outdir / f"{args.stem}_state_encoder_candidate_predictions.jsonl"
    metrics_path = args.outdir / f"{args.stem}_state_encoder_candidate_metrics.json"
    bsigma_predictions_path = args.outdir / f"{args.stem}_state_encoder_candidate_bsigma_predictions.jsonl"
    bsigma_metrics_path = args.outdir / f"{args.stem}_state_encoder_candidate_bsigma_metrics.json"
    report_path = args.outdir / f"PSM_{args.version_tag}_State_Encoder_Candidate_Report.md"

    model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    predictions_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in predictions), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    bsigma_predictions_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in bsigma_predictions), encoding="utf-8")
    bsigma_metrics_path.write_text(json.dumps(bsigma_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(
        build_report(metrics, bsigma_metrics, model_path, predictions_path, bsigma_predictions_path, args.version_tag),
        encoding="utf-8",
    )

    print(f"records: {len(records)}")
    print(f"state_exact_match: {metrics['overall']['all_targets_exact_match']}")
    print(f"bsigma_exact_match: {bsigma_metrics['overall']['exact_match']}")
    print(f"bsigma_micro_f1: {bsigma_metrics['overall']['micro_f1']}")
    print(f"model: {model_path}")
    print(f"report: {report_path}")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def train_candidate(records: list[dict], dataset_stem: str = DATASET_STEM) -> dict:
    train_records = [record for record in records if record["split"] == "train"] or records
    global_targets = {target: majority(record["labels"][target] for record in train_records) for target in TARGETS}
    domain_targets = {
        domain: {target: majority(record["labels"][target] for record in domain_records) for target in TARGETS}
        for domain, domain_records in group_by(train_records, lambda item: item["input"]["domain"]).items()
    }
    signature_targets = {
        signature: {target: majority(record["labels"][target] for record in signature_records) for target in TARGETS}
        for signature, signature_records in group_by(train_records, record_signature).items()
    }
    signal_labels = train_signal_labels(train_records)
    return {
        "version": dataset_stem,
        "candidate_type": "transparent_signal_signature_encoder",
        "training_records": len(train_records),
        "global_targets": global_targets,
        "domain_targets": domain_targets,
        "signature_targets": signature_targets,
        "signal_labels": signal_labels,
        "boundary": {
            "uses_rule_labels_as_training_targets": True,
            "does_not_replace_rule_labels": True,
            "leakage_guard": "No label fields or omega_observed risk_level are used as prediction features.",
        },
    }


def train_signal_labels(records: list[dict]) -> dict:
    observed: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for record in records:
        signals = extract_signals(record)
        truth = set(record["labels"]["bsigma_risks"])
        for signal in signals:
            totals[signal] += 1
            for label in truth:
                observed[signal][label] += 1
    learned: dict[str, list[str]] = {}
    for signal, total in sorted(totals.items()):
        labels = [label for label, count in observed[signal].items() if count / total >= 0.8]
        learned[signal] = sorted(labels)
    return learned


def predict_record(model: dict, record: dict) -> dict:
    signature = record_signature(record)
    domain = record["input"]["domain"]
    if signature in model["signature_targets"]:
        predicted = dict(model["signature_targets"][signature])
    else:
        predicted = dict(model["domain_targets"].get(domain, model["global_targets"]))
        predicted.update(rule_fallback_state(record))
    predicted["bsigma_risks"] = predict_bsigma_risks(model, record)
    return {
        "record_id": record["record_id"],
        "split": record["split"],
        "domain": domain,
        "signature": signature,
        "truth": {target: record["labels"][target] for target in TARGETS} | {"bsigma_risks": record["labels"]["bsigma_risks"]},
        "prediction": predicted,
    }


def rule_fallback_state(record: dict) -> dict:
    domain = record["input"]["domain"]
    signals = set(extract_signals(record))
    if domain in {"medical", "legal", "trading"} or "critical_world_execution" in signals:
        risk_level = "critical"
    elif domain in {"business_decision", "code_engineering", "research", "wuxing_theory"}:
        risk_level = "high"
    elif domain == "writing":
        risk_level = "low"
    else:
        risk_level = "medium"

    route = {
        "low": "direct_language",
        "medium": "retrieval_or_tool_check",
        "high": "audited_generation",
        "critical": "external_judge_and_human_confirmation",
    }[risk_level]

    if domain == "business_decision" and "language_cover" in signals:
        q_status = "veto"
    elif risk_level in {"high", "critical"}:
        q_status = "review_required"
    else:
        q_status = "pass"

    high_risks = {"overclaim", "backfit", "external_authority_required", "untested_code"}
    if signals & high_risks or (domain == "business_decision" and "language_cover" in signals):
        bsigma_status = "suspect"
    elif signals:
        bsigma_status = "review"
    else:
        bsigma_status = "clean"

    return {
        "q_status": q_status,
        "risk_level": risk_level,
        "route": route,
        "bsigma_status": bsigma_status,
    }


def predict_bsigma_risks(model: dict, record: dict) -> list[str]:
    signals = extract_signals(record)
    labels: set[str] = set()
    for signal in signals:
        labels.update(model["signal_labels"].get(signal, []))
        if signal in BSIGMA_LABELS:
            labels.add(signal)
    if not labels:
        labels.add("unverified_claim")
    if "critical_world_execution" in labels:
        labels.remove("critical_world_execution")
    return sorted(label for label in labels if label in BSIGMA_LABELS)


def extract_signals(record: dict) -> list[str]:
    text = record["input"]["user_request"]
    domain = record["input"]["domain"]
    signals: set[str] = set()
    if contains_language_cover(text):
        signals.add("language_cover")
    if contains_overclaim(text):
        signals.add("overclaim")
    if domain in {"research", "trading"} or contains_any(text, BACKFIT_CONTEXT_TERMS):
        signals.add("backfit")
    if domain in {"medical", "legal"} or contains_any(text, AUTHORITY_TERMS):
        signals.add("external_authority_required")
    if domain == "code_engineering" or contains_any(text, UNTESTED_CODE_TERMS):
        signals.add("untested_code")
    if contains_any(text, CRITICAL_TERMS):
        signals.add("critical_world_execution")
    if not signals or should_mark_unverified(text, domain, signals):
        signals.add("unverified_claim")
    return sorted(signals)


def should_mark_unverified(text: str, domain: str, signals: set[str]) -> bool:
    if signals - {"critical_world_execution"}:
        return False
    if domain in {"general", "writing", "wuxing_theory"}:
        return True
    return contains_any(text, ["缺口", "来源", "來源", "检查", "檢查", "边界", "邊界", "假设", "假設", "验证口径", "驗證口徑", "不要写成结论", "不要寫成結論"])


def record_signature(record: dict) -> str:
    return "|".join([f"domain={record['input']['domain']}"] + [f"signal={signal}" for signal in extract_signals(record)])


def evaluate(records: list[dict], predictions: list[dict]) -> dict:
    by_id = {record["record_id"]: record for record in records}
    return {
        "overall": score_state_subset(records, predictions),
        "splits": {
            split: score_state_subset(
                [record for record in records if record["split"] == split],
                [prediction for prediction in predictions if by_id[prediction["record_id"]]["split"] == split],
            )
            for split in sorted({record["split"] for record in records})
        },
        "confusions": build_state_confusions(records, predictions),
    }


def score_state_subset(records: list[dict], predictions: list[dict]) -> dict:
    if not records:
        return {"records": 0}
    truth_by_id = {record["record_id"]: record["labels"] for record in records}
    result = {"records": len(records)}
    exact_all = 0
    for target in TARGETS:
        correct = sum(1 for item in predictions if item["prediction"][target] == truth_by_id[item["record_id"]][target])
        result[f"{target}_accuracy"] = round(correct / len(records), 3)
    for item in predictions:
        truth = truth_by_id[item["record_id"]]
        if all(item["prediction"][target] == truth[target] for target in TARGETS) and set(item["prediction"]["bsigma_risks"]) == set(truth["bsigma_risks"]):
            exact_all += 1
    result["all_targets_exact_match"] = round(exact_all / len(records), 3)
    result["bsigma_risks_exact_match"] = round(
        sum(1 for item in predictions if set(item["prediction"]["bsigma_risks"]) == set(truth_by_id[item["record_id"]]["bsigma_risks"])) / len(records),
        3,
    )
    result["bsigma_risks_micro_f1"] = round(micro_f1(truth_by_id, predictions), 3)
    return result


def build_bsigma_predictions(records: list[dict], predictions: list[dict]) -> list[dict]:
    by_id = {record["record_id"]: record for record in records}
    result = []
    for item in predictions:
        record = by_id[item["record_id"]]
        result.append(
            {
                "record_id": item["record_id"],
                "split": item["split"],
                "domain": item["domain"],
                "risk_level": record["labels"]["risk_level"],
                "truth": sorted(record["labels"]["bsigma_risks"]),
                "prediction": sorted(item["prediction"]["bsigma_risks"]),
            }
        )
    return result


def evaluate_bsigma_predictions(predictions: list[dict]) -> dict:
    return {
        "overall": score_bsigma_subset(predictions),
        "splits": {
            split: score_bsigma_subset([item for item in predictions if item["split"] == split])
            for split in sorted({item["split"] for item in predictions})
        },
        "per_label": {label: score_bsigma_label(predictions, label) for label in BSIGMA_LABELS},
        "confusions": build_bsigma_confusions(predictions),
    }


def score_bsigma_subset(predictions: list[dict]) -> dict:
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
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "records": len(predictions),
        "exact_match": round(exact / len(predictions), 3),
        "micro_precision": round(precision, 3),
        "micro_recall": round(recall, 3),
        "micro_f1": round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0,
    }


def score_bsigma_label(predictions: list[dict], label: str) -> dict:
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


def build_state_confusions(records: list[dict], predictions: list[dict]) -> dict:
    truth_by_id = {record["record_id"]: record["labels"] for record in records}
    confusions: dict[str, dict[str, int]] = defaultdict(Counter)
    for item in predictions:
        truth = truth_by_id[item["record_id"]]
        for target in TARGETS:
            actual = truth[target]
            predicted = item["prediction"][target]
            if actual != predicted:
                confusions[target][f"{actual}->{predicted}"] += 1
    return {target: dict(sorted(counter.items())) for target, counter in sorted(confusions.items())}


def build_bsigma_confusions(predictions: list[dict]) -> dict:
    false_positive_pairs = Counter()
    false_negative_pairs = Counter()
    critical_false_negatives = []
    for item in predictions:
        truth = set(item["truth"])
        pred = set(item["prediction"])
        for label in sorted(pred - truth):
            false_positive_pairs[(item["domain"], label)] += 1
        for label in sorted(truth - pred):
            false_negative_pairs[(item["domain"], label)] += 1
            if item.get("risk_level") == "critical":
                critical_false_negatives.append({"record_id": item["record_id"], "domain": item["domain"], "label": label})
    return {
        "false_positives_by_domain_label": {f"{domain}:{label}": count for (domain, label), count in sorted(false_positive_pairs.items())},
        "false_negatives_by_domain_label": {f"{domain}:{label}": count for (domain, label), count in sorted(false_negative_pairs.items())},
        "critical_false_negatives": critical_false_negatives,
    }


def micro_f1(truth_by_id: dict, predictions: list[dict]) -> float:
    tp = fp = fn = 0
    for item in predictions:
        truth = set(truth_by_id[item["record_id"]]["bsigma_risks"])
        pred = set(item["prediction"]["bsigma_risks"])
        tp += len(truth & pred)
        fp += len(pred - truth)
        fn += len(truth - pred)
    if tp == 0 and fp == 0 and fn == 0:
        return 1.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def build_report(
    metrics: dict,
    bsigma_metrics: dict,
    model_path: Path,
    predictions_path: Path,
    bsigma_predictions_path: Path,
    version_tag: str = VERSION_TAG,
) -> str:
    lines = [
        f"# PSM {version_tag} State Encoder Candidate Report",
        "",
        "## Summary",
        "",
        f"- Model: `{model_path}`",
        f"- Predictions: `{predictions_path}`",
        f"- B_sigma predictions: `{bsigma_predictions_path}`",
        f"- Overall records: {metrics['overall']['records']}",
        f"- All-target exact match: {metrics['overall']['all_targets_exact_match']}",
        f"- Q status accuracy: {metrics['overall']['q_status_accuracy']}",
        f"- Risk level accuracy: {metrics['overall']['risk_level_accuracy']}",
        f"- Route accuracy: {metrics['overall']['route_accuracy']}",
        f"- B_sigma status accuracy: {metrics['overall']['bsigma_status_accuracy']}",
        f"- B_sigma risks exact match: {bsigma_metrics['overall']['exact_match']}",
        f"- B_sigma risks micro F1: {bsigma_metrics['overall']['micro_f1']}",
        "",
        "## Split Metrics",
        "",
    ]
    for split, split_metrics in metrics["splits"].items():
        bsigma_split = bsigma_metrics["splits"][split]
        lines.extend(
            [
                f"### {split}",
                "",
                f"- Records: {split_metrics['records']}",
                f"- All-target exact match: {split_metrics['all_targets_exact_match']}",
                f"- Q status accuracy: {split_metrics['q_status_accuracy']}",
                f"- Risk level accuracy: {split_metrics['risk_level_accuracy']}",
                f"- Route accuracy: {split_metrics['route_accuracy']}",
                f"- B_sigma status accuracy: {split_metrics['bsigma_status_accuracy']}",
                f"- B_sigma risks exact match: {bsigma_split['exact_match']}",
                f"- B_sigma risks micro F1: {bsigma_split['micro_f1']}",
                "",
            ]
        )
    lines.extend(
        [
            "## B_sigma Confusions",
            "",
            f"- False positives by domain/label: {bsigma_metrics['confusions']['false_positives_by_domain_label']}",
            f"- False negatives by domain/label: {bsigma_metrics['confusions']['false_negatives_by_domain_label']}",
            f"- Critical false negatives: {bsigma_metrics['confusions']['critical_false_negatives']}",
            "",
            "## Boundary",
            "",
            "- This is a transparent trainable candidate, not a neural foundation model.",
            "- Rule-derived labels remain authoritative.",
            "- The candidate may be evaluated by admission gates, but passing a gate does not automatically replace the PSM rule pipeline.",
        ]
    )
    return "\n".join(lines)


def group_by(records: list[dict], key_fn) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[str(key_fn(record))].append(record)
    return dict(grouped)


def majority(values) -> str:
    counter = Counter(values)
    return sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))[0][0]


def contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def contains_language_cover(text: str) -> bool:
    filtered = text
    for phrase in LANGUAGE_COVER_META_OR_NEGATION:
        filtered = filtered.replace(phrase, "")
    return contains_any(filtered, LANGUAGE_COVER_TERMS)


def contains_overclaim(text: str) -> bool:
    filtered = text
    for phrase in OVERCLAIM_META_OR_NEGATION:
        filtered = filtered.replace(phrase, "")
    return contains_any(filtered, OVERCLAIM_TERMS)


if __name__ == "__main__":
    main()
