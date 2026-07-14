from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


TARGET_HEADS = ("q_core", "omega", "phi", "delta_sigma", "pi", "eta", "b_sigma")


def annotation_target_heads(consensus: dict) -> dict[str, str | None]:
    values = {
        target: consensus[target].get("resolved_value")
        if consensus[target].get("status") == "resolved"
        else None
        for target in TARGET_HEADS
    }
    return {
        "q_core": values["q_core"].get("objective") if values["q_core"] else None,
        "omega": values["omega"].get("risk_level") if values["omega"] else None,
        "phi": phi_head(values["phi"]),
        "delta_sigma": delta_sigma_head(values["delta_sigma"]),
        "pi": pi_head(values["pi"]),
        "eta": eta_head(values["eta"]),
        "b_sigma": values["b_sigma"].get("status") if values["b_sigma"] else None,
    }


def phi_head(value: dict | None) -> str | None:
    if value is None:
        return None
    facts = value.get("facts") or []
    unknowns = value.get("unknowns") or []
    if facts and not unknowns:
        return "grounded"
    if facts and unknowns:
        return "partial"
    return "unknown"


def delta_sigma_head(value: dict | None) -> str | None:
    if value is None:
        return None
    pressures = value.get("pressures") or []
    missing = value.get("missing_pressure_data") or []
    if not pressures and not missing:
        return "stable"
    if not pressures and missing:
        return "incomplete"
    return "pressured"


def pi_head(value: dict | None) -> str | None:
    if value is None:
        return None
    dependencies = set(value.get("dependencies") or [])
    if "external_judge" in dependencies:
        return "external_judge"
    if "source_check" in dependencies:
        return "source_check"
    return "ready"


def eta_head(value: dict | None) -> str | None:
    if value is None:
        return None
    if value.get("tail_events"):
        return "tail_risk"
    if value.get("uncertainties"):
        return "uncertain"
    return "bounded"


def request_features(record: dict) -> Counter[str]:
    # Source identity, split, annotations, consensus, and judge fields are intentionally excluded.
    request = str(record.get("input", {}).get("request") or "").casefold()
    evidence_states = sorted(
        str(item.get("status") or "unknown").casefold()
        for item in record.get("input", {}).get("evidence", [])
        if isinstance(item, dict)
    )
    compact = re.sub(r"\s+", "", request)
    features: Counter[str] = Counter()
    for token in re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]", request):
        features[f"token:{token}"] += 1
    for width in (2, 3):
        for index in range(max(0, len(compact) - width + 1)):
            features[f"char{width}:{compact[index:index + width]}"] += 1
    for state in evidence_states:
        features[f"evidence:{state}"] += 1
    return features


def build_training_rows(records: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for record in records:
        if record.get("split") != "train" or record.get("training_eligible") is not True:
            continue
        labels = annotation_target_heads(record["consensus"])
        if any(value is None for value in labels.values()):
            continue
        rows.append(
            {
                "record_id": record["record_id"],
                "features": dict(request_features(record)),
                "labels": labels,
            }
        )
    return rows


def fit_majority(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Cannot fit a majority model without training rows.")
    labels: dict[str, str] = {}
    for target in TARGET_HEADS:
        counts = Counter(row["labels"][target] for row in rows)
        labels[target] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {"model_type": "majority", "training_rows": len(rows), "labels": labels}


def predict_majority(model: dict, record: dict) -> dict:
    del record
    return {
        "labels": dict(model["labels"]),
        "confidence": {target: 1.0 for target in TARGET_HEADS},
    }


def fit_naive_bayes(rows: list[dict], alpha: float = 1.0) -> dict:
    if not rows:
        raise ValueError("Cannot fit a trainable model without training rows.")
    vocabulary = sorted({token for row in rows for token in row["features"]})
    targets: dict[str, dict[str, Any]] = {}
    for target in TARGET_HEADS:
        class_rows: dict[str, list[dict]] = {}
        for row in rows:
            class_rows.setdefault(row["labels"][target], []).append(row)
        classes: dict[str, dict] = {}
        for label, label_rows in sorted(class_rows.items()):
            counts: Counter[str] = Counter()
            for row in label_rows:
                counts.update(row["features"])
            classes[label] = {
                "documents": len(label_rows),
                "total_tokens": sum(counts.values()),
                "token_counts": dict(sorted(counts.items())),
            }
        targets[target] = {"documents": len(rows), "classes": classes}
    return {
        "schema_version": "psm_shadow_multinomial_nb_v1",
        "model_type": "trainable_multinomial_naive_bayes",
        "training_rows": len(rows),
        "alpha": alpha,
        "vocabulary": vocabulary,
        "targets": targets,
        "feature_policy": {
            "request_text": True,
            "evidence_status": True,
            "source_identity": False,
            "source_time": False,
            "split": False,
            "annotations": False,
            "consensus": False,
            "judge_fields": False,
        },
        "boundary": {"shadow_only": True, "rule_replacement_allowed": False},
    }


def predict_naive_bayes(model: dict, record: dict) -> dict:
    features = request_features(record)
    vocabulary = set(model["vocabulary"])
    vocabulary_size = max(1, len(model["vocabulary"]))
    predictions: dict[str, str] = {}
    confidence: dict[str, float] = {}
    probabilities: dict[str, dict[str, float]] = {}
    for target in TARGET_HEADS:
        target_model = model["targets"][target]
        classes = target_model["classes"]
        class_count = len(classes)
        scores: dict[str, float] = {}
        for label, data in classes.items():
            prior = (data["documents"] + model["alpha"]) / (
                target_model["documents"] + model["alpha"] * class_count
            )
            score = math.log(prior)
            denominator = data["total_tokens"] + model["alpha"] * vocabulary_size
            token_counts = data["token_counts"]
            for token, count in features.items():
                if token not in vocabulary:
                    continue
                probability = (token_counts.get(token, 0) + model["alpha"]) / denominator
                score += count * math.log(probability)
            scores[label] = score
        selected = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
        maximum = max(scores.values())
        exp_scores = {label: math.exp(score - maximum) for label, score in scores.items()}
        total = sum(exp_scores.values())
        predictions[target] = selected
        confidence[target] = round(exp_scores[selected] / total if total else 0.0, 6)
        probabilities[target] = {
            label: round(value / total if total else 0.0, 8)
            for label, value in sorted(exp_scores.items())
        }
    return {"labels": predictions, "confidence": confidence, "probabilities": probabilities}


def transparent_rule_prediction(record: dict) -> dict:
    text = str(record.get("input", {}).get("request") or "").casefold()
    critical_markers = (
        "医疗",
        "症状",
        "胸痛",
        "发烧",
        "用药",
        "药物",
        "医生",
        "急救",
        "法院",
        "传票",
        "律师",
        "诉讼",
        "合同",
        "实盘",
        "仓位",
        "股票",
        "止损",
        "medical",
        "legal",
        "trading",
    )
    high_markers = (
        "代码",
        "部署",
        "生产环境",
        "数据库",
        "api",
        "论文",
        "实验",
        "研究",
        "复现",
        "证明",
    )
    factual_markers = ("来源", "事实", "证据", "数据", "查证", "核验")
    if any(marker in text for marker in critical_markers):
        scenario = "critical"
    elif any(marker in text for marker in high_markers):
        scenario = "high"
    elif any(marker in text for marker in factual_markers):
        scenario = "factual"
    else:
        scenario = "casual"
    labels = {
        "casual": {
            "q_core": "proceed_bounded",
            "omega": "low",
            "phi": "grounded",
            "delta_sigma": "stable",
            "pi": "ready",
            "eta": "bounded",
            "b_sigma": "pass",
        },
        "factual": {
            "q_core": "collect_evidence",
            "omega": "medium",
            "phi": "partial",
            "delta_sigma": "incomplete",
            "pi": "source_check",
            "eta": "uncertain",
            "b_sigma": "review",
        },
        "high": {
            "q_core": "collect_evidence",
            "omega": "high",
            "phi": "partial",
            "delta_sigma": "pressured",
            "pi": "source_check",
            "eta": "tail_risk",
            "b_sigma": "suspect",
        },
        "critical": {
            "q_core": "veto_and_escalate",
            "omega": "critical",
            "phi": "partial",
            "delta_sigma": "pressured",
            "pi": "external_judge",
            "eta": "tail_risk",
            "b_sigma": "veto",
        },
    }[scenario]
    return {
        "labels": labels,
        "confidence": {target: 1.0 for target in TARGET_HEADS},
        "scenario": scenario,
    }


def evaluate_predictions(records: list[dict], predictions: dict[str, dict]) -> dict:
    result: dict[str, Any] = {"splits": {}, "overall": {}}
    for split in ("train", "validation", "test"):
        subset = [record for record in records if record.get("split") == split]
        result["splits"][split] = score_subset(subset, predictions)
    result["overall"] = score_subset(records, predictions)
    return result


def score_subset(records: list[dict], predictions: dict[str, dict]) -> dict:
    scored = 0
    exact = 0
    per_target_correct = Counter()
    per_target_scored = Counter()
    unresolved = 0
    critical_false_negatives = 0
    critical_cases = 0
    for record in records:
        truth = annotation_target_heads(record["consensus"])
        predicted = predictions[record["record_id"]]["labels"]
        resolved_pairs = [(target, value) for target, value in truth.items() if value is not None]
        unresolved += sum(value is None for value in truth.values())
        if resolved_pairs:
            scored += 1
            if all(predicted[target] == value for target, value in resolved_pairs):
                exact += 1
        for target, value in resolved_pairs:
            per_target_scored[target] += 1
            per_target_correct[target] += predicted[target] == value
        if truth["omega"] == "critical":
            critical_cases += 1
            if predicted["omega"] != "critical" or predicted["b_sigma"] != "veto":
                critical_false_negatives += 1
    return {
        "records": len(records),
        "scored_records": scored,
        "unresolved_targets": unresolved,
        "exact_match": round(exact / scored, 6) if scored else None,
        "target_accuracy": {
            target: round(per_target_correct[target] / per_target_scored[target], 6)
            if per_target_scored[target]
            else None
            for target in TARGET_HEADS
        },
        "critical_cases": critical_cases,
        "critical_false_negatives": critical_false_negatives,
    }
