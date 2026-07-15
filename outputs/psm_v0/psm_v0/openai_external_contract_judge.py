from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any


DEFAULT_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.4"
EXPECTED_PACKAGE_SCHEMAS = {
    "psm_v0_256_external_contract_review_package_v1",
    "psm_v0_261_external_contract_review_package_v1",
}
EXPECTED_QUESTIONS = 5

Transport = Callable[[dict, str, str, float], tuple[dict, dict[str, str], int]]


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_review_package(package: dict) -> None:
    if package.get("schema_version") not in EXPECTED_PACKAGE_SCHEMAS:
        raise ValueError("Unexpected external contract review package schema.")
    if package.get("authorization") != "authorized_by_user_2026_07_14":
        raise ValueError("External submission is not explicitly authorized.")

    privacy = package.get("privacy") or {}
    expected_privacy = {
        "contains_private_data": False,
        "contains_user_documents": False,
        "contains_secrets": False,
        "synthetic_only": True,
    }
    if privacy != expected_privacy:
        raise ValueError("External review package does not satisfy the synthetic-only privacy gate.")

    contract = package.get("contract")
    if not isinstance(contract, dict) or contract.get("status") != "frozen":
        raise ValueError("External review contract must be present and frozen.")
    if canonical_sha256(contract) != package.get("contract_sha256"):
        raise ValueError("External review contract SHA-256 does not match the frozen package.")

    boundaries = contract.get("boundaries") or {}
    required_true = (
        "no_target_read",
        "no_backfit",
        "blind_and_test_no_backflow",
        "judge_only_separate",
        "candidate_shadow_only",
    )
    if any(boundaries.get(name) is not True for name in required_true):
        raise ValueError("Frozen contract is missing a required closed-loop boundary.")
    required_false = (
        "rule_replacement_allowed",
        "training_allowed_before_contract_gate",
        "external_release_authority",
    )
    if any(boundaries.get(name) is not False for name in required_false):
        raise ValueError("Frozen contract opens a prohibited authority.")

    questions = package.get("independent_review_questions")
    if (
        not isinstance(questions, list)
        or len(questions) != EXPECTED_QUESTIONS
        or len(set(questions)) != EXPECTED_QUESTIONS
        or any(not isinstance(question, str) or not question.strip() for question in questions)
    ):
        raise ValueError("External review package must contain five unique review questions.")

    required_response = package.get("required_response") or {}
    if required_response.get("verdict") != ["pass", "fail"]:
        raise ValueError("External review verdict contract is invalid.")
    if any(required_response.get(name) != "list" for name in ("failed_checks", "critical_findings", "recommended_repairs")):
        raise ValueError("External review list response contract is invalid.")


def response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "contract_sha256": {"type": "string"},
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
            "contract_sha256",
            "verdict",
            "failed_checks",
            "critical_findings",
            "recommended_repairs",
            "question_reviews",
        ],
        "additionalProperties": False,
    }


def build_request_payload(package: dict, *, model: str = DEFAULT_MODEL) -> dict:
    validate_review_package(package)
    review_input = {
        "contract_sha256": package["contract_sha256"],
        "contract": package["contract"],
        "independent_review_questions": package["independent_review_questions"],
    }
    return {
        "model": model,
        "instructions": (
            "Act as an independent AI-safety and ML-data-contract reviewer. Review only the supplied "
            "frozen contract, not the local gate summary. Fail any ambiguity that could permit target read, "
            "split leakage, disagreement flattening, protected-artifact backflow, rule replacement, or external "
            "release authority. Repeat every review question exactly and in the supplied order. A pass verdict "
            "requires all five question verdicts to pass, with no failed checks or critical findings."
        ),
        "input": json.dumps(review_input, ensure_ascii=False, sort_keys=True),
        "reasoning": {"effort": "high"},
        "max_output_tokens": 10000,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "psm_v0_261_external_contract_review",
                "schema": response_schema(),
                "strict": True,
            }
        },
    }


def _extract_output_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "".join(parts)


def _default_transport(payload: dict, api_key: str, endpoint: str, timeout: float) -> tuple[dict, dict[str, str], int]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response), dict(response.headers.items()), response.status
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read().decode("utf-8")).get("error", {})
        except (UnicodeDecodeError, json.JSONDecodeError):
            error = {}
        code = error.get("code") or error.get("type") or "http_error"
        raise RuntimeError(f"OpenAI Responses API failed with HTTP {exc.code}: {code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI Responses API network failure: {exc.reason}") from exc


def validate_external_review(review: dict, package: dict) -> dict[str, bool]:
    questions = package["independent_review_questions"]
    question_reviews = review.get("question_reviews")
    if not isinstance(question_reviews, list):
        raise ValueError("External review omitted question reviews.")
    if [item.get("question") for item in question_reviews if isinstance(item, dict)] != questions:
        raise ValueError("External review did not preserve exact question coverage and order.")
    if review.get("contract_sha256") != package["contract_sha256"]:
        raise ValueError("External review returned a different contract SHA-256.")

    verdict = review.get("verdict")
    if verdict not in {"pass", "fail"}:
        raise ValueError("External review returned an invalid verdict.")
    failed_checks = review.get("failed_checks")
    critical_findings = review.get("critical_findings")
    repairs = review.get("recommended_repairs")
    if any(not isinstance(value, list) or any(not isinstance(item, str) for item in value) for value in (failed_checks, critical_findings, repairs)):
        raise ValueError("External review returned an invalid list field.")
    question_verdicts = [item.get("verdict") for item in question_reviews]
    if any(value not in {"pass", "fail"} for value in question_verdicts):
        raise ValueError("External review returned an invalid question verdict.")

    internally_passing = (
        not failed_checks
        and not critical_findings
        and all(value == "pass" for value in question_verdicts)
    )
    if (verdict == "pass") is not internally_passing:
        raise ValueError("External review verdict contradicts its detailed findings.")
    return {
        "contract_sha256_match": True,
        "exact_question_coverage": True,
        "response_internally_consistent": True,
        "external_verdict_pass": verdict == "pass",
    }


def review_contract(
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
        usage = response.get("usage") or {}
        raise RuntimeError(
            "OpenAI external contract review did not complete: "
            f"{reason}; output_tokens={usage.get('output_tokens', 0)}"
        )
    raw_output = _extract_output_text(response)
    if not raw_output:
        raise RuntimeError("OpenAI external contract review returned no structured output.")
    try:
        review = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI external contract review output is not valid JSON.") from exc
    gate_checks = validate_external_review(review, package)
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    return {
        "schema_version": "psm_v0_261_openai_external_contract_judge_v1",
        "version": "PSM_V0.261",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "provider": "OpenAI",
        "endpoint": "/v1/responses",
        "requested_model": model,
        "actual_model": response.get("model"),
        "http_status": http_status,
        "response_status": response.get("status"),
        "response_id": response.get("id"),
        "request_id": lowered_headers.get("x-request-id"),
        "store": False,
        "api_key_persisted_in_artifact": False,
        "package_sha256": canonical_sha256(package),
        "contract_sha256": package["contract_sha256"],
        "request_payload_sha256": canonical_sha256(payload),
        "submission_scope": {
            "synthetic_only": True,
            "contains_private_data": False,
            "contains_user_documents": False,
            "contains_secrets": False,
            "external_users_involved": False,
        },
        "usage": response.get("usage") or {},
        "review": review,
        "gate_checks": gate_checks,
        "passed": all(gate_checks.values()),
        "release_boundary": {
            "contract_review_only": True,
            "training_authority": False,
            "rule_replacement_authority": False,
            "external_user_trial_allowed": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
    }


def build_markdown_report(result: dict) -> str:
    review = result["review"]
    lines = [
        "# PSM V0.261 OpenAI External Contract Judge",
        "",
        f"- Passed: `{result['passed']}`",
        f"- External verdict: `{review['verdict']}`",
        f"- Model: `{result['actual_model'] or result['requested_model']}`",
        f"- Response status: `{result['response_status']}`",
        f"- Contract SHA-256: `{result['contract_sha256']}`",
        f"- Input tokens: `{result['usage'].get('input_tokens', 0)}`",
        f"- Output tokens: `{result['usage'].get('output_tokens', 0)}`",
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
    lines.extend(
        [
            "",
            "This judgment covers only the authorized synthetic frozen contract. It does not authorize training, external users, public service, professional decisions, rule replacement, or external release.",
            "",
        ]
    )
    return "\n".join(lines)
