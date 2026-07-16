#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from psm_v0.openai_external_open_context_judge import (
    APPROVED_AUTONOMOUS_TOKEN_AUTHORIZATION,
    canonical_sha256,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
ORIGINAL_JUDGE = RUNTIME / "v0_275_openai_external_open_context_judge.json"
REJUDGE = RUNTIME / "v0_275_openai_external_open_context_rejudge.json"
SECOND_REPAIR = RUNTIME / "v0_275_external_open_context_second_repair_candidate.json"
SECOND_REPAIR_GATE = RUNTIME / "v0_275_external_open_context_second_repair_gate.json"
CHECKPOINT = RUNTIME / "v0_275_external_open_context_checkpoint.json"
PACKAGE = RUNTIME / "v0_275_external_open_context_review_attempt_3_package.json"
PACKAGE_GATE = RUNTIME / "v0_275_external_open_context_review_attempt_3_package_gate.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"

TOKEN_LIMIT = 1_000_000
MAXIMUM_CALL_TOKENS = 12_000


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_openai_usage() -> tuple[int, list[dict]]:
    seen: set[str] = set()
    records: list[dict] = []
    for path in sorted(RUNTIME.glob("*openai*.json")):
        value = read(path)
        if value.get("provider") != "OpenAI":
            continue
        identity = str(value.get("response_id") or value.get("request_id") or path.name)
        if identity in seen:
            continue
        seen.add(identity)
        total_tokens = int((value.get("usage") or {}).get("total_tokens") or 0)
        records.append({
            "artifact": str(path.relative_to(PSM_ROOT)),
            "response_id": value.get("response_id"),
            "request_id": value.get("request_id"),
            "total_tokens": total_tokens,
        })
    return sum(item["total_tokens"] for item in records), records


def main() -> None:
    original_judge = read(ORIGINAL_JUDGE)
    rejudge = read(REJUDGE)
    repaired = read(SECOND_REPAIR)
    repair_gate = read(SECOND_REPAIR_GATE)
    checkpoint = read(CHECKPOINT)
    observed_tokens, usage_records = collect_openai_usage()
    reserved_total_tokens = observed_tokens + MAXIMUM_CALL_TOKENS

    package = copy.deepcopy(repaired)
    package.update({
        "schema_version": "psm_v0_275_external_open_context_review_package_v1",
        "version": "PSM_V0.275-review-attempt-3-candidate",
        "authorization": APPROVED_AUTONOMOUS_TOKEN_AUTHORIZATION,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_scope": "synthetic_external_judging_within_1000000_token_authority",
        "source_failed_judge": "runtime/v0_275_openai_external_open_context_rejudge.json",
        "source_repair_report": "runtime/v0_275_external_open_context_second_repair_report.json",
    })
    package["budget"] = {
        "currency": "USD",
        "maximum_api_calls": 1,
        "reserved_usd": 0.0,
        "token_authority_limit": TOKEN_LIMIT,
        "observed_tokens_before": observed_tokens,
        "maximum_call_tokens": MAXIMUM_CALL_TOKENS,
        "reserved_total_tokens": reserved_total_tokens,
        "approval_required": False,
        "authorization_scope": "synthetic_external_judging_only",
    }
    package.pop("source_original_external_failure", None)
    package.pop("source_failed_external_rejudge", None)
    package.pop("source_rejudge_package", None)
    package.pop("source_local_report", None)
    validate_review_package(package, require_authorization=True)

    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [
        token
        for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers")
        if token in serialized
    ]
    checks = {
        "original_external_failure_retained": (
            original_judge.get("passed") is False
            and original_judge.get("review", {}).get("failed_item_ids") == ["O01", "O02", "O10"]
        ),
        "first_external_rejudge_failure_retained": (
            rejudge.get("passed") is False
            and rejudge.get("review", {}).get("failed_item_ids") == ["O09"]
        ),
        "second_local_repair_gate_passed": repair_gate.get("passed") is True and all(repair_gate.get("checks", {}).values()),
        "repaired_payload_hash_retained": package["review_payload_sha256"] == repaired["review_payload_sha256"],
        "prior_checkpoint_requires_old_budget_decision": checkpoint.get("requires_user_input") is True,
        "single_call_authorized": package["budget"]["maximum_api_calls"] == 1,
        "token_authority_exactly_one_million": package["budget"]["token_authority_limit"] == TOKEN_LIMIT,
        "call_reservation_exactly_twelve_thousand": package["budget"]["maximum_call_tokens"] == MAXIMUM_CALL_TOKENS,
        "reserved_total_within_token_authority": reserved_total_tokens <= TOKEN_LIMIT,
        "approval_not_required_within_authority": package["budget"]["approval_required"] is False,
        "privacy_boundary_closed": package["privacy"].get("synthetic_only") is True
        and all(value is False for key, value in package["privacy"].items() if key != "synthetic_only"),
        "release_boundary_closed": not any(package["release_boundary"].values()),
        "prohibited_material_absent": not prohibited,
    }
    gate = {
        "schema_version": "psm_v0_275_external_open_context_review_attempt_3_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "authorization": APPROVED_AUTONOMOUS_TOKEN_AUTHORIZATION,
        "authorization_scope": "synthetic_external_judging_within_1000000_token_authority",
        "review_payload_sha256": package["review_payload_sha256"],
        "authorized_package_sha256": canonical_sha256(package),
        "prohibited_material_found": prohibited,
    }
    authority = {
        "schema_version": "psm_autonomous_api_token_authority_v1",
        "effective_at": "2026-07-16",
        "authorized_by_user": True,
        "token_limit": TOKEN_LIMIT,
        "observed_tokens_before_reservation": observed_tokens,
        "reserved_tokens_for_next_call": MAXIMUM_CALL_TOKENS,
        "reserved_total_tokens": reserved_total_tokens,
        "remaining_tokens_after_reservation": TOKEN_LIMIT - reserved_total_tokens,
        "approval_required": False,
        "scope": "synthetic_external_judging_only",
        "supersedes_per_call_dollar_approval_within_token_limit": True,
        "participant_content_allowed": False,
        "private_data_allowed": False,
        "training_feedback_allowed": False,
        "external_release_authority": False,
        "usage_records": usage_records,
    }
    if not gate["passed"]:
        write(PACKAGE_GATE, gate)
        raise SystemExit(f"V0.275 attempt 3 authorization failed: {[key for key, value in checks.items() if not value]}")

    checkpoint.update({
        "status": "external_open_context_review_attempt_3_authorized_under_token_authority",
        "requires_user_input": False,
        "next_action": "run_openai_open_context_review_attempt_3",
        "review_payload_sha256": package["review_payload_sha256"],
        "token_authority_limit": TOKEN_LIMIT,
        "observed_tokens_before_call": observed_tokens,
        "maximum_call_tokens": MAXIMUM_CALL_TOKENS,
        "required_decision": "无；合成外部评审在 1,000,000-token 授权内可自动执行。",
        "review_attempt_3_package": str(PACKAGE.relative_to(PSM_ROOT)),
        "review_attempt_3_package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
        "token_authority": str(TOKEN_AUTHORITY.relative_to(PSM_ROOT)),
    })
    write(PACKAGE, package)
    write(PACKAGE_GATE, gate)
    write(TOKEN_AUTHORITY, authority)
    write(CHECKPOINT, checkpoint)
    print(f"observed_tokens_before: {observed_tokens}")
    print(f"reserved_total_tokens: {reserved_total_tokens}")
    print(f"remaining_tokens_after_reservation: {TOKEN_LIMIT - reserved_total_tokens}")
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print("external_calls_authorized: 1")
    print("approval_required: false")


if __name__ == "__main__":
    main()
