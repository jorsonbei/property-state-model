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
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.280_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.281_project_status.json"
PACKAGE = RUNTIME / "v0_281_external_rolling_state_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_281_external_rolling_state_package_gate.json"
JUDGE = RUNTIME / "v0_281_openai_external_rolling_state_judge.json"
ISOLATION = RUNTIME / "v0_281_rolling_state_isolation_report.json"
ISOLATION_GATE = RUNTIME / "v0_281_rolling_state_isolation_gate.json"
EVALUATOR_GAP = RUNTIME / "v0_281_rolling_state_isolation_attempt_1_evaluator_gap.json"
GATE = RUNTIME / "v0_281_external_rolling_state_gate.json"
CHECKPOINT = RUNTIME / "v0_281_external_rolling_state_checkpoint.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"
MANIFEST = RUNTIME / "v0_281_external_rolling_state_promotion_manifest.json"
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
    isolation = read(ISOLATION)
    isolation_gate = read(ISOLATION_GATE)
    evaluator_gap = read(EVALUATOR_GAP)
    checkpoint = read(CHECKPOINT)
    observed_tokens, usage_records = collect_openai_usage()
    review = judge["review"]
    item_reviews = review["item_reviews"]
    checks = {
        "source_version_is_v0_280": source.get("current_version") == "psm_v0.280",
        "package_gate_passed": package_gate.get("passed") is True and all(package_gate.get("checks", {}).values()),
        "package_hash_matches_judge": digest(package) == judge.get("package_sha256"),
        "external_judge_passed": judge.get("passed") is True and all(judge.get("gate_checks", {}).values()),
        "all_four_items_passed": len(item_reviews) == 4 and all(item.get("verdict") == "pass" for item in item_reviews),
        "failed_items_zero": review.get("failed_item_ids") == [],
        "critical_findings_zero": review.get("critical_findings") == [],
        "isolation_gate_passed": isolation_gate.get("passed") is True and isolation.get("passed") is True,
        "cross_session_leaks_zero": isolation.get("metrics", {}).get("cross_session_leaks") == 0,
        "disk_writes_zero": isolation.get("metrics", {}).get("disk_writes") == 0,
        "evaluator_gap_retained": evaluator_gap.get("passed") is False and evaluator_gap.get("checks", {}).get("expired_session_a_removed") is False,
        "observed_tokens_within_authority": observed_tokens <= TOKEN_LIMIT,
        "participant_content_zero": package["privacy"].get("contains_participant_content") is False,
        "private_data_zero": package["privacy"].get("contains_private_data") is False,
        "training_feedback_zero": package["privacy"].get("training_eligible") is False,
        "external_release_closed": package["release_boundary"].get("external_release_authority") is False,
    }
    gate = {
        "schema_version": "psm_v0_281_external_rolling_state_gate_v1",
        "decision": "independent_external_rolling_state_and_isolation_review_passed" if all(checks.values()) else "blocked",
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
        "cross_session_leaks": isolation.get("metrics", {}).get("cross_session_leaks"),
        "disk_writes": isolation.get("metrics", {}).get("disk_writes"),
        "participant_content_calls": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "training_feedback_written": False,
        "external_release_authority": False,
    }
    write(GATE, gate)
    if not gate["passed"]:
        checkpoint.update({
            "status": "external_or_isolation_review_failed_local_repair_required",
            "requires_user_input": False,
            "next_action": "evaluate_recorded_findings_and_repair_locally",
        })
        write(CHECKPOINT, checkpoint)
        raise SystemExit(f"V0.281 promotion failed: {[key for key, value in checks.items() if not value]}")

    external_gate = {
        "decision": gate["decision"],
        "passed": True,
        "provider": gate["provider"],
        "model": gate["model"],
        "items": 4,
        "items_passed": 4,
        "families": 4,
        "failed_item_ids": [],
        "critical_findings": [],
        "isolation_checks": len(isolation_gate["checks"]),
        "isolation_checks_passed": sum(isolation_gate["checks"].values()),
        "cross_session_leaks": 0,
        "disk_writes": 0,
        "evaluator_gap_attempts_retained": 1,
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
        "current_version": "psm_v0.281",
        "previous_formal_version": "psm_v0.280",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_rolling_state_and_session_isolation_review_passed",
        "v0_281_external_rolling_state_gate": external_gate,
        "next_stage": {
            "version": "PSM_V0.282",
            "objective": "执行真实浏览器的跨窗口连续聊天回归，并明确页面刷新、服务重启与临时记忆失效时的用户体验和恢复边界。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_281_package": str(PACKAGE.relative_to(PSM_ROOT)),
        "v0_281_package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
        "v0_281_external_judge": str(JUDGE.relative_to(PSM_ROOT)),
        "v0_281_isolation_report": str(ISOLATION.relative_to(PSM_ROOT)),
        "v0_281_isolation_gate": str(ISOLATION_GATE.relative_to(PSM_ROOT)),
        "v0_281_evaluator_gap": str(EVALUATOR_GAP.relative_to(PSM_ROOT)),
        "v0_281_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_281_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_281_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.281_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_281_external_rolling_state_promotion_manifest_v1",
        "version": "PSM_V0.281",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_rolling_state_review": external_gate,
        "evidence": {
            "package": str(PACKAGE.relative_to(PSM_ROOT)),
            "package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
            "judge": str(JUDGE.relative_to(PSM_ROOT)),
            "isolation_report": str(ISOLATION.relative_to(PSM_ROOT)),
            "isolation_gate": str(ISOLATION_GATE.relative_to(PSM_ROOT)),
            "evaluator_gap": str(EVALUATOR_GAP.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
        },
        "release_boundary": package["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.281",
        "target_promoted": True,
        "status": "v0_281_promoted_v0_282_browser_lifecycle_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_282_browser_rolling_state_lifecycle_regression",
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
    print("next_stage: PSM_V0.282")


if __name__ == "__main__":
    main()
