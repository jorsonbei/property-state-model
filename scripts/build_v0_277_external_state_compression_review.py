#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from psm_v0.openai_external_state_compression_judge import (
    APPROVED_AUTHORIZATION,
    DIMENSIONS,
    TOKEN_AUTHORITY_LIMIT,
    canonical_sha256,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_276_long_horizon_state_compression_contract.json"
REPORT = RUNTIME / "v0_276_long_horizon_state_compression_report.json"
GATE = RUNTIME / "v0_276_long_horizon_state_compression_gate.json"
STATUS = PSM_ROOT / "project_status_out" / "psm_v0.276_project_status.json"
PACKAGE = RUNTIME / "v0_277_external_state_compression_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_277_external_state_compression_package_gate.json"
CHECKPOINT = RUNTIME / "v0_277_external_state_compression_checkpoint.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"
MAXIMUM_CALL_TOKENS = 30_000


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
        records.append({
            "artifact": str(path.relative_to(PSM_ROOT)),
            "response_id": value.get("response_id"),
            "request_id": value.get("request_id"),
            "total_tokens": int((value.get("usage") or {}).get("total_tokens") or 0),
        })
    return sum(item["total_tokens"] for item in records), records


def main() -> None:
    contract = read(CONTRACT)
    report = read(REPORT)
    source_gate = read(GATE)
    status = read(STATUS)
    rows = {row["case_id"]: row for row in report["rows"]}
    observed_tokens, usage_records = collect_openai_usage()
    reserved_total_tokens = observed_tokens + MAXIMUM_CALL_TOKENS
    review_items = [
        {
            "review_id": item["id"],
            "family": item["family"],
            "conversation": item["messages"],
            "final_answer": rows[item["id"]]["answer"],
        }
        for item in contract["cases"]
    ]
    payload = {
        "objective": "Independently review long-horizon state recovery after more than 40 synthetic conversation messages.",
        "rubric_dimensions": list(DIMENSIONS),
        "items": review_items,
    }
    package = {
        "schema_version": "psm_v0_277_external_state_compression_review_package_v1",
        "version": "PSM_V0.277-candidate",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "source_version": "PSM_V0.276",
        "authorization": APPROVED_AUTHORIZATION,
        "authorization_scope": "synthetic_external_judging_within_1000000_token_authority",
        "privacy": {
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
        },
        "budget": {
            "maximum_api_calls": 1,
            "token_authority_limit": TOKEN_AUTHORITY_LIMIT,
            "observed_tokens_before": observed_tokens,
            "maximum_call_tokens": MAXIMUM_CALL_TOKENS,
            "reserved_total_tokens": reserved_total_tokens,
            "approval_required": False,
            "authorization_scope": "synthetic_external_judging_only",
        },
        "release_boundary": {
            "human_validation_claimed": False,
            "training_feedback_allowed": False,
            "rule_replacement_allowed": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
    }
    validate_review_package(package)
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [
        token
        for token in (
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
        if token in serialized
    ]
    checks = {
        "source_version_promoted": status.get("current_version") == "psm_v0.276",
        "source_gate_passed": source_gate.get("passed") is True,
        "source_cases_all_passed": report.get("summary", {}).get("passed") == 10,
        "exact_ten_item_coverage": len(review_items) == 10,
        "all_conversations_exceed_forty_messages": all(len(item["conversation"]) >= 40 for item in review_items),
        "token_authority_exactly_one_million": package["budget"]["token_authority_limit"] == TOKEN_AUTHORITY_LIMIT,
        "single_call_reserved": package["budget"]["maximum_api_calls"] == 1,
        "reserved_total_within_authority": reserved_total_tokens <= TOKEN_AUTHORITY_LIMIT,
        "privacy_boundary_closed": package["privacy"]["synthetic_only"] is True
        and all(value is False for key, value in package["privacy"].items() if key != "synthetic_only"),
        "release_boundary_closed": not any(package["release_boundary"].values()),
        "prohibited_material_absent": not prohibited,
    }
    gate = {
        "schema_version": "psm_v0_277_external_state_compression_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "review_payload_sha256": package["review_payload_sha256"],
        "package_sha256": canonical_sha256(package),
        "prohibited_material_found": prohibited,
    }
    authority = {
        "schema_version": "psm_autonomous_api_token_authority_v1",
        "effective_at": "2026-07-16",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "authorized_by_user": True,
        "token_limit": TOKEN_AUTHORITY_LIMIT,
        "observed_tokens_before_reservation": observed_tokens,
        "reserved_tokens_for_next_call": MAXIMUM_CALL_TOKENS,
        "reserved_total_tokens": reserved_total_tokens,
        "remaining_tokens_after_reservation": TOKEN_AUTHORITY_LIMIT - reserved_total_tokens,
        "approval_required": False,
        "scope": "synthetic_external_judging_only",
        "supersedes_per_call_dollar_approval_within_token_limit": True,
        "participant_content_allowed": False,
        "private_data_allowed": False,
        "training_feedback_allowed": False,
        "external_release_authority": False,
        "usage_records": usage_records,
    }
    checkpoint = {
        "schema_version": "psm_v0_277_external_state_compression_checkpoint_v1",
        "version": "PSM_V0.277-candidate",
        "status": "authorized_external_review_ready",
        "requires_user_input": False,
        "next_action": "run_openai_state_compression_judge",
        "review_payload_sha256": package["review_payload_sha256"],
        "token_authority_limit": TOKEN_AUTHORITY_LIMIT,
        "observed_tokens_before_call": observed_tokens,
        "maximum_call_tokens": MAXIMUM_CALL_TOKENS,
        "participant_content_calls": 0,
        "external_release_authority": False,
    }
    write(PACKAGE, package)
    write(PACKAGE_GATE, gate)
    write(TOKEN_AUTHORITY, authority)
    write(CHECKPOINT, checkpoint)
    if not gate["passed"]:
        raise SystemExit(f"V0.277 package gate failed: {[key for key, value in checks.items() if not value]}")
    print(f"observed_tokens_before: {observed_tokens}")
    print(f"reserved_total_tokens: {reserved_total_tokens}")
    print(f"remaining_tokens_after_reservation: {TOKEN_AUTHORITY_LIMIT - reserved_total_tokens}")
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print("external_calls_authorized: 1")


if __name__ == "__main__":
    main()
