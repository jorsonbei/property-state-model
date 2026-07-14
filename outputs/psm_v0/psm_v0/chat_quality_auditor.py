from __future__ import annotations

import re
from collections.abc import Iterable


GENERIC_ACK_PHRASES = (
    "页面应该就是正常聊天模式",
    "頁面應該就是正常聊天模式",
    "正常聊天模式已启用",
    "正常聊天模式已啟用",
)

GENERIC_EVASION_PHRASES = (
    "我的理解是：你想让我直接回应",
    "我的理解是：你想讓我直接回應",
    "建议先分三步推进",
    "建議先分三步推進",
)

INTERNAL_DEBUG_PHRASES = (
    "PSM 门控候选回答",
    "PSM 門控候選回答",
    "B_sigma 审计状态",
    "B_sigma 審計狀態",
    "required_judges",
    "release boundary",
)


def audit_chat_answer(
    question: str,
    answer: str,
    *,
    intent: str,
    grounding_facts: Iterable[str] = (),
    grounding_sources: Iterable[str] = (),
    previous_assistant_answers: Iterable[str] = (),
    route_execution: dict | None = None,
) -> dict:
    """Audit conversational relevance separately from candidate safety."""

    text = answer.strip()
    facts = [str(item).strip() for item in grounding_facts if str(item).strip()]
    previous = [str(item).strip() for item in previous_assistant_answers if str(item).strip()]
    checks: list[dict] = []

    def add(name: str, passed: bool, expected: str, actual: str) -> None:
        checks.append(
            {
                "name": name,
                "passed": passed,
                "expected": expected,
                "actual": actual,
            }
        )

    add("non_empty", bool(text), "a non-empty conversational answer", f"characters={len(text)}")

    content_intents = {
        "project_status",
        "project_results",
        "roadmap",
        "history_reference",
        "psm_vs_llm",
        "theory",
        "repeated_question",
        "general",
    }
    generic_ack = next((phrase for phrase in GENERIC_ACK_PHRASES if phrase in text), "")
    add(
        "directness",
        intent not in content_intents or not generic_ack,
        "answer the requested content instead of describing chat mode",
        generic_ack or "no capability-only acknowledgement",
    )

    generic_evasion = next((phrase for phrase in GENERIC_EVASION_PHRASES if phrase in text), "")
    grounded_intents = {
        "project_status",
        "project_results",
        "roadmap",
        "history_reference",
        "psm_vs_llm",
        "theory",
        "general",
    }
    add(
        "non_evasion",
        intent not in grounded_intents or not generic_evasion,
        "provide the requested grounded answer",
        generic_evasion or "no generic fallback template",
    )

    missing_facts = [fact for fact in facts if fact.casefold() not in text.casefold()]
    add(
        "fact_grounding",
        not missing_facts,
        "include every required structured fact",
        "missing=" + repr(missing_facts),
    )

    debug_leaks = [
        phrase
        for phrase in INTERNAL_DEBUG_PHRASES
        if phrase.casefold() in text.casefold()
    ]
    add(
        "no_internal_debug_leakage",
        not debug_leaks,
        "keep internal audit fields out of the user-facing answer",
        "found=" + repr(debug_leaks),
    )

    normalized = normalize_text(text)
    duplicate = next((item for item in previous if normalize_text(item) == normalized), "")
    add(
        "non_duplicate",
        not duplicate,
        "do not repeat an earlier assistant answer verbatim",
        "exact_previous_match=" + str(bool(duplicate)).lower(),
    )

    coverage_markers = {
        "identity": ("物性AI",),
        "chat_capability": ("聊天",),
        "psm_vs_llm": ("物性AI", "普通大模型"),
    }.get(intent, ())
    missing_markers = [marker for marker in coverage_markers if marker.casefold() not in text.casefold()]
    add(
        "question_coverage",
        not missing_markers,
        f"cover the detected {intent} intent",
        "missing=" + repr(missing_markers),
    )

    execution = route_execution or {}
    execution_status = str(execution.get("status") or "not_available")
    false_verification = next(
        (
            phrase
            for phrase in (
                "工具检查已经通过",
                "工具檢查已經通過",
                "来源已经核实",
                "來源已經核實",
                "外部验证已经完成",
                "外部驗證已經完成",
            )
            if phrase in text
        ),
        "",
    )
    evidence_succeeded = execution_status in {
        "not_available",
        "not_required",
        "partial",
        "success",
    }
    add(
        "route_claim_integrity",
        evidence_succeeded or not false_verification,
        "do not describe missing, failed, blocked, or conflicting route evidence as verified",
        false_verification or f"route_status={execution_status}",
    )
    if execution.get("explicit_evidence_request") and execution_status in {
        "blocked",
        "conflict",
        "failed",
        "missing_evidence",
        "not_executed",
        "timeout",
    }:
        transparent = any(
            marker in text
            for marker in (
                "没有完成",
                "沒有完成",
                "缺失",
                "冲突",
                "衝突",
                "失败",
                "失敗",
                "超时",
                "超時",
                "blocked",
                "timeout",
            )
        )
        add(
            "route_failure_transparency",
            transparent,
            "surface an explicitly requested route failure in the user-facing answer",
            f"route_status={execution_status}, transparent={transparent}",
        )

    passed = sum(1 for check in checks if check["passed"])
    critical_failures = {
        check["name"]
        for check in checks
        if not check["passed"]
        and check["name"]
        in {
            "non_empty",
            "directness",
            "non_evasion",
            "fact_grounding",
            "route_claim_integrity",
            "route_failure_transparency",
        }
    }
    if critical_failures:
        status = "fail"
    elif passed == len(checks):
        status = "pass"
    else:
        status = "review"
    return {
        "status": status,
        "score": round(passed / len(checks), 4),
        "intent": intent,
        "question": question,
        "checks": checks,
        "grounding_facts": facts,
        "grounding_sources": [str(item) for item in grounding_sources],
        "route_execution_status": execution_status,
    }


def normalize_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold(), flags=re.UNICODE)
