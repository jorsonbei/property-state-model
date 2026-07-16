#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from psm_v0.openai_external_contract_judge import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.286_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.287_project_status.json"
PACKAGE = RUNTIME / "v0_287_external_natural_recovery_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_287_external_natural_recovery_package_gate.json"
JUDGE = RUNTIME / "v0_287_openai_external_natural_recovery_judge.json"
GATE = RUNTIME / "v0_287_external_natural_recovery_gate.json"
CHECKPOINT = RUNTIME / "v0_287_external_natural_recovery_checkpoint.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"
MANIFEST = RUNTIME / "v0_287_external_natural_recovery_promotion_manifest.json"
TOKEN_LIMIT = 1_000_000


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


def main() -> None:
    source = read(SOURCE)
    package = read(PACKAGE)
    package_gate = read(PACKAGE_GATE)
    judge = read(JUDGE)
    observed_tokens, usage_records = collect_openai_usage()
    review = judge["review"]
    item_reviews = review["item_reviews"]
    checks = {
        "source_version_is_v0_286": source.get("current_version") == "psm_v0.286",
        "package_gate_passed": package_gate.get("passed") is True and all(package_gate.get("checks", {}).values()),
        "package_hash_matches_judge": canonical_sha256(package) == judge.get("package_sha256"),
        "external_judge_passed": judge.get("passed") is True and all(judge.get("gate_checks", {}).values()),
        "all_sixteen_items_passed": len(item_reviews) == 16 and all(item.get("verdict") == "pass" for item in item_reviews),
        "failed_items_zero": review.get("failed_item_ids") == [],
        "critical_findings_zero": review.get("critical_findings") == [],
        "observed_tokens_within_authority": observed_tokens <= TOKEN_LIMIT,
        "participant_content_zero": package["privacy"].get("contains_participant_content") is False,
        "private_data_zero": package["privacy"].get("contains_private_data") is False,
        "persistent_memory_closed": package["release_boundary"].get("persistent_conversation_memory_enabled") is False,
        "external_release_closed": package["release_boundary"].get("external_release_authority") is False,
    }
    gate = {
        "schema_version": "psm_v0_287_external_natural_recovery_gate_v1",
        "decision": "independent_external_natural_recovery_review_passed" if all(checks.values()) else "blocked",
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
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    write(GATE, gate)
    if not gate["passed"]:
        raise SystemExit(f"V0.287 promotion failed: {[key for key, value in checks.items() if not value]}")

    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.287",
        "previous_formal_version": "psm_v0.286",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_natural_recovery_review_passed",
        "v0_287_external_natural_recovery_gate": gate,
        "next_stage": {
            "version": "PSM_V0.288",
            "objective": "执行 V0.287 代码在主机与 Docker 的版本一致性、自然指代恢复、页面状态提示和无原文写盘回归。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_287_package": str(PACKAGE.relative_to(PSM_ROOT)),
        "v0_287_package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
        "v0_287_external_judge": str(JUDGE.relative_to(PSM_ROOT)),
        "v0_287_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_287_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_287_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.287_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_287_external_natural_recovery_promotion_manifest_v1",
        "version": "PSM_V0.287",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_natural_recovery_review": gate,
        "release_boundary": judge["release_boundary"],
        "next_stage": target["next_stage"],
    }
    checkpoint = {
        "schema_version": "psm_v0_287_external_natural_recovery_checkpoint_v1",
        "current_promoted_version": "PSM_V0.287",
        "target_promoted": True,
        "status": "v0_287_promoted_v0_288_runtime_parity_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "verify_v0_288_host_docker_natural_recovery",
        "required_decision": "无。",
    }
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
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    write(TOKEN_AUTHORITY, authority)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"observed_cumulative_openai_tokens: {observed_tokens}")
    print(f"remaining_tokens: {TOKEN_LIMIT - observed_tokens}")
    print("promoted: true")
    print("next_stage: PSM_V0.288")


if __name__ == "__main__":
    main()
