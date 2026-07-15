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


PACKAGE_SCHEMA = "psm_v0_262_external_trial_protocol_review_package_v1"
EXPECTED_QUESTIONS = 7
Transport = Callable[[dict, str, str, float], tuple[dict, dict[str, str], int]]


def validate_review_package(package: dict) -> None:
    if package.get("schema_version") != PACKAGE_SCHEMA:
        raise ValueError("Unexpected V0.262 external trial review package schema.")
    if package.get("authorization") != "approved_by_user_2026_07_15_conservative_plan":
        raise ValueError("V0.262 external protocol review is not authorized.")
    expected_privacy = {
        "contains_private_data": False,
        "contains_user_documents": False,
        "contains_participant_content": False,
        "contains_secrets": False,
        "synthetic_only": True,
    }
    if package.get("privacy") != expected_privacy:
        raise ValueError("V0.262 external protocol review is not synthetic-only.")
    protocol = package.get("protocol")
    if not isinstance(protocol, dict) or protocol.get("status") != "frozen":
        raise ValueError("V0.262 external trial protocol is missing or not frozen.")
    if canonical_sha256(protocol) != package.get("protocol_sha256"):
        raise ValueError("V0.262 external trial protocol hash does not match.")
    questions = package.get("independent_review_questions")
    if not isinstance(questions, list) or len(questions) != EXPECTED_QUESTIONS or len(set(questions)) != EXPECTED_QUESTIONS:
        raise ValueError("V0.262 review requires seven unique questions.")
    if any(not isinstance(question, str) or not question.strip() for question in questions):
        raise ValueError("V0.262 review questions must be non-empty text.")
    boundary = protocol.get("release_boundary") or {}
    prohibited = (
        "participant_enrollment_completed",
        "public_service_allowed",
        "privacy_compliance_claimed",
        "production_readiness_claimed",
        "medical_legal_trading_authority",
        "training_on_trial_data_allowed",
        "rule_replacement_allowed",
        "external_release_authority",
    )
    if any(boundary.get(name) is not False for name in prohibited):
        raise ValueError("V0.262 protocol opens a prohibited authority.")


def response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "protocol_sha256": {"type": "string"},
            "verdict": {"type": "string", "enum": ["pass", "fail"]},
            "failed_checks": {"type": "array", "items": {"type": "string"}},
            "critical_findings": {"type": "array", "items": {"type": "string"}},
            "recommended_repairs": {"type": "array", "items": {"type": "string"}},
            "question_reviews": {
                "type": "array",
                "minItems": EXPECTED_QUESTIONS,
                "maxItems": EXPECTED_QUESTIONS,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["pass", "fail"]},
                        "finding": {"type": "string"},
                    },
                    "required": ["question", "verdict", "finding"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "protocol_sha256", "verdict", "failed_checks", "critical_findings",
            "recommended_repairs", "question_reviews",
        ],
        "additionalProperties": False,
    }


def build_request_payload(package: dict, *, model: str = DEFAULT_MODEL) -> dict:
    validate_review_package(package)
    review_input = {
        "protocol_sha256": package["protocol_sha256"],
        "protocol": package["protocol"],
        "independent_review_questions": package["independent_review_questions"],
    }
    return {
        "model": model,
        "instructions": (
            "Act as an independent privacy, safety, and trial-governance reviewer. Review only the supplied frozen protocol, not its local "
            "gate summary or user authorization. Fail ambiguities that could permit public exposure, non-consenting or minor participants, "
            "sensitive data, raw-content retention, participant-content API submission, retention beyond seven days, budget overrun, "
            "automatic incident recovery, professional authority, trial-data training, rule replacement, or release authority. Repeat all "
            "seven questions exactly and in order. Pass requires seven passing question verdicts and no failed or critical findings."
        ),
        "input": json.dumps(review_input, ensure_ascii=False, sort_keys=True),
        "reasoning": {"effort": "high"},
        "max_output_tokens": 10000,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "psm_v0_262_external_trial_protocol_review",
                "schema": response_schema(),
                "strict": True,
            }
        },
    }


def validate_external_review(review: dict, package: dict) -> dict[str, bool]:
    if review.get("protocol_sha256") != package["protocol_sha256"]:
        raise ValueError("External review returned a different protocol hash.")
    question_reviews = review.get("question_reviews")
    if not isinstance(question_reviews, list) or [item.get("question") for item in question_reviews if isinstance(item, dict)] != package["independent_review_questions"]:
        raise ValueError("External review did not preserve exact question coverage and order.")
    list_fields = [review.get(name) for name in ("failed_checks", "critical_findings", "recommended_repairs")]
    if any(not isinstance(items, list) or any(not isinstance(item, str) for item in items) for items in list_fields):
        raise ValueError("External review returned an invalid list field.")
    verdict = review.get("verdict")
    question_verdicts = [item.get("verdict") for item in question_reviews]
    if verdict not in {"pass", "fail"} or any(item not in {"pass", "fail"} for item in question_verdicts):
        raise ValueError("External review returned an invalid verdict.")
    internally_passing = not review["failed_checks"] and not review["critical_findings"] and all(item == "pass" for item in question_verdicts)
    if (verdict == "pass") is not internally_passing:
        raise ValueError("External review verdict contradicts detailed findings.")
    return {
        "protocol_sha256_match": True,
        "exact_question_coverage": True,
        "response_internally_consistent": True,
        "external_verdict_pass": verdict == "pass",
    }


def review_protocol(
    package: dict,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 180.0,
    transport: Transport | None = None,
) -> dict:
    if not api_key:
        raise ValueError("OpenAI API key is required.")
    payload = build_request_payload(package, model=model)
    response, headers, http_status = (transport or _default_transport)(payload, api_key, endpoint, timeout)
    if http_status != 200 or response.get("status") != "completed":
        details = response.get("incomplete_details") or {}
        reason = details.get("reason") or response.get("status") or "unknown"
        raise RuntimeError(f"OpenAI V0.262 protocol review did not complete: {reason}")
    output = _extract_output_text(response)
    if not output:
        raise RuntimeError("OpenAI V0.262 protocol review returned no output.")
    try:
        review = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI V0.262 protocol review output is not JSON.") from exc
    gate_checks = validate_external_review(review, package)
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    return {
        "schema_version": "psm_v0_262_openai_external_trial_protocol_judge_v1",
        "version": "PSM_V0.262",
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
        "protocol_sha256": package["protocol_sha256"],
        "request_payload_sha256": canonical_sha256(payload),
        "submission_scope": package["privacy"],
        "usage": response.get("usage") or {},
        "review": review,
        "gate_checks": gate_checks,
        "passed": all(gate_checks.values()),
        "release_boundary": {
            "protocol_review_only": True,
            "participant_content_submitted": False,
            "participant_enrollment_completed": False,
            "public_service_allowed": False,
            "privacy_compliance_claimed": False,
            "external_release_authority": False,
        },
    }


def build_markdown_report(result: dict) -> str:
    review = result["review"]
    lines = [
        "# PSM V0.262 OpenAI External Trial Protocol Judge",
        "",
        f"- Passed: `{result['passed']}`",
        f"- Verdict: `{review['verdict']}`",
        f"- Model: `{result['actual_model'] or result['requested_model']}`",
        f"- Protocol SHA-256: `{result['protocol_sha256']}`",
        f"- Total tokens: `{result['usage'].get('total_tokens', 0)}`",
        "",
        "## Independent Questions",
        "",
    ]
    for item in review["question_reviews"]:
        lines.append(f"- `{item['verdict']}` {item['question']} {item['finding']}")
    lines.extend(["", "## Critical Findings", ""])
    lines.extend(f"- {item}" for item in review["critical_findings"])
    if not review["critical_findings"]:
        lines.append("none")
    lines.extend(["", "## Recommended Repairs", ""])
    lines.extend(f"- {item}" for item in review["recommended_repairs"])
    if not review["recommended_repairs"]:
        lines.append("none")
    lines.extend(["", "This review contains only a synthetic protocol. It does not enroll participants, authorize public service, or establish privacy compliance.", ""])
    return "\n".join(lines)
