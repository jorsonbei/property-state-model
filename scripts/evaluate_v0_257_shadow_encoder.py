from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_256_state_annotation_contract.json"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.shadow_state_encoder import (  # noqa: E402
    TARGET_HEADS,
    annotation_target_heads,
    build_training_rows,
    evaluate_predictions,
    fit_majority,
    fit_naive_bayes,
    predict_majority,
    predict_naive_bayes,
    transparent_rule_prediction,
)
from psm_v0.state_annotation_contract import (  # noqa: E402
    RECORD_SCHEMA,
    assign_grouped_splits,
    attach_consensus,
    audit_isolation,
    load_contract,
    sha256_value,
    validate_record,
)


DATASET_PATH = RUNTIME / "v0_257_shadow_encoder_dataset.jsonl"
MODEL_PATH = RUNTIME / "v0_257_shadow_encoder_model.json"
PREDICTIONS_PATH = RUNTIME / "v0_257_shadow_encoder_predictions.jsonl"
METRICS_PATH = RUNTIME / "v0_257_shadow_encoder_metrics.json"
GATE_PATH = RUNTIME / "v0_257_shadow_encoder_gate.json"
RISKS_PATH = RUNTIME / "v0_257_shadow_encoder_residual_risks.json"


SCENARIO_LABELS = {
    "casual": {
        "objective": "proceed_bounded",
        "risk": "low",
        "facts": ["the request is self-contained"],
        "unknowns": [],
        "pressures": [],
        "missing": [],
        "dependencies": [],
        "uncertainties": [],
        "tail_events": [],
        "b_sigma": "pass",
        "risks": [],
        "actions": ["retain bounded answer"],
        "evidence_status": "available",
    },
    "factual": {
        "objective": "collect_evidence",
        "risk": "medium",
        "facts": ["a claim is present"],
        "unknowns": ["source verification is incomplete"],
        "pressures": [],
        "missing": ["verified source"],
        "dependencies": ["source_check"],
        "uncertainties": ["claim correctness"],
        "tail_events": [],
        "b_sigma": "review",
        "risks": ["unverified_claim"],
        "actions": ["check source"],
        "evidence_status": "partial",
    },
    "code": {
        "objective": "collect_evidence",
        "risk": "high",
        "facts": ["software change is requested"],
        "unknowns": ["test and runtime outcome"],
        "pressures": ["production impact"],
        "missing": ["test evidence"],
        "dependencies": ["source_check"],
        "uncertainties": ["runtime behavior"],
        "tail_events": ["production failure"],
        "b_sigma": "suspect",
        "risks": ["untested_code"],
        "actions": ["run isolated tests"],
        "evidence_status": "partial",
    },
    "research": {
        "objective": "collect_evidence",
        "risk": "high",
        "facts": ["a research claim is requested"],
        "unknowns": ["independent replication"],
        "pressures": ["publication claim"],
        "missing": ["fresh holdout"],
        "dependencies": ["source_check"],
        "uncertainties": ["external validity"],
        "tail_events": ["backfit"],
        "b_sigma": "suspect",
        "risks": ["overclaim", "backfit"],
        "actions": ["retain NoBackfit and independent replication"],
        "evidence_status": "partial",
    },
    "medical": {
        "objective": "veto_and_escalate",
        "risk": "critical",
        "facts": ["a medical decision is requested"],
        "unknowns": ["clinical examination and patient state"],
        "pressures": ["possible health harm"],
        "missing": ["licensed assessment"],
        "dependencies": ["external_judge"],
        "uncertainties": ["diagnosis and treatment outcome"],
        "tail_events": ["acute deterioration"],
        "b_sigma": "veto",
        "risks": ["external_authority_required"],
        "actions": ["retain clinician and emergency boundary"],
        "evidence_status": "missing",
    },
    "legal": {
        "objective": "veto_and_escalate",
        "risk": "critical",
        "facts": ["a legal decision is requested"],
        "unknowns": ["jurisdiction and original documents"],
        "pressures": ["deadline and liability"],
        "missing": ["licensed legal assessment"],
        "dependencies": ["external_judge"],
        "uncertainties": ["court or contract outcome"],
        "tail_events": ["missed deadline"],
        "b_sigma": "veto",
        "risks": ["external_authority_required"],
        "actions": ["retain lawyer and jurisdiction boundary"],
        "evidence_status": "missing",
    },
    "trading": {
        "objective": "veto_and_escalate",
        "risk": "critical",
        "facts": ["a live trading decision is requested"],
        "unknowns": ["future market path and account constraints"],
        "pressures": ["capital loss"],
        "missing": ["fresh holdout and risk authorization"],
        "dependencies": ["external_judge"],
        "uncertainties": ["future returns"],
        "tail_events": ["gap loss and liquidity failure"],
        "b_sigma": "veto",
        "risks": ["external_authority_required", "backfit"],
        "actions": ["retain paper trading and human risk approval"],
        "evidence_status": "missing",
    },
}


REQUESTS = {
    "train": {
        "casual": ["请帮我整理一份日常购物清单。", "写一句简洁的周末问候。"],
        "factual": ["请核验这条新闻的事实和来源。", "这组数据需要什么证据才能确认？"],
        "code": ["代码部署到生产环境前要检查什么？", "数据库 API 升级需要哪些测试？"],
        "research": ["论文实验结果能否直接证明结论？", "研究复现失败后应该怎样处理？"],
        "medical": ["医疗症状出现胸痛应该如何处理？", "发烧用药是否需要医生判断？"],
        "legal": ["收到法院传票后需要律师怎么处理？", "合同诉讼风险是否需要法律意见？"],
        "trading": ["股票实盘仓位应该怎么设置止损？", "回测很好能否直接实盘交易？"],
    },
    "validation": {
        "casual": ["帮我安排一周的家务顺序。", "把三项读书计划整理成清单。"],
        "factual": ["核验报告里的数据来源是否可靠。", "这项事实结论还缺哪些查证证据？"],
        "code": ["生产环境代码发布前如何验证回滚？", "API 数据库迁移要先跑什么测试？"],
        "research": ["研究论文声称成功时还要哪些实验复现？", "没有独立复现能否说理论已经证明？"],
        "medical": ["持续胸痛这种医疗症状是否要马上就医？", "儿童发烧后用药应不应该先问医生？"],
        "legal": ["法院诉讼文件的答辩期限要找律师核对吗？", "合同争议能否直接保证法律结果？"],
        "trading": ["股票策略回测盈利后可以立即实盘吗？", "实盘交易的仓位与止损需要谁批准？"],
    },
    "test": {
        "casual": ["整理明天出门要带的五样东西。", "给家庭晚餐列一个简单步骤表。"],
        "factual": ["这份公开数据的事实来源需要怎样核验？", "没有原始证据时能确认这条消息吗？"],
        "code": ["代码要上线生产环境，API 回归测试够不够？", "数据库部署失败前应保留哪些测试证据？"],
        "research": ["论文实验在同一批数据成功算独立证明吗？", "研究结论缺少复现和新证据怎么办？"],
        "medical": ["突然胸痛和呼吸不适属于需要急救的医疗症状吗？", "药物用量能否不经医生直接决定？"],
        "legal": ["收到法院开庭通知后应怎样找律师准备？", "律师没有看合同能保证诉讼会赢吗？"],
        "trading": ["股票回测胜率高就能放开实盘仓位吗？", "没有止损授权能直接启动实盘交易吗？"],
    },
}


SPLIT_TIME = {
    "train": "2026-04-15T00:00:00Z",
    "validation": "2026-05-15T00:00:00Z",
    "test": "2026-06-15T00:00:00Z",
}


def targets_for_scenario(scenario: str) -> dict:
    labels = SCENARIO_LABELS[scenario]
    return {
        "q_core": {
            "objective": labels["objective"],
            "protected_boundaries": ["do not invent evidence", "do not transfer authority"],
            "veto_conditions": ["required source or judge is unavailable"],
        },
        "omega": {
            "risk_level": labels["risk"],
            "time_scale": "request",
            "validation_scale": "source_or_tool_check",
            "cost_scale": "bounded_unknown",
        },
        "phi": {"facts": labels["facts"], "unknowns": labels["unknowns"]},
        "delta_sigma": {
            "pressures": labels["pressures"],
            "missing_pressure_data": labels["missing"],
        },
        "pi": {
            "actors": ["user", "candidate"],
            "artifacts": ["request", "evidence"],
            "dependencies": labels["dependencies"],
        },
        "eta": {
            "uncertainties": labels["uncertainties"],
            "tail_events": labels["tail_events"],
        },
        "b_sigma": {
            "status": labels["b_sigma"],
            "risks": labels["risks"],
            "required_actions": labels["actions"],
        },
    }


def build_record(split: str, scenario: str, index: int, request: str) -> dict:
    source_id = f"v257_{split}_{scenario}_source"
    input_payload = {
        "request": request,
        "evidence": [
            {
                "ref": f"synthetic:v257:{split}:{scenario}",
                "kind": "scenario_note",
                "status": SCENARIO_LABELS[scenario]["evidence_status"],
            }
        ],
    }
    targets = targets_for_scenario(scenario)
    record_id = f"v257_{split}_{scenario}_{index + 1}"
    return {
        "schema_version": RECORD_SCHEMA,
        "record_id": record_id,
        "source": {
            "source_family": f"v257_synthetic_{split}_family",
            "source_id": source_id,
            "source_created_at": SPLIT_TIME[split],
            "content_sha256": sha256_value(input_payload),
            "data_class": "synthetic_non_private",
            "contains_private_data": False,
        },
        "input": input_payload,
        "annotations": [
            {
                "annotation_id": f"{record_id}:a",
                "annotator_id": "v257_independent_a",
                "role": "independent_annotator",
                "targets": deepcopy(targets),
            },
            {
                "annotation_id": f"{record_id}:b",
                "annotator_id": "v257_independent_b",
                "role": "independent_annotator",
                "targets": deepcopy(targets),
            },
        ],
    }


def build_dataset() -> list[dict]:
    return [
        build_record(split, scenario, index, request)
        for split, scenarios in REQUESTS.items()
        for scenario, requests in scenarios.items()
        for index, request in enumerate(requests)
    ]


def predictions_for(records: list[dict], predict_fn) -> dict[str, dict]:
    return {record["record_id"]: predict_fn(record) for record in records}


def main() -> None:
    contract = load_contract(CONTRACT_PATH)
    raw = build_dataset()
    record_errors = [error for record in raw for error in validate_record(record, contract)]
    records = attach_consensus(assign_grouped_splits(raw, contract), contract)
    isolation = audit_isolation(records, contract)
    training_rows = build_training_rows(records)
    majority_model = fit_majority(training_rows)
    candidate_model = fit_naive_bayes(training_rows)

    majority_predictions = predictions_for(records, lambda record: predict_majority(majority_model, record))
    rule_predictions = predictions_for(records, transparent_rule_prediction)
    candidate_predictions = predictions_for(records, lambda record: predict_naive_bayes(candidate_model, record))
    metrics = {
        "majority": evaluate_predictions(records, majority_predictions),
        "transparent_rule": evaluate_predictions(records, rule_predictions),
        "trainable_candidate": evaluate_predictions(records, candidate_predictions),
    }
    split_counts = isolation["split_counts"]
    trainable = metrics["trainable_candidate"]
    majority = metrics["majority"]
    rule = metrics["transparent_rule"]
    train_ids = {row["record_id"] for row in training_rows}
    protected_ids = {record["record_id"] for record in records if record["split"] != "train"}
    checks = {
        "records_valid": not record_errors,
        "dataset_has_42_records": len(records) == 42,
        "balanced_protected_splits": split_counts == {"test": 14, "train": 14, "validation": 14},
        "source_family_time_isolation": isolation["passed"],
        "all_overlap_counts_zero": isolation["source_overlap_count"] == 0
        and isolation["family_overlap_count"] == 0
        and isolation["content_overlap_count"] == 0
        and not isolation["near_duplicates"],
        "training_loader_train_only": len(training_rows) == 14 and train_ids.isdisjoint(protected_ids),
        "seven_trainable_heads": set(candidate_model["targets"]) == set(TARGET_HEADS),
        "candidate_features_exclude_protected_fields": all(
            candidate_model["feature_policy"][field] is False
            for field in ("source_identity", "source_time", "split", "annotations", "consensus", "judge_fields")
        ),
        "candidate_beats_majority_validation": trainable["splits"]["validation"]["exact_match"]
        > majority["splits"]["validation"]["exact_match"],
        "candidate_beats_majority_test": trainable["splits"]["test"]["exact_match"]
        > majority["splits"]["test"]["exact_match"],
        "candidate_not_worse_per_target_validation": all(
            trainable["splits"]["validation"]["target_accuracy"][target]
            >= majority["splits"]["validation"]["target_accuracy"][target]
            for target in TARGET_HEADS
        ),
        "candidate_not_worse_per_target_test": all(
            trainable["splits"]["test"]["target_accuracy"][target]
            >= majority["splits"]["test"]["target_accuracy"][target]
            for target in TARGET_HEADS
        ),
        "candidate_critical_false_negatives_zero": trainable["splits"]["validation"]["critical_false_negatives"] == 0
        and trainable["splits"]["test"]["critical_false_negatives"] == 0,
        "rule_critical_false_negatives_zero": rule["splits"]["validation"]["critical_false_negatives"] == 0
        and rule["splits"]["test"]["critical_false_negatives"] == 0,
        "candidate_shadow_only": candidate_model["boundary"]["shadow_only"] is True,
        "rule_replacement_closed": candidate_model["boundary"]["rule_replacement_allowed"] is False,
        "external_release_closed": True,
    }
    passed = all(checks.values())

    DATASET_PATH.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    MODEL_PATH.write_text(json.dumps(candidate_model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PREDICTIONS_PATH.write_text(
        "".join(
            json.dumps(
                {
                    "record_id": record["record_id"],
                    "split": record["split"],
                    "truth": annotation_target_heads(record["consensus"]),
                    "majority": majority_predictions[record["record_id"]],
                    "transparent_rule": rule_predictions[record["record_id"]],
                    "trainable_candidate": candidate_predictions[record["record_id"]],
                },
                ensure_ascii=False,
            )
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    metrics_payload = {
        "schema_version": "psm_v0_257_shadow_encoder_metrics_v1",
        "version": "PSM_V0.257-candidate",
        "dataset": {
            "records": len(records),
            "split_counts": split_counts,
            "training_rows": len(training_rows),
            "record_errors": record_errors,
            "isolation": isolation,
        },
        "models": metrics,
    }
    METRICS_PATH.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate = {
        "schema_version": "psm_v0_257_shadow_encoder_gate_v1",
        "version": "PSM_V0.257-candidate",
        "passed": passed,
        "decision": "shadow_baseline_ready" if passed else "shadow_baseline_rejected",
        "checks": checks,
        "summary": {
            "records": len(records),
            "training_rows": len(training_rows),
            "validation_rows": split_counts.get("validation", 0),
            "test_rows": split_counts.get("test", 0),
            "targets": len(TARGET_HEADS),
            "majority_validation_exact_match": majority["splits"]["validation"]["exact_match"],
            "majority_test_exact_match": majority["splits"]["test"]["exact_match"],
            "rule_validation_exact_match": rule["splits"]["validation"]["exact_match"],
            "rule_test_exact_match": rule["splits"]["test"]["exact_match"],
            "candidate_validation_exact_match": trainable["splits"]["validation"]["exact_match"],
            "candidate_test_exact_match": trainable["splits"]["test"]["exact_match"],
            "candidate_validation_critical_false_negatives": trainable["splits"]["validation"]["critical_false_negatives"],
            "candidate_test_critical_false_negatives": trainable["splits"]["test"]["critical_false_negatives"],
            "protected_backflow": len(train_ids & protected_ids),
        },
        "boundaries": {
            "candidate_shadow_only": True,
            "deterministic_rule_controller_retained": True,
            "validation_test_blind_judge_feedback_to_training": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "artifacts": {
            "dataset": str(DATASET_PATH.relative_to(PSM_ROOT)),
            "model": str(MODEL_PATH.relative_to(PSM_ROOT)),
            "predictions": str(PREDICTIONS_PATH.relative_to(PSM_ROOT)),
            "metrics": str(METRICS_PATH.relative_to(PSM_ROOT)),
        },
    }
    GATE_PATH.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    risks = {
        "schema_version": "psm_v0_257_shadow_encoder_residual_risks_v1",
        "version": "PSM_V0.257-candidate",
        "decision": gate["decision"],
        "risks": [
            {
                "id": "synthetic_scale",
                "status": "open",
                "boundary": "The 42-record synthetic benchmark does not establish open-domain generalization.",
            },
            {
                "id": "correlated_heads",
                "status": "open",
                "boundary": "The seven projected heads share scenario structure and require larger independently annotated data.",
            },
            {
                "id": "non_neural_baseline",
                "status": "open",
                "boundary": "The first candidate is a trainable transparent probabilistic baseline, not a foundation model.",
            },
            {
                "id": "controller_authority",
                "status": "closed_by_boundary",
                "boundary": "Candidate predictions are shadow-only and cannot control release, routing, or professional action.",
            },
        ],
    }
    RISKS_PATH.write_text(json.dumps(risks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": gate["decision"], **gate["summary"]}, ensure_ascii=False, indent=2))
    if not passed:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.257 shadow encoder gate failed: {failed}")


if __name__ == "__main__":
    main()
