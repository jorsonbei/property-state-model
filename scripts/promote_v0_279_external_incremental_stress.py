#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.278_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.279_project_status.json"
PACKAGE = RUNTIME / "v0_279_external_incremental_stress_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_279_external_incremental_stress_package_gate.json"
JUDGE = RUNTIME / "v0_279_openai_external_incremental_stress_judge.json"
GATE = RUNTIME / "v0_279_external_incremental_stress_gate.json"
CHECKPOINT = RUNTIME / "v0_279_external_incremental_stress_checkpoint.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"
MANIFEST = RUNTIME / "v0_279_external_incremental_stress_promotion_manifest.json"
TOKEN_LIMIT = 1_000_000


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


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
    source = read(SOURCE)
    package = read(PACKAGE)
    package_gate = read(PACKAGE_GATE)
    judge = read(JUDGE)
    checkpoint = read(CHECKPOINT)
    observed_tokens, usage_records = collect_openai_usage()
    review = judge["review"]
    item_reviews = review["item_reviews"]
    checks = {
        "source_version_is_v0_278": source.get("current_version") == "psm_v0.278",
        "package_gate_passed": package_gate.get("passed") is True and all(package_gate.get("checks", {}).values()),
        "package_hash_matches_judge": digest(package) == judge.get("package_sha256"),
        "external_judge_passed": judge.get("passed") is True and all(judge.get("gate_checks", {}).values()),
        "all_ten_items_passed": len(item_reviews) == 10 and all(item.get("verdict") == "pass" for item in item_reviews),
        "failed_items_zero": review.get("failed_item_ids") == [],
        "critical_findings_zero": review.get("critical_findings") == [],
        "observed_tokens_within_authority": observed_tokens <= TOKEN_LIMIT,
        "participant_content_zero": package["privacy"].get("contains_participant_content") is False,
        "private_data_zero": package["privacy"].get("contains_private_data") is False,
        "training_feedback_zero": package["privacy"].get("training_eligible") is False,
        "external_release_closed": package["release_boundary"].get("external_release_authority") is False,
    }
    gate = {
        "schema_version": "psm_v0_279_external_incremental_stress_gate_v1",
        "decision": "independent_external_incremental_stress_review_passed" if all(checks.values()) else "blocked",
        "passed": all(checks.values()),
        "checks": checks,
        "provider": judge.get("provider"),
        "model": judge.get("actual_model"),
        "items": len(item_reviews),
        "items_passed": sum(item.get("verdict") == "pass" for item in item_reviews),
        "failed_item_ids": review.get("failed_item_ids"),
        "critical_findings": review.get("critical_findings"),
        "total_tokens": int((judge.get("usage") or {}).get("total_tokens") or 0),
        "observed_cumulative_openai_tokens": observed_tokens,
        "token_authority_limit": TOKEN_LIMIT,
        "participant_content_calls": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "training_feedback_written": False,
        "external_release_authority": False,
    }
    write(GATE, gate)
    if not gate["passed"]:
        checkpoint.update({
            "status": "external_review_failed_local_repair_required",
            "requires_user_input": False,
            "next_action": "evaluate_external_findings_and_repair_locally",
            "failed_item_ids": review.get("failed_item_ids"),
        })
        write(CHECKPOINT, checkpoint)
        raise SystemExit(f"V0.279 promotion failed: {[key for key, value in checks.items() if not value]}")

    external_gate = {
        "decision": gate["decision"],
        "passed": True,
        "provider": gate["provider"],
        "model": gate["model"],
        "items": 10,
        "items_passed": 10,
        "families": 5,
        "message_levels": [81, 119],
        "failed_item_ids": [],
        "critical_findings": [],
        "total_tokens": gate["total_tokens"],
        "observed_cumulative_openai_tokens": observed_tokens,
        "autonomous_token_authority_limit": TOKEN_LIMIT,
        "participant_content_calls": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "training_feedback_written": False,
        "external_release_authority": False,
        "review_payload_sha256": package["review_payload_sha256"],
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.279",
        "previous_formal_version": "psm_v0.278",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_incremental_long_horizon_stress_review_passed",
        "v0_279_external_incremental_stress_gate": external_gate,
        "next_stage": {
            "version": "PSM_V0.280",
            "objective": "实现跨 120 消息截断的滚动状态交接，使早期用户事实在原始消息退出窗口后仍可恢复，同时保持无助手历史权威、无原文持久化与话题切换清理。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_279_package": str(PACKAGE.relative_to(PSM_ROOT)),
        "v0_279_package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
        "v0_279_external_judge": str(JUDGE.relative_to(PSM_ROOT)),
        "v0_279_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_279_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_279_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.279_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_279_external_incremental_stress_promotion_manifest_v1",
        "version": "PSM_V0.279",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_incremental_stress_review": external_gate,
        "evidence": {
            "package": str(PACKAGE.relative_to(PSM_ROOT)),
            "package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
            "judge": str(JUDGE.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
        },
        "release_boundary": package["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.279",
        "target_promoted": True,
        "status": "v0_279_promoted_v0_280_rolling_state_handoff_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_280_rolling_state_handoff_contract",
        "required_decision": "无。",
    })
    write(CHECKPOINT, checkpoint)
    authority = {
        "schema_version": "psm_autonomous_api_token_authority_v1",
        "effective_at": "2026-07-16",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "authorized_by_user": True,
        "token_limit": TOKEN_LIMIT,
        "observed_tokens": observed_tokens,
        "reserved_tokens_for_next_call": 0,
        "remaining_tokens": TOKEN_LIMIT - observed_tokens,
        "approval_required": False,
        "scope": "synthetic_external_judging_only",
        "participant_content_allowed": False,
        "private_data_allowed": False,
        "training_feedback_allowed": False,
        "external_release_authority": False,
        "usage_records": usage_records,
    }
    write(TOKEN_AUTHORITY, authority)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print(f"observed_cumulative_openai_tokens: {observed_tokens}")
    print(f"remaining_tokens: {TOKEN_LIMIT - observed_tokens}")
    print("promoted: true")
    print("next_stage: PSM_V0.280")


if __name__ == "__main__":
    main()
