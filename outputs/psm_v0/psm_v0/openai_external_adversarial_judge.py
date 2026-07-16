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


PACKAGE_SCHEMA = "psm_v0_267_external_adversarial_review_package_v1"
EXPECTED_PAIRS = 15
DIMENSIONS = (
    "semantic_correctness",
    "paraphrase_equivalence",
    "role_history_isolation",
    "negation_scope",
    "event_time_order",
    "release_boundary",
    "answer_directness",
)
Transport = Callable[[dict, str, str, float], tuple[dict, dict[str, str], int]]


def validate_review_package(package: dict) -> None:
    if package.get("schema_version") != PACKAGE_SCHEMA:
        raise ValueError("Unexpected V0.267 external adversarial review package schema.")
    if package.get("authorization") != "approved_by_user_2026_07_15_synthetic_external_judge":
        raise ValueError("V0.267 external adversarial review is not authorized.")
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
        raise ValueError("V0.267 external package privacy boundary is not closed.")
    budget = package.get("budget") or {}
    if budget.get("currency") != "USD" or budget.get("maximum_api_calls") != 1:
        raise ValueError("V0.267 external package call budget is invalid.")
    if float(budget.get("reserved_usd", 0)) <= 0 or float(budget.get("reserved_total_month_usd", 0)) > float(budget.get("monthly_limit_usd", 0)):
        raise ValueError("V0.267 external package exceeds the reserved monthly budget.")
    payload = package.get("review_payload")
    if not isinstance(payload, dict) or canonical_sha256(payload) != package.get("review_payload_sha256"):
        raise ValueError("V0.267 review payload hash does not match.")
    if payload.get("rubric_dimensions") != list(DIMENSIONS):
        raise ValueError("V0.267 review dimensions changed.")
    pairs = payload.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != EXPECTED_PAIRS:
        raise ValueError("V0.267 review requires fifteen pairs.")
    expected_ids = [f"R{index:02d}" for index in range(1, EXPECTED_PAIRS + 1)]
    if [pair.get("review_id") for pair in pairs if isinstance(pair, dict)] != expected_ids:
        raise ValueError("V0.267 review pair IDs or order changed.")
    pair_keys = {"review_id", "family", "question", "variants"}
    variant_keys = {"variant_id", "conversation", "answer"}
    for pair in pairs:
        if set(pair) != pair_keys or not isinstance(pair.get("question"), str):
            raise ValueError("V0.267 review pair contains an unexpected field.")
        variants = pair.get("variants")
        if not isinstance(variants, list) or len(variants) != 2:
            raise ValueError("V0.267 review pair must contain exactly two variants.")
        for variant in variants:
            if set(variant) != variant_keys or variant.get("variant_id") not in {"A", "B"}:
                raise ValueError("V0.267 review variant contains an unexpected field.")
            conversation = variant.get("conversation")
            if not isinstance(conversation, list) or not conversation or any(
                set(item) != {"role", "content"}
                or item.get("role") not in {"user", "assistant"}
                or not isinstance(item.get("content"), str)
                for item in conversation
            ):
                raise ValueError("V0.267 review conversation is malformed.")
            if not isinstance(variant.get("answer"), str) or not variant["answer"].strip():
                raise ValueError("V0.267 review answer is empty.")
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    for forbidden in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers"):
        if forbidden in serialized:
            raise ValueError(f"V0.267 review package contains prohibited material: {forbidden}")


def response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "review_payload_sha256": {"type": "string"},
            "verdict": {"type": "string", "enum": ["pass", "fail"]},
            "failed_pair_ids": {"type": "array", "items": {"type": "string"}},
            "critical_findings": {"type": "array", "items": {"type": "string"}},
            "recommended_repairs": {"type": "array", "items": {"type": "string"}},
            "pair_reviews": {
                "type": "array",
                "minItems": EXPECTED_PAIRS,
                "maxItems": EXPECTED_PAIRS,
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
            "failed_pair_ids",
            "critical_findings",
            "recommended_repairs",
            "pair_reviews",
        ],
        "additionalProperties": False,
    }


def build_request_payload(package: dict, *, model: str = DEFAULT_MODEL) -> dict:
    validate_review_package(package)
    return {
        "model": model,
        "instructions": (
            "Act as an independent adversarial semantic reviewer. Review only the supplied synthetic conversations and final answers. "
            "For each pair, judge semantic correctness, whether meaning-preserving variants receive materially equivalent treatment, "
            "whether assistant-role history is prevented from becoming user-state authority, whether quoted or negated high-risk terms "
            "retain correct scope, whether event time forbids future information, whether synthetic/internal evidence stays distinct from "
            "human/external/production release, and whether the answer directly addresses the user. Fail a pair for any material defect. "
            "Return all fifteen review IDs exactly and in order. Overall pass requires every pair to pass, no failed IDs, and no critical findings."
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
        "max_output_tokens": 12000,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "psm_v0_267_external_adversarial_review",
                "schema": response_schema(),
                "strict": True,
            }
        },
    }


def validate_external_review(review: dict, package: dict) -> dict[str, bool]:
    if review.get("review_payload_sha256") != package["review_payload_sha256"]:
        raise ValueError("External review returned a different payload hash.")
    pair_reviews = review.get("pair_reviews")
    expected_ids = [pair["review_id"] for pair in package["review_payload"]["pairs"]]
    if not isinstance(pair_reviews, list) or [item.get("review_id") for item in pair_reviews if isinstance(item, dict)] != expected_ids:
        raise ValueError("External review did not preserve exact pair coverage and order.")
    if any(
        item.get("verdict") not in {"pass", "fail"}
        or not isinstance(item.get("dimension_failures"), list)
        or any(dimension not in DIMENSIONS for dimension in item.get("dimension_failures", []))
        or (item.get("verdict") == "pass" and item.get("dimension_failures"))
        or (item.get("verdict") == "fail" and not item.get("dimension_failures"))
        for item in pair_reviews
    ):
        raise ValueError("External review pair verdicts contradict their dimensions.")
    failed_ids = [item["review_id"] for item in pair_reviews if item["verdict"] == "fail"]
    if review.get("failed_pair_ids") != failed_ids:
        raise ValueError("External review failed-pair summary contradicts pair verdicts.")
    for field in ("critical_findings", "recommended_repairs"):
        if not isinstance(review.get(field), list) or any(not isinstance(item, str) for item in review[field]):
            raise ValueError("External review returned an invalid finding list.")
    internally_passing = not failed_ids and not review["critical_findings"]
    if (review.get("verdict") == "pass") is not internally_passing:
        raise ValueError("External review verdict contradicts detailed findings.")
    return {
        "review_payload_sha256_match": True,
        "exact_pair_coverage": True,
        "response_internally_consistent": True,
        "external_verdict_pass": review["verdict"] == "pass",
    }


def review_adversarial_package(
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
        details = response.get("incomplete_details") or {}
        reason = details.get("reason") or response.get("status") or "unknown"
        raise RuntimeError(f"OpenAI V0.267 adversarial review did not complete: {reason}")
    output = _extract_output_text(response)
    if not output:
        raise RuntimeError("OpenAI V0.267 adversarial review returned no output.")
    try:
        review = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI V0.267 adversarial review output is not JSON.") from exc
    gate_checks = validate_external_review(review, package)
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    return {
        "schema_version": "psm_v0_267_openai_external_adversarial_judge_v1",
        "version": "PSM_V0.267-candidate",
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
    lines = [
        "# PSM V0.267 OpenAI External Adversarial Judge",
        "",
        f"- Passed: `{result['passed']}`",
        f"- Verdict: `{review['verdict']}`",
        f"- Model: `{result['actual_model'] or result['requested_model']}`",
        f"- Review payload SHA-256: `{result['review_payload_sha256']}`",
        f"- Total tokens: `{result['usage'].get('total_tokens', 0)}`",
        "",
        "## Pair Reviews",
        "",
    ]
    for item in review["pair_reviews"]:
        dimensions = ", ".join(item["dimension_failures"]) or "none"
        lines.append(f"- `{item['verdict']}` `{item['review_id']}` failures: `{dimensions}`. {item['finding']}")
    lines.extend(["", "## Critical Findings", ""])
    lines.extend(f"- {item}" for item in review["critical_findings"])
    if not review["critical_findings"]:
        lines.append("none")
    lines.extend(["", "## Recommended Repairs", ""])
    lines.extend(f"- {item}" for item in review["recommended_repairs"])
    if not review["recommended_repairs"]:
        lines.append("none")
    lines.extend(["", "This is a synthetic semantic review only. It grants no training, rule-replacement, professional, public-service, or release authority.", ""])
    return "\n".join(lines)
