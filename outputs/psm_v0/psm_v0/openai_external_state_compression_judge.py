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


PACKAGE_SCHEMA = "psm_v0_277_external_state_compression_review_package_v1"
STRESS_PACKAGE_SCHEMA = "psm_v0_279_external_incremental_stress_review_package_v1"
ROLLING_PACKAGE_SCHEMA = "psm_v0_281_external_rolling_state_review_package_v1"
APPROVED_AUTHORIZATION = "approved_by_user_up_to_1000000_tokens_v0_277_synthetic_external_judge"
STRESS_APPROVED_AUTHORIZATION = "approved_by_user_up_to_1000000_tokens_v0_279_synthetic_external_judge"
ROLLING_APPROVED_AUTHORIZATION = "approved_by_user_up_to_1000000_tokens_v0_281_synthetic_external_judge"
EXPECTED_ITEMS = 10
TOKEN_AUTHORITY_LIMIT = 1_000_000
DIMENSIONS = (
    "semantic_correctness",
    "remote_state_recovery",
    "latest_correction_priority",
    "unresolved_task_recovery",
    "constraint_inheritance",
    "topic_switch_isolation",
    "answer_directness",
    "release_boundary",
)
Transport = Callable[[dict, str, str, float], tuple[dict, dict[str, str], int]]


def _package_profile(package: dict) -> tuple[str, str, int, int, str, str]:
    schema = package.get("schema_version")
    if schema == PACKAGE_SCHEMA:
        return APPROVED_AUTHORIZATION, "H", 40, 10, "V0.277", "psm_v0_277_external_state_compression_review"
    if schema == STRESS_PACKAGE_SCHEMA:
        return STRESS_APPROVED_AUTHORIZATION, "S", 80, 10, "V0.279", "psm_v0_279_external_incremental_stress_review"
    if schema == ROLLING_PACKAGE_SCHEMA:
        return ROLLING_APPROVED_AUTHORIZATION, "R", 160, 4, "V0.281", "psm_v0_281_external_rolling_state_review"
    raise ValueError("Unexpected external state-compression package schema.")


def validate_review_package(package: dict) -> None:
    expected_authorization, id_prefix, minimum_messages, expected_items, _, _ = _package_profile(package)
    expected_privacy = {
        "synthetic_only": True,
        "contains_private_data": False,
        "contains_user_documents": False,
        "contains_participant_content": False,
        "contains_secrets": False,
        "contains_local_paths": False,
        "contains_candidate_rules": False,
        "contains_hidden_labels": False,
        "contains_state_capsules": False,
        "training_eligible": False,
    }
    if package.get("privacy") != expected_privacy:
        raise ValueError("V0.277 external package privacy boundary is not closed.")
    if package.get("authorization") != expected_authorization:
        raise ValueError("External state-compression review is not authorized.")
    budget = package.get("budget") or {}
    required_budget = (
        budget.get("maximum_api_calls") == 1
        and budget.get("token_authority_limit") == TOKEN_AUTHORITY_LIMIT
        and int(budget.get("maximum_call_tokens", 0)) > 0
        and int(budget.get("reserved_total_tokens", TOKEN_AUTHORITY_LIMIT + 1)) <= TOKEN_AUTHORITY_LIMIT
        and budget.get("approval_required") is False
        and budget.get("authorization_scope") == "synthetic_external_judging_only"
    )
    if not required_budget:
        raise ValueError("V0.277 token authorization boundary is invalid.")
    payload = package.get("review_payload")
    if not isinstance(payload, dict) or canonical_sha256(payload) != package.get("review_payload_sha256"):
        raise ValueError("V0.277 review payload hash does not match.")
    if payload.get("rubric_dimensions") != list(DIMENSIONS):
        raise ValueError("V0.277 review dimensions changed.")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) != expected_items:
        raise ValueError(f"External state-compression review requires {expected_items} items.")
    expected_ids = [f"{id_prefix}{index:02d}" for index in range(1, expected_items + 1)]
    if [item.get("review_id") for item in items if isinstance(item, dict)] != expected_ids:
        raise ValueError("V0.277 review IDs or order changed.")
    required_keys = {"review_id", "family", "conversation", "final_answer"}
    for item in items:
        if set(item) != required_keys or not isinstance(item.get("final_answer"), str) or not item["final_answer"].strip():
            raise ValueError("V0.277 review item contains an unexpected or empty field.")
        conversation = item.get("conversation")
        if not isinstance(conversation, list) or len(conversation) < minimum_messages or any(
            set(message) != {"role", "content"}
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
            for message in conversation
        ):
            raise ValueError("V0.277 review conversation is malformed or too short.")
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    forbidden = (
        "sk-proj-",
        "/users/",
        "invitation_code",
        "api_key",
        "training_target",
        "expected_markers",
        "required_answer_markers",
        "required_capsule_markers",
        "user_statements",
    )
    for token in forbidden:
        if token in serialized:
            raise ValueError(f"V0.277 review package contains prohibited material: {token}")


def response_schema(expected_items: int = EXPECTED_ITEMS) -> dict:
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
                "minItems": expected_items,
                "maxItems": expected_items,
                "items": {
                    "type": "object",
                    "properties": {
                        "review_id": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["pass", "fail"]},
                        "dimension_failures": {
                            "type": "array",
                            "items": {"type": "string", "enum": list(DIMENSIONS)},
                        },
                        "finding": {"type": "string"},
                    },
                    "required": ["review_id", "verdict", "dimension_failures", "finding"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "review_payload_sha256",
            "verdict",
            "failed_item_ids",
            "critical_findings",
            "recommended_repairs",
            "item_reviews",
        ],
        "additionalProperties": False,
    }


def build_request_payload(package: dict, *, model: str = DEFAULT_MODEL) -> dict:
    validate_review_package(package)
    _, _, minimum_messages, expected_items, version_label, schema_name = _package_profile(package)
    return {
        "model": model,
        "instructions": (
            f"Act as an independent {version_label} long-horizon conversation reviewer. Review only the supplied synthetic conversations "
            "and final answers. For each item, determine whether the answer correctly recovers remote user state after "
            f"at least {minimum_messages} messages, honors the latest correction, resumes only unresolved work, inherits explicit output "
            "constraints, isolates prior topics after an explicit switch, and answers directly. Assistant statements do "
            "not override user facts. Do not assume access to implementation rules or hidden labels. Fail any material "
            "semantic defect or any implication of public release, professional authority, training authority, or rule "
            f"replacement. Return all {expected_items} review IDs exactly and in order. Overall pass requires every item to pass and "
            "no critical findings."
        ),
        "input": json.dumps(
            {
                "review_payload_sha256": package["review_payload_sha256"],
                "review_payload": package["review_payload"],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        "reasoning": {"effort": "high"},
        "max_output_tokens": 9000,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": response_schema(expected_items),
                "strict": True,
            }
        },
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


def review_state_compression_package(
    package: dict,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 300.0,
    transport: Transport | None = None,
) -> dict:
    if not api_key:
        raise ValueError("OpenAI API key is required.")
    payload = build_request_payload(package, model=model)
    _, _, _, _, version_label, _ = _package_profile(package)
    response, headers, http_status = (transport or _default_transport)(payload, api_key, endpoint, timeout)
    if http_status != 200 or response.get("status") != "completed":
        reason = (response.get("incomplete_details") or {}).get("reason") or response.get("status") or "unknown"
        raise RuntimeError(f"OpenAI {version_label} state-compression review did not complete: {reason}")
    output = _extract_output_text(response)
    if not output:
        raise RuntimeError(f"OpenAI {version_label} state-compression review returned no output.")
    try:
        review = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI {version_label} state-compression review output is not JSON.") from exc
    gate_checks = validate_external_review(review, package)
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    return {
        "schema_version": (
            "psm_v0_277_openai_external_state_compression_judge_v1"
            if version_label == "V0.277"
            else "psm_v0_279_openai_external_incremental_stress_judge_v1"
            if version_label == "V0.279"
            else "psm_v0_281_openai_external_rolling_state_judge_v1"
        ),
        "version": f"PSM_{version_label}-candidate",
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


def build_markdown_report(result: dict) -> str:
    review = result["review"]
    version_label = str(result.get("version") or "PSM_V0.277-candidate").removeprefix("PSM_").removesuffix("-candidate")
    lines = [
        f"# PSM {version_label} OpenAI External State-Compression Review",
        "",
        f"- Passed: `{result['passed']}`",
        f"- Verdict: `{review['verdict']}`",
        f"- Actual model: `{result.get('actual_model')}`",
        f"- Review payload SHA-256: `{result['review_payload_sha256']}`",
        f"- Total tokens: `{result.get('usage', {}).get('total_tokens', 0)}`",
        f"- Failed item IDs: `{review['failed_item_ids']}`",
        "",
        "## Item Reviews",
        "",
    ]
    for item in review["item_reviews"]:
        dimensions = ", ".join(item["dimension_failures"]) or "none"
        lines.append(
            f"- `{item['review_id']}`: **{item['verdict'].upper()}**; "
            f"dimension failures: `{dimensions}`; {item['finding']}"
        )
    lines.extend([
        "",
        "## Critical Findings",
        "",
        *([f"- {item}" for item in review["critical_findings"]] or ["- None."]),
        "",
        "## Recommended Repairs",
        "",
        *([f"- {item}" for item in review["recommended_repairs"]] or ["- None."]),
        "",
        "This review covers synthetic long-horizon conversations only. It grants no training, rule-replacement, public-service, or external-release authority.",
        "",
    ])
    return "\n".join(lines)
