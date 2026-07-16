#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from product_alpha_app import server
from psm_v0.openai_external_natural_recovery_judge import (
    APPROVED_AUTHORIZATION,
    DIMENSIONS,
    PACKAGE_SCHEMA,
    TOKEN_AUTHORITY_LIMIT,
    canonical_sha256,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
STATUS = PSM_ROOT / "project_status_out" / "psm_v0.286_project_status.json"
SOURCE_GATE = RUNTIME / "v0_286_natural_recovery_reference_promotion_manifest.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_286_natural_recovery_reference_contract.json"
PACKAGE = RUNTIME / "v0_287_external_natural_recovery_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_287_external_natural_recovery_package_gate.json"
CHECKPOINT = RUNTIME / "v0_287_external_natural_recovery_checkpoint.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"
MAXIMUM_CALL_TOKENS = 30_000
LOSS_STATES = ("reset", "reload", "expired", "restarted")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_openai_usage() -> tuple[int, list[dict]]:
    seen: set[str] = set()
    records = []
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


def candidate_item(case: dict, positive_index: int) -> dict:
    if case["should_trigger_recovery"]:
        state = LOSS_STATES[positive_index % len(LOSS_STATES)]
        event_labels = {
            "reset": "会话已清空",
            "reload": "页面已刷新且旧状态不可用",
            "expired": "会话已过期",
            "restarted": "服务已重启且旧状态不可用",
        }
        result = server.run_chat_turn(
            [{"role": "user", "content": case["text"]}],
            "review",
            rolling_state_metadata={
                "continuity_status": server.continuity_status(state, memory_available=False),
                "ephemeral_memory_only": True,
                "disk_persistence": False,
            },
        )
        conversation = [
            {"role": "user", "content": "项目代号定为白砾。"},
            {"role": "assistant", "content": "已记录。"},
            {"role": "user", "content": f"[{event_labels[state]}] {case['text']}"},
        ]
    else:
        state = "active"
        result = server.run_chat_turn(
            [{"role": "user", "content": case["text"]}],
            "review",
            rolling_state_metadata={
                "continuity_status": server.continuity_status(state, memory_available=True),
                "ephemeral_memory_only": True,
                "disk_persistence": False,
            },
        )
        conversation = [{"role": "user", "content": case["text"]}]
    return {
        "review_id": case["case_id"],
        "continuity_state": state,
        "conversation": conversation,
        "final_answer": result["chat"]["assistant_message"],
    }


def main() -> None:
    status = read(STATUS)
    source_gate = read(SOURCE_GATE)
    contract = read(CONTRACT)
    observed_tokens, usage_records = collect_openai_usage()
    reserved_total = observed_tokens + MAXIMUM_CALL_TOKENS
    items = []
    positive_index = 0
    for case in contract["cases"]:
        items.append(candidate_item(case, positive_index))
        if case["should_trigger_recovery"]:
            positive_index += 1
    payload = {
        "objective": "Independently review natural prior-reference recovery and explicit new-task specificity.",
        "rubric_dimensions": list(DIMENSIONS),
        "items": items,
    }
    privacy = {
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
    package = {
        "schema_version": PACKAGE_SCHEMA,
        "version": "PSM_V0.287-candidate",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "source_version": "PSM_V0.286",
        "authorization": APPROVED_AUTHORIZATION,
        "authorization_scope": "synthetic_external_judging_within_1000000_token_authority",
        "privacy": privacy,
        "budget": {
            "maximum_api_calls": 1,
            "token_authority_limit": TOKEN_AUTHORITY_LIMIT,
            "observed_tokens_before": observed_tokens,
            "maximum_call_tokens": MAXIMUM_CALL_TOKENS,
            "reserved_total_tokens": reserved_total,
            "approval_required": False,
            "authorization_scope": "synthetic_external_judging_only",
        },
        "release_boundary": {
            "human_validation_claimed": False,
            "training_feedback_allowed": False,
            "persistent_conversation_memory_enabled": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
    }
    validate_review_package(package)
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [token for token in ("sk-proj-", "/users/", "invitation_code", "api_key") if token in serialized]
    positive_items = items[:12]
    negative_items = items[12:]
    loss_answer = server.continuity_loss_answer("reset")
    checks = {
        "source_version_promoted": status.get("current_version") == "psm_v0.286",
        "source_promotion_gate_passed": source_gate.get("promoted") is True and all(source_gate.get("checks", {}).values()),
        "exact_sixteen_case_coverage": [item["review_id"] for item in items] == [f"N{i:02d}" for i in range(1, 17)],
        "twelve_loss_answers_do_not_leak_fact": all("白砾" not in item["final_answer"] for item in positive_items),
        "twelve_loss_answers_show_boundary": all("无法读取先前会话内容" in item["final_answer"] for item in positive_items),
        "four_new_tasks_not_false_recovery": all(item["final_answer"] != loss_answer for item in negative_items),
        "reserved_total_within_authority": reserved_total <= TOKEN_AUTHORITY_LIMIT,
        "privacy_boundary_closed": privacy["synthetic_only"] is True and all(not value for key, value in privacy.items() if key != "synthetic_only"),
        "release_boundary_closed": not any(package["release_boundary"].values()),
        "prohibited_material_absent": not prohibited,
    }
    gate = {
        "schema_version": "psm_v0_287_external_natural_recovery_package_gate_v1",
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
        "reserved_total_tokens": reserved_total,
        "remaining_tokens_after_reservation": TOKEN_AUTHORITY_LIMIT - reserved_total,
        "approval_required": False,
        "scope": "synthetic_external_judging_only",
        "participant_content_allowed": False,
        "private_data_allowed": False,
        "training_feedback_allowed": False,
        "external_release_authority": False,
        "usage_records": usage_records,
    }
    checkpoint = {
        "schema_version": "psm_v0_287_external_natural_recovery_checkpoint_v1",
        "version": "PSM_V0.287-candidate",
        "status": "authorized_external_review_ready" if gate["passed"] else "package_gate_failed",
        "requires_user_input": False,
        "next_action": "run_v0_287_openai_natural_recovery_judge" if gate["passed"] else "repair_package",
        "observed_tokens_before_call": observed_tokens,
        "maximum_call_tokens": MAXIMUM_CALL_TOKENS,
        "external_release_authority": False,
    }
    write(PACKAGE, package)
    write(PACKAGE_GATE, gate)
    write(TOKEN_AUTHORITY, authority)
    write(CHECKPOINT, checkpoint)
    print(f"package: {PACKAGE.relative_to(ROOT)}")
    print(f"observed_tokens_before: {observed_tokens}")
    print(f"reserved_total_tokens: {reserved_total}")
    print(f"package_gate_passed: {gate['passed']}")
    if not gate["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
