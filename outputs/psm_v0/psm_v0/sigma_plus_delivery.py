from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from .confidence_calibration import apply_abstention, calibrated_prediction
from .shadow_state_encoder import predict_naive_bayes


SCHEMA_VERSION = "psm_sigma_plus_delivery_v1"
STRONG_CLAIM_MARKERS = re.compile(
    r"\d+(?:\.\d+)?%|PSM\s*V?\d|版本.*\d|已完成|已通过|已通過|已经|已經|当前.*(?:版本|状态|狀態)|共有|均为|均為|必须|必須|务必|務必|"
    r"保证|保證|一定|证明|證明|正式|为零|為零|critical|准确率|準確率|覆盖率|覆蓋率|法律规定|法律規定|"
    r"数据显示|數據顯示|研究表明|诊断|診斷",
    re.IGNORECASE,
)
DOWNGRADE_MARKERS = (
    "不",
    "未",
    "无",
    "無",
    "无法",
    "無法",
    "不能",
    "尚",
    "可能",
    "建议",
    "建議",
    "请",
    "請",
    "应",
    "應",
    "需",
    "若",
    "如果",
    "取决于",
    "取決於",
    "仅",
    "僅",
    "只",
    "仍",
    "暂",
    "暫",
    "候选",
    "候選",
    "风险",
    "風險",
    "边界",
    "邊界",
)
INTERNAL_DEBUG_TERMS = (
    "route_execution",
    "task_state_graph",
    "q_core",
    "delta_sigma",
    "pi_cavity",
    "b_sigma",
    "shadow",
    "abstention",
    "threshold",
    "provenance",
    "critical false negative",
    "family/source/time",
)
INTERNAL_ALLOWED_INTENTS = {"project_results", "project_status", "roadmap", "theory", "psm_vs_llm"}
PROJECT_GROUNDED_INTENTS = {"project_results", "project_status", "roadmap"}


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _sentences(answer: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[。！？!?])|\n+", answer) if item.strip()]


def _source_refs(grounding_sources: list[str], route_execution: dict) -> list[dict]:
    refs: list[dict] = []
    for source in grounding_sources:
        refs.append({"ref": str(source), "kind": "grounding_source"})
    for item in route_execution.get("provenance") or []:
        if isinstance(item, dict):
            ref = str(item.get("path") or item.get("source") or item.get("uri") or item.get("sha256") or "route_provenance")
            refs.append({"ref": ref, "kind": "route_provenance", "details": item})
    for source in route_execution.get("sources") or []:
        refs.append({"ref": str(source), "kind": "route_source"})
    deduped: dict[tuple[str, str], dict] = {}
    for item in refs:
        deduped[(item["kind"], item["ref"])] = item
    return list(deduped.values())


def _fact_matches(sentence: str, fact: str) -> bool:
    compact_fact = re.sub(r"\s+", "", str(fact)).casefold()
    compact_sentence = re.sub(r"\s+", "", sentence).casefold()
    if len(compact_fact) >= 3 and compact_fact in compact_sentence:
        return True
    tokens = {token for token in re.findall(r"[\w.]+", compact_fact) if len(token) >= 2}
    return bool(tokens) and sum(token in compact_sentence for token in tokens) >= min(2, len(tokens))


def audit_statements(
    answer: str,
    *,
    intent: str,
    grounding_facts: list[str],
    grounding_sources: list[str],
    route_execution: dict,
) -> dict:
    sources = _source_refs(grounding_sources, route_execution)
    claims = []
    for sentence in _sentences(answer):
        strong = bool(STRONG_CLAIM_MARKERS.search(sentence))
        matched_facts = [str(fact) for fact in grounding_facts if _fact_matches(sentence, str(fact))]
        route_support = route_execution.get("can_support_strong_claim") is True and bool(sources)
        source_supported = bool(sources) and (intent in PROJECT_GROUNDED_INTENTS or bool(matched_facts) or route_support)
        downgrade_markers = [marker for marker in DOWNGRADE_MARKERS if marker in sentence]
        if not strong:
            disposition = "ordinary"
        elif source_supported:
            disposition = "supported"
        elif downgrade_markers:
            disposition = "downgraded"
        else:
            disposition = "unsupported"
        claims.append(
            {
                "claim_id": _stable_id("claim", sentence),
                "text": sentence,
                "strong": strong,
                "disposition": disposition,
                "statement_level": route_execution.get("allowed_statement_level") or "C1",
                "matched_facts": matched_facts,
                "provenance_refs": [item["ref"] for item in sources] if disposition == "supported" else [],
                "downgrade_markers": downgrade_markers if disposition == "downgraded" else [],
            }
        )
    strong_claims = [item for item in claims if item["strong"]]
    unsupported = [item for item in strong_claims if item["disposition"] == "unsupported"]
    return {
        "claims": claims,
        "total_claims": len(claims),
        "strong_claims": len(strong_claims),
        "supported_strong_claims": sum(item["disposition"] == "supported" for item in strong_claims),
        "downgraded_strong_claims": sum(item["disposition"] == "downgraded" for item in strong_claims),
        "unsupported_strong_claims": len(unsupported),
        "strong_claim_coverage": 1.0 if not strong_claims else round((len(strong_claims) - len(unsupported)) / len(strong_claims), 8),
    }


def repair_user_answer(answer: str, statement_audit: dict, internal_leaks: list[str]) -> str:
    unsupported = {
        item["text"] for item in statement_audit.get("claims") or []
        if item.get("disposition") == "unsupported"
    }
    repaired: list[str] = []
    for sentence in _sentences(answer):
        if any(term.casefold() in sentence.casefold() for term in internal_leaks):
            continue
        if sentence in unsupported:
            claim = sentence.rstrip("。！？!?")
            repaired.append(f"目前缺少可核验证据，不能确认“{claim}”。")
        else:
            repaired.append(sentence)
    return "\n\n".join(repaired) if repaired else "目前缺少足够的可核验信息，不能给出确定结论。"


@lru_cache(maxsize=4)
def load_shadow_resources(psm_root: str) -> tuple[dict, dict]:
    root = Path(psm_root)
    model = json.loads((root / "runtime" / "v0_257_shadow_encoder_model.json").read_text(encoding="utf-8"))
    calibration = json.loads((root / "runtime" / "v0_258_confidence_calibration.json").read_text(encoding="utf-8"))
    return model, calibration


def calibrated_shadow_observation(request: str, route_execution: dict, model: dict, calibration: dict) -> dict:
    evidence_status = "available" if route_execution.get("sources") else "missing" if route_execution.get("status") == "failed" else "partial"
    record = {"input": {"request": request, "evidence": [{"status": evidence_status}]}}
    raw = predict_naive_bayes(model, record)
    calibrated = calibrated_prediction(raw, calibration.get("temperatures") or {})
    selective = apply_abstention(calibrated, calibration.get("thresholds") or {})
    fallback_targets = sorted(target for target, abstained in selective["abstained"].items() if abstained)
    return {
        "model_version": "PSM_V0.257-shadow",
        "calibration_version": "PSM_V0.258",
        "authority": "observation_only",
        "labels": selective["labels"],
        "confidence": selective["confidence"],
        "accepted_labels": selective["accepted_labels"],
        "abstained": selective["abstained"],
        "fallback_targets": fallback_targets,
        "controller_used": "deterministic_rule",
        "candidate_controlled_output": False,
        "rule_replacement_allowed": False,
        "training_feedback_written": False,
    }


def build_sigma_plus_delivery(
    *,
    request: str,
    answer: str,
    intent: str,
    pipeline_result: dict,
    route_execution: dict,
    task_state_graph: dict,
    grounding_facts: list[str],
    grounding_sources: list[str],
    quality_audit: dict,
    shadow_model: dict,
    calibration: dict,
) -> dict:
    packet = pipeline_result["packet"]
    statement_audit = audit_statements(
        answer,
        intent=intent,
        grounding_facts=grounding_facts,
        grounding_sources=grounding_sources,
        route_execution=route_execution,
    )
    shadow = calibrated_shadow_observation(request, route_execution, shadow_model, calibration)
    internal_leaks = [] if intent in INTERNAL_ALLOWED_INTENTS else [
        term for term in INTERNAL_DEBUG_TERMS if term.casefold() in answer.casefold()
    ]
    sources = _source_refs(grounding_sources, route_execution)
    checks = {
        "strong_claims_supported_or_downgraded": statement_audit["unsupported_strong_claims"] == 0,
        "ordinary_answer_debug_clean": not internal_leaks,
        "quality_gate_passed": quality_audit.get("status") == "pass",
        "shadow_has_no_output_authority": shadow["candidate_controlled_output"] is False,
        "deterministic_controller_retained": shadow["controller_used"] == "deterministic_rule",
        "external_release_closed": route_execution.get("external_release_authority") is False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "delivery_id": _stable_id("sigma", {"request": request, "answer": answer, "graph": task_state_graph.get("graph_id")}),
        "passed": all(checks.values()),
        "decision": "traceable_candidate_delivery" if all(checks.values()) else "delivery_rejected",
        "user_view": {"assistant_message": answer},
        "developer_view": {
            "state_chain": {
                "q_core": packet.get("q_core"),
                "omega": packet.get("omega"),
                "phi": packet.get("phi_state"),
                "delta_sigma": packet.get("delta_sigma"),
                "pi": packet.get("pi_cavity"),
                "eta": packet.get("eta"),
                "b_sigma": pipeline_result.get("bsigma_audit"),
                "sigma_plus": {"statement_level": packet.get("statement_level"), "decision": "candidate_only"},
            },
            "statement_audit": statement_audit,
            "provenance": sources,
            "tool_results": route_execution.get("adapters") or [],
            "failures": (route_execution.get("failures") or []) + (route_execution.get("failure_events") or []),
            "required_judges": route_execution.get("unresolved_judges") or [],
            "task_graph": {
                "graph_id": task_state_graph.get("graph_id"),
                "state_counts": task_state_graph.get("state_counts"),
                "next_protocol": task_state_graph.get("next_protocol"),
            },
            "calibrated_shadow_observation": shadow,
        },
        "checks": checks,
        "internal_debug_terms_in_user_view": internal_leaks,
        "release_boundary": {
            "candidate_only": True,
            "shadow_output_authority": False,
            "deterministic_rule_controller_retained": True,
            "rule_replacement_allowed": False,
            "external_user_trial_allowed": False,
            "external_release_authority": False,
        },
    }
