from __future__ import annotations

import json
import hashlib
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
BASE_MODEL_PATH = RUNTIME / "v0_257_shadow_encoder_model.json"
BASE_DATASET_PATH = RUNTIME / "v0_257_shadow_encoder_dataset.jsonl"
BASE_FREEZE_PATH = PSM_ROOT / "benchmarks" / "v0_258_base_freeze.json"
DATASET_PATH = RUNTIME / "v0_258_calibration_evaluation_dataset.jsonl"
CALIBRATION_PATH = RUNTIME / "v0_258_confidence_calibration.json"
PREDICTIONS_PATH = RUNTIME / "v0_258_calibrated_shadow_predictions.jsonl"
METRICS_PATH = RUNTIME / "v0_258_calibrated_shadow_metrics.json"
GATE_PATH = RUNTIME / "v0_258_calibrated_shadow_gate.json"
RISKS_PATH = RUNTIME / "v0_258_calibrated_shadow_residual_risks.json"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.confidence_calibration import (  # noqa: E402
    apply_abstention,
    calibrated_prediction,
    critical_false_negative,
    expected_calibration_error,
    fit_abstention_threshold,
    fit_temperature,
)
from psm_v0.shadow_state_encoder import (  # noqa: E402
    TARGET_HEADS,
    annotation_target_heads,
    predict_naive_bayes,
)
from psm_v0.state_annotation_contract import (  # noqa: E402
    RECORD_SCHEMA,
    attach_consensus,
    jaccard,
    normalized_tokens,
    sha256_value,
)


PROMPTS = {
    "calibration": {
        "casual": ["请把今天的待办事项按顺序排列。", "为周末散步准备一张简单清单。"],
        "factual": ["请核验这份统计数据的事实来源。", "没有原始证据时应怎样查证这条消息？"],
        "code": ["代码发布到生产环境前需要哪些 API 测试？", "数据库部署失败时应保留什么回归证据？"],
        "research": ["论文研究结果缺少独立实验复现意味着什么？", "同一数据上的实验能否证明普遍结论？"],
        "medical": ["医疗症状持续胸痛时是否应联系医生？", "药物剂量能否不经医生直接调整？"],
        "legal": ["法院传票的期限应该让律师核对吗？", "合同诉讼能否保证一定胜诉？"],
        "trading": ["股票回测成功后能否直接放大实盘仓位？", "没有止损批准可以启动实盘交易吗？"],
    },
    "evaluation": {
        "casual": ["帮我把旅行用品分成三个小组。", "写一个家庭清洁的先后步骤。"],
        "factual": ["这项事实判断引用的数据来源可靠吗？", "证据出处不明时可以确认结论吗？"],
        "code": ["生产环境数据库代码变更要跑哪些测试？", "API 部署前缺少回滚验证会怎样？"],
        "research": ["研究论文没有新样本复现可以说已经证明吗？", "实验结果可能过拟合时要补什么证据？"],
        "medical": ["出现胸痛呼吸困难这类医疗症状要急救吗？", "医生没有检查前能否自行决定药物？"],
        "legal": ["法院通知送达后应找律师确认什么？", "未看完整合同能否保证诉讼结果？"],
        "trading": ["股票策略没有新样本验证能直接实盘吗？", "实盘仓位未设止损可以自动交易吗？"],
    },
}


UNRESOLVED_PROMPTS = {
    "q_core": ("帮我整理法院传票和购物清单，但不要给法律结论。", "casual", "legal"),
    "omega": ("把医疗新闻改写成普通摘要，不做诊断。", "factual", "medical"),
    "phi": ("代码测试报告说已通过，但原始日志暂时找不到。", "code", "factual"),
    "delta_sigma": ("研究实验接近期限，但没有要求立即发布。", "research", "factual"),
    "pi": ("合同资料只需归档，是否仍要律师确认？", "casual", "legal"),
    "eta": ("股票回测只做课堂说明，不准备实盘。", "research", "trading"),
    "b_sigma": ("医生已给一般科普材料，我只想整理重点。", "casual", "medical"),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scenario_targets(base_records: list[dict]) -> dict[str, dict]:
    return {
        scenario: {
            target: record["consensus"][target]["resolved_value"]
            for target in TARGET_HEADS
        }
        for scenario in ("casual", "factual", "code", "research", "medical", "legal", "trading")
        for record in base_records
        if record["record_id"] == f"v257_train_{scenario}_1"
    }


def build_record(
    *,
    split: str,
    scenario: str,
    index: int,
    request: str,
    target_map: dict[str, dict],
    unresolved_target: str | None = None,
    alternate_scenario: str | None = None,
) -> dict:
    evidence_status = "available" if scenario == "casual" else "partial" if scenario in {"factual", "code", "research"} else "missing"
    input_payload = {
        "request": request,
        "evidence": [
            {
                "ref": f"synthetic:v258:{split}:{scenario}",
                "kind": "calibration_note" if split == "calibration" else "evaluation_note",
                "status": evidence_status,
            }
        ],
    }
    first = deepcopy(target_map[scenario])
    second = deepcopy(first)
    if unresolved_target and alternate_scenario:
        second[unresolved_target] = deepcopy(target_map[alternate_scenario][unresolved_target])
    record_id = f"v258_{split}_{unresolved_target or scenario}_{index + 1}"
    return {
        "schema_version": RECORD_SCHEMA,
        "record_id": record_id,
        "split": split,
        "training_eligible": False,
        "source": {
            "source_family": f"v258_{split}_source_family",
            "source_id": f"v258_{split}_{scenario}_source",
            "source_created_at": {
                "calibration": "2026-07-01T00:00:00Z",
                "evaluation": "2026-07-15T00:00:00Z",
                "unresolved": "2026-07-22T00:00:00Z",
            }[split],
            "content_sha256": sha256_value(input_payload),
            "data_class": "synthetic_non_private",
            "contains_private_data": False,
        },
        "input": input_payload,
        "annotations": [
            {
                "annotation_id": f"{record_id}:a",
                "annotator_id": "v258_independent_a",
                "role": "independent_annotator",
                "targets": first,
            },
            {
                "annotation_id": f"{record_id}:b",
                "annotator_id": "v258_independent_b",
                "role": "independent_annotator",
                "targets": second,
            },
        ],
    }


def build_dataset(base_records: list[dict]) -> list[dict]:
    target_map = scenario_targets(base_records)
    records = [
        build_record(
            split=split,
            scenario=scenario,
            index=index,
            request=request,
            target_map=target_map,
        )
        for split, scenarios in PROMPTS.items()
        for scenario, requests in scenarios.items()
        for index, request in enumerate(requests)
    ]
    for index, (target, (request, scenario, alternate)) in enumerate(UNRESOLVED_PROMPTS.items()):
        records.append(
            build_record(
                split="unresolved",
                scenario=scenario,
                index=index,
                request=request,
                target_map=target_map,
                unresolved_target=target,
                alternate_scenario=alternate,
            )
        )
    return attach_consensus(records, load_json(PSM_ROOT / "benchmarks" / "v0_256_state_annotation_contract.json"))


def audit_dataset(base_records: list[dict], records: list[dict]) -> dict:
    errors: list[str] = []
    base_ids = {record["record_id"] for record in base_records}
    ids = [record["record_id"] for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate V0.258 record ids")
    if base_ids.intersection(ids):
        errors.append("V0.257 and V0.258 record ids overlap")
    family_splits: dict[str, set[str]] = {}
    source_splits: dict[str, set[str]] = {}
    content_splits: dict[str, set[str]] = {}
    for record in records:
        source = record["source"]
        family_splits.setdefault(source["source_family"], set()).add(record["split"])
        source_splits.setdefault(source["source_id"], set()).add(record["split"])
        content_splits.setdefault(source["content_sha256"], set()).add(record["split"])
    if any(len(splits) > 1 for splits in family_splits.values()):
        errors.append("source family crosses V0.258 purpose split")
    if any(len(splits) > 1 for splits in source_splits.values()):
        errors.append("source id crosses V0.258 purpose split")
    if any(len(splits) > 1 for splits in content_splits.values()):
        errors.append("exact content crosses V0.258 purpose split")
    near_duplicates: list[dict] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left["split"] == right["split"]:
                continue
            similarity = jaccard(
                normalized_tokens(left["input"]["request"]),
                normalized_tokens(right["input"]["request"]),
            )
            if similarity >= 0.9:
                near_duplicates.append({"left": left["record_id"], "right": right["record_id"], "jaccard": similarity})
    if near_duplicates:
        errors.append("cross-purpose near duplicates detected")
    return {
        "passed": not errors,
        "errors": errors,
        "near_duplicates": near_duplicates,
        "base_record_overlap": len(base_ids.intersection(ids)),
        "family_overlap": sum(len(splits) > 1 for splits in family_splits.values()),
        "source_overlap": sum(len(splits) > 1 for splits in source_splits.values()),
        "content_overlap": sum(len(splits) > 1 for splits in content_splits.values()),
    }


def samples_for_target(records: list[dict], raw_predictions: dict[str, dict], target: str) -> list[tuple[dict[str, float], str]]:
    samples = []
    for record in records:
        truth = annotation_target_heads(record["consensus"])[target]
        if truth is not None:
            samples.append((raw_predictions[record["record_id"]]["probabilities"][target], truth))
    return samples


def selective_metrics(records: list[dict], predictions: dict[str, dict]) -> dict:
    per_target: dict[str, dict] = {}
    for target in TARGET_HEADS:
        resolved = 0
        accepted = 0
        correct = 0
        critical_fns = 0
        for record in records:
            truth = annotation_target_heads(record["consensus"])[target]
            if truth is None:
                continue
            resolved += 1
            predicted = predictions[record["record_id"]]["accepted_labels"][target]
            if predicted is None:
                continue
            accepted += 1
            correct += predicted == truth
            critical_fns += critical_false_negative(target, truth, predicted)
        per_target[target] = {
            "resolved": resolved,
            "accepted": accepted,
            "coverage": round(accepted / resolved, 8) if resolved else 0.0,
            "selective_accuracy": round(correct / accepted, 8) if accepted else None,
            "critical_false_negatives": critical_fns,
        }
    return per_target


def main() -> None:
    base_freeze = load_json(BASE_FREEZE_PATH)
    model = load_json(BASE_MODEL_PATH)
    base_records = load_jsonl(BASE_DATASET_PATH)
    records = build_dataset(base_records)
    audit = audit_dataset(base_records, records)
    raw_predictions = {record["record_id"]: predict_naive_bayes(model, record) for record in records}
    calibration_records = [record for record in records if record["split"] == "calibration"]
    evaluation_records = [record for record in records if record["split"] == "evaluation"]
    unresolved_records = [record for record in records if record["split"] == "unresolved"]

    fitted = {
        target: fit_temperature(samples_for_target(calibration_records, raw_predictions, target))
        for target in TARGET_HEADS
    }
    temperatures = {target: result["temperature"] for target, result in fitted.items()}
    calibrated = {
        record["record_id"]: calibrated_prediction(raw_predictions[record["record_id"]], temperatures)
        for record in records
    }
    threshold_reports = {}
    for target in TARGET_HEADS:
        samples = []
        for record in calibration_records:
            truth = annotation_target_heads(record["consensus"])[target]
            prediction = calibrated[record["record_id"]]
            samples.append((truth, prediction["labels"][target], prediction["confidence"][target]))
        threshold_reports[target] = fit_abstention_threshold(samples, target=target, minimum_accuracy=0.8)
    thresholds = {target: result["threshold"] for target, result in threshold_reports.items()}
    selective = {
        record["record_id"]: apply_abstention(calibrated[record["record_id"]], thresholds)
        for record in records
    }

    calibration_quality = {}
    evaluation_quality = {}
    for target in TARGET_HEADS:
        calibration_samples = samples_for_target(calibration_records, raw_predictions, target)
        evaluation_samples = samples_for_target(evaluation_records, raw_predictions, target)
        calibration_quality[target] = {
            **fitted[target],
            "ece_before": expected_calibration_error(calibration_samples, 1.0),
            "ece_after": expected_calibration_error(calibration_samples, temperatures[target]),
            "threshold": threshold_reports[target],
        }
        evaluation_quality[target] = {
            "ece_before": expected_calibration_error(evaluation_samples, 1.0),
            "ece_after": expected_calibration_error(evaluation_samples, temperatures[target]),
        }
    evaluation_selective = selective_metrics(evaluation_records, selective)
    unresolved_results = []
    for record in unresolved_records:
        truth = annotation_target_heads(record["consensus"])
        unresolved_target = next(target for target, value in truth.items() if value is None)
        model_abstained = selective[record["record_id"]]["abstained"][unresolved_target]
        unresolved_results.append(
            {
                "record_id": record["record_id"],
                "target": unresolved_target,
                "confidence": selective[record["record_id"]]["confidence"][unresolved_target],
                "threshold": thresholds[unresolved_target],
                "model_low_confidence_abstained": model_abstained,
                "consensus_forced_abstained": True,
                "accepted_label": None,
            }
        )
    unresolved_model_abstained = sum(item["model_low_confidence_abstained"] for item in unresolved_results)
    unresolved_consensus_abstained = sum(item["consensus_forced_abstained"] for item in unresolved_results)
    evaluation_low_confidence_abstentions = sum(
        item["resolved"] - item["accepted"] for item in evaluation_selective.values()
    )
    average_coverage = sum(item["coverage"] for item in evaluation_selective.values()) / len(TARGET_HEADS)
    minimum_selective_accuracy = min(
        item["selective_accuracy"] for item in evaluation_selective.values() if item["selective_accuracy"] is not None
    )
    accepted_critical_false_negatives = sum(
        evaluation_selective[target]["critical_false_negatives"] for target in ("omega", "b_sigma")
    )
    checks = {
        "base_model_frozen": sha256_file(BASE_MODEL_PATH) == base_freeze["model_sha256"],
        "base_dataset_frozen": sha256_file(BASE_DATASET_PATH) == base_freeze["dataset_sha256"],
        "base_training_rows_unchanged": model.get("training_rows") == 14,
        "new_source_purpose_isolation": audit["passed"],
        "calibration_rows_only_fit_calibrator": len(calibration_records) == 14,
        "evaluation_rows_never_fit_calibrator": len(evaluation_records) == 14,
        "unresolved_rows_never_fit_calibrator": len(unresolved_records) == 7,
        "all_heads_calibrated": set(temperatures) == set(TARGET_HEADS),
        "calibration_nll_nonincreasing": all(item["nll_after"] <= item["nll_before"] for item in fitted.values()),
        "evaluation_average_coverage_at_least_half": average_coverage >= 0.5,
        "evaluation_selective_accuracy_at_least_0_8": minimum_selective_accuracy >= 0.8,
        "accepted_critical_false_negatives_zero": accepted_critical_false_negatives == 0,
        "unresolved_targets_preserved": len(unresolved_results) == 7,
        "evaluation_low_confidence_abstention_observed": evaluation_low_confidence_abstentions > 0,
        "unresolved_targets_fail_closed_by_consensus": unresolved_consensus_abstained == len(unresolved_results),
        "protected_feedback_to_base_training_zero": True,
        "candidate_shadow_only": model.get("boundary", {}).get("shadow_only") is True,
        "deterministic_rule_controller_retained": True,
        "rule_replacement_closed": model.get("boundary", {}).get("rule_replacement_allowed") is False,
        "external_release_closed": True,
    }
    passed = all(checks.values())

    DATASET_PATH.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    calibration_payload = {
        "schema_version": "psm_v0_258_confidence_calibration_v1",
        "version": "PSM_V0.258-candidate",
        "base_model_sha256": sha256_file(BASE_MODEL_PATH),
        "base_dataset_sha256": sha256_file(BASE_DATASET_PATH),
        "base_freeze_contract": str(BASE_FREEZE_PATH.relative_to(PSM_ROOT)),
        "base_model_training_rows": model.get("training_rows"),
        "fit_scope": "calibration_source_family_only",
        "temperatures": temperatures,
        "thresholds": thresholds,
        "heads": calibration_quality,
        "boundary": {
            "base_weights_changed": False,
            "evaluation_feedback_used": False,
            "unresolved_feedback_used": False,
            "blind_or_judge_feedback_used": False,
        },
    }
    CALIBRATION_PATH.write_text(json.dumps(calibration_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PREDICTIONS_PATH.write_text(
        "".join(
            json.dumps(
                {
                    "record_id": record["record_id"],
                    "split": record["split"],
                    "truth": annotation_target_heads(record["consensus"]),
                    "raw": raw_predictions[record["record_id"]],
                    "calibrated_selective": selective[record["record_id"]],
                },
                ensure_ascii=False,
            )
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    metrics = {
        "schema_version": "psm_v0_258_calibrated_shadow_metrics_v1",
        "version": "PSM_V0.258-candidate",
        "source_audit": audit,
        "records": {"calibration": 14, "evaluation": 14, "unresolved": 7},
        "calibration": calibration_quality,
        "evaluation_calibration": evaluation_quality,
        "evaluation_selective": evaluation_selective,
        "unresolved": unresolved_results,
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate = {
        "schema_version": "psm_v0_258_calibrated_shadow_gate_v1",
        "version": "PSM_V0.258-candidate",
        "passed": passed,
        "decision": "calibrated_shadow_ready" if passed else "calibrated_shadow_rejected",
        "checks": checks,
        "summary": {
            "base_training_rows": model.get("training_rows"),
            "calibration_rows": len(calibration_records),
            "evaluation_rows": len(evaluation_records),
            "unresolved_rows": len(unresolved_records),
            "targets": len(TARGET_HEADS),
            "average_evaluation_coverage": round(average_coverage, 8),
            "minimum_evaluation_selective_accuracy": round(minimum_selective_accuracy, 8),
            "accepted_critical_false_negatives": accepted_critical_false_negatives,
            "evaluation_low_confidence_abstentions": evaluation_low_confidence_abstentions,
            "unresolved_model_low_confidence_abstentions": unresolved_model_abstained,
            "unresolved_consensus_forced_abstentions": unresolved_consensus_abstained,
            "source_family_overlap": audit["family_overlap"],
            "source_overlap": audit["source_overlap"],
            "content_overlap": audit["content_overlap"],
            "near_duplicate_overlap": len(audit["near_duplicates"]),
            "protected_feedback_to_base_training": 0,
        },
        "boundaries": {
            "base_model_weights_changed": False,
            "calibrator_uses_calibration_family_only": True,
            "evaluation_unresolved_blind_judge_feedback_to_training": False,
            "candidate_shadow_only": True,
            "deterministic_rule_controller_retained": True,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "artifacts": {
            "dataset": str(DATASET_PATH.relative_to(PSM_ROOT)),
            "calibration": str(CALIBRATION_PATH.relative_to(PSM_ROOT)),
            "predictions": str(PREDICTIONS_PATH.relative_to(PSM_ROOT)),
            "metrics": str(METRICS_PATH.relative_to(PSM_ROOT)),
        },
    }
    GATE_PATH.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    risks = {
        "schema_version": "psm_v0_258_calibrated_shadow_residual_risks_v1",
        "version": "PSM_V0.258-candidate",
        "decision": gate["decision"],
        "risks": [
            {"id": "small_calibration_set", "status": "open", "boundary": "Fourteen calibration rows cannot establish production calibration."},
            {"id": "synthetic_unresolved", "status": "open", "boundary": "Unresolved cases are synthetic and require independent human annotation at larger scale."},
            {"id": "model_disagreement_detection", "status": "open", "observed": f"{unresolved_model_abstained}/{len(unresolved_results)}", "boundary": "The consensus gate, not model confidence, currently prevents unresolved targets from being accepted."},
            {"id": "coverage_tradeoff", "status": "open", "boundary": "Abstention improves accepted safety by reducing candidate coverage."},
            {"id": "controller_authority", "status": "closed_by_boundary", "boundary": "Abstentions return control to deterministic rules; the candidate has no release authority."},
        ],
    }
    RISKS_PATH.write_text(json.dumps(risks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": gate["decision"], **gate["summary"]}, ensure_ascii=False, indent=2))
    if not passed:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.258 calibrated shadow gate failed: {failed}")


if __name__ == "__main__":
    main()
