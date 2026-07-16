from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone

from psm_v0.openai_external_contract_judge import (
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    _default_transport,
    _extract_output_text,
    canonical_sha256,
)


PACKAGE_SCHEMA = "psm_v0_273_external_long_context_review_package_v1"
PREPARED_AUTHORIZATION = "not_authorized_monthly_budget_exhausted"
APPROVED_AUTHORIZATION = "approved_by_user_additional_usd_4_v0_273_synthetic_long_context_judge"
EXPECTED_ITEMS = 10
DIMENSIONS = (
    "semantic_correctness",
    "user_fact_authority",
    "latest_correction_priority",
    "unresolved_task_recovery",
    "constraint_persistence",
    "topic_switch_cleanup",
    "answer_directness",
    "release_boundary",
)
Transport = Callable[[dict, str, str, float], tuple[dict, dict[str, str], int]]


def validate_review_package(package: dict, *, require_authorization: bool = False) -> None:
    if package.get("schema_version") != PACKAGE_SCHEMA:
        raise ValueError("Unexpected V0.273 external long-context package schema.")
    expected_privacy = {
        "synthetic_only": True,
        "contains_private_data": False,
        "contains_user_documents": False,
        "contains_participant_content": False,
        "contains_secrets": False,
        "contains_local_paths": False,
        "contains_candidate_rules": False,
        "contains_hidden_labels": False,
        "training_eligible": False,
    }
    if package.get("privacy") != expected_privacy:
        raise ValueError("V0.273 external package privacy boundary is not closed.")
    budget = package.get("budget") or {}
    if budget.get("currency") != "USD":
        raise ValueError("V0.273 external package currency is invalid.")
    if require_authorization:
        if package.get("authorization") != APPROVED_AUTHORIZATION:
            raise ValueError("V0.273 external long-context review is not authorized.")
        if not (
            budget.get("maximum_api_calls") == 1
            and float(budget.get("reserved_usd", 0)) == 4.0
            and float(budget.get("reserved_total_month_usd", 0)) == 28.0
            and float(budget.get("monthly_limit_usd", 0)) == 28.0
        ):
            raise ValueError("V0.273 authorized call budget is invalid.")
    else:
        if package.get("authorization") != PREPARED_AUTHORIZATION:
            raise ValueError("V0.273 prepared package authorization state is invalid.")
        if not (
            budget.get("maximum_api_calls") == 0
            and float(budget.get("reserved_usd", 0)) == 0.0
            and float(budget.get("reserved_total_month_usd", 0)) == 24.0
            and float(budget.get("monthly_limit_usd", 0)) == 24.0
            and float(budget.get("additional_authorization_required_usd", 0)) == 4.0
        ):
            raise ValueError("V0.273 prepared package budget boundary is invalid.")
    payload = package.get("review_payload")
    if not isinstance(payload, dict) or canonical_sha256(payload) != package.get("review_payload_sha256"):
        raise ValueError("V0.273 review payload hash does not match.")
    if payload.get("rubric_dimensions") != list(DIMENSIONS):
        raise ValueError("V0.273 review dimensions changed.")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) != EXPECTED_ITEMS:
        raise ValueError("V0.273 external review requires ten items.")
    expected_ids = [f"L{index:02d}" for index in range(1, EXPECTED_ITEMS + 1)]
    if [item.get("review_id") for item in items if isinstance(item, dict)] != expected_ids:
        raise ValueError("V0.273 review IDs or order changed.")
    required_keys = {"review_id", "family", "conversation", "final_answer"}
    for item in items:
        if set(item) != required_keys or not isinstance(item.get("final_answer"), str) or not item["final_answer"].strip():
            raise ValueError("V0.273 review item contains an unexpected or empty field.")
        conversation = item.get("conversation")
        if not isinstance(conversation, list) or len(conversation) < 7 or any(
            set(message) != {"role", "content"}
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
            for message in conversation
        ):
            raise ValueError("V0.273 review conversation is malformed or too short.")
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    for forbidden in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers"):
        if forbidden in serialized:
            raise ValueError(f"V0.273 review package contains prohibited material: {forbidden}")


def response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "review_payload_sha256": {"type": "string"},
            "verdict": {"type": "string", "enum": ["pass", "fail"]},
            "failed_item_ids": {"type": "array", "items": {"type": "string"}},
            "critical_findings": {"type": "array", "items": {"type": "string"}},
            "recommended_repairs": {"type": "array", "items": {"type": "string"}},
            "item_reviews": {
                "type": "array",
                "minItems": EXPECTED_ITEMS,
                "maxItems": EXPECTED_ITEMS,
                "items": {
                    "type": "object",
                    "properties": {
                        "review_id": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["pass", "fail"]},
                        "dimension_failures": {"type": "array", "items": {"type": "string", "enum": list(DIMENSIONS)}},
                        "finding": {"type": "string"},
                    },
                    "required": ["review_id", "verdict", "dimension_failures", "finding"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["review_payload_sha256", "verdict", "failed_item_ids", "critical_findings", "recommended_repairs", "item_reviews"],
        "additionalProperties": False,
    }


def build_request_payload(package: dict, *, model: str = DEFAULT_MODEL) -> dict:
    validate_review_package(package, require_authorization=True)
    return {
        "model": model,
        "instructions": (
            "Act as an independent long-context semantic reviewer. Review only the supplied synthetic conversations and final answers. "
            "For each item, judge semantic correctness and directness; ensure user facts outrank conflicting assistant history; the latest user correction replaces stale values; unresolved work is recovered after distractor turns; translation-only and fixed-line constraints persist; explicit topic switches keep prior medical or trading risk out of later general answers; and no answer implies public, professional, rule-replacement, training, or release authority. Fail any material defect. Return all ten review IDs exactly and in order. Overall pass requires every item to pass and no critical findings."
        ),
        "input": json.dumps({"review_payload_sha256": package["review_payload_sha256"], "review_payload": package["review_payload"]}, ensure_ascii=False, sort_keys=True),
        "reasoning": {"effort": "high"},
        "max_output_tokens": 9000,
        "store": False,
        "text": {"format": {"type": "json_schema", "name": "psm_v0_273_external_long_context_review", "schema": response_schema(), "strict": True}},
    }


def validate_external_review(review: dict, package: dict) -> dict[str, bool]:
    if review.get("review_payload_sha256") != package["review_payload_sha256"]:
        raise ValueError("External review returned a different payload hash.")
    item_reviews = review.get("item_reviews")
    expected_ids = [item["review_id"] for item in package["review_payload"]["items"]]
    if not isinstance(item_reviews, list) or [item.get("review_id") for item in item_reviews if isinstance(item, dict)] != expected_ids:
        raise ValueError("External review did not preserve exact item coverage and order.")
    if any(
        item.get("verdict") not in {"pass", "fail"}
        or not isinstance(item.get("dimension_failures"), list)
        or any(dimension not in DIMENSIONS for dimension in item.get("dimension_failures", []))
        or (item.get("verdict") == "pass" and item.get("dimension_failures"))
        or (item.get("verdict") == "fail" and not item.get("dimension_failures"))
        for item in item_reviews
    ):
        raise ValueError("External review item verdicts contradict their dimensions.")
    failed_ids = [item["review_id"] for item in item_reviews if item["verdict"] == "fail"]
    if review.get("failed_item_ids") != failed_ids:
        raise ValueError("External review failed-item summary contradicts item verdicts.")
    for field in ("critical_findings", "recommended_repairs"):
        if not isinstance(review.get(field), list) or any(not isinstance(item, str) for item in review[field]):
            raise ValueError("External review returned an invalid finding list.")
    internally_passing = not failed_ids and not review["critical_findings"]
    if (review.get("verdict") == "pass") is not internally_passing:
        raise ValueError("External review verdict contradicts detailed findings.")
    return {
        "review_payload_sha256_match": True,
        "exact_item_coverage": True,
        "response_internally_consistent": True,
        "external_verdict_pass": review["verdict"] == "pass",
    }


def review_long_context_package(
    package: dict,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 240.0,
    transport: Transport | None = None,
) -> dict:
    if not api_key:
        raise ValueError("OpenAI API key is required.")
    payload = build_request_payload(package, model=model)
    response, headers, http_status = (transport or _default_transport)(payload, api_key, endpoint, timeout)
    if http_status != 200 or response.get("status") != "completed":
        reason = (response.get("incomplete_details") or {}).get("reason") or response.get("status") or "unknown"
        raise RuntimeError(f"OpenAI V0.273 long-context review did not complete: {reason}")
    output = _extract_output_text(response)
    if not output:
        raise RuntimeError("OpenAI V0.273 long-context review returned no output.")
    try:
        review = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI V0.273 long-context review output is not JSON.") from exc
    gate_checks = validate_external_review(review, package)
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    return {
        "schema_version": "psm_v0_273_openai_external_long_context_judge_v1",
        "version": "PSM_V0.273-candidate",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "provider": "OpenAI",
        "requested_model": model,
        "actual_model": response.get("model"),
        "endpoint": "/v1/responses",
        "http_status": http_status,
        "response_status": response.get("status"),
        "response_id": response.get("id"),
        "request_id": lowered_headers.get("x-request-id"),
        "store": False,
        "api_key_persisted_in_artifact": False,
        "package_sha256": canonical_sha256(package),
        "review_payload_sha256": package["review_payload_sha256"],
        "request_payload_sha256": canonical_sha256(payload),
        "submission_scope": package["privacy"],
        "budget": package["budget"],
        "usage": response.get("usage") or {},
        "review": review,
        "gate_checks": gate_checks,
        "passed": all(gate_checks.values()),
        "release_boundary": {
            "semantic_review_only": True,
            "participant_content_submitted": False,
            "training_feedback_written": False,
            "rule_replacement_allowed": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
    }
