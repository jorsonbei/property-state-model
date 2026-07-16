#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.282_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.283_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_283_restart_recovery_contract.json"
BASELINE = RUNTIME / "v0_283_restart_recovery_initial_failure_ledger.json"
REPORT = RUNTIME / "v0_283_restart_recovery_report.json"
GATE = RUNTIME / "v0_283_restart_recovery_gate.json"
RUNTIME_BOUNDARY = RUNTIME / "v0_283_controlled_restart_boundary.json"
BROWSER_DIR = RUNTIME / "v0_283_restart_recovery_browser_regression"
BROWSER = BROWSER_DIR / "report.json"
TEST_GAP = RUNTIME / "v0_283_targeted_test_attempt_1_evaluator_gap.json"
BROWSER_GAP = RUNTIME / "v0_283_browser_attempt_1_semantic_gap.json"
CHECKPOINT = RUNTIME / "v0_283_restart_recovery_checkpoint.json"
MANIFEST = RUNTIME / "v0_283_restart_recovery_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    contract = read(CONTRACT)
    baseline = read(BASELINE)
    report = read(REPORT)
    gate = read(GATE)
    runtime_boundary = read(RUNTIME_BOUNDARY)
    browser = read(BROWSER)
    test_gap = read(TEST_GAP)
    browser_gap = read(BROWSER_GAP)
    checks = {
        "source_version_is_v0_282": source.get("current_version") == "psm_v0.282",
        "contract_frozen_and_synthetic": contract.get("frozen") is True and contract.get("synthetic_only") is True,
        "baseline_retained_at_zero_of_five": baseline.get("passed") == 0 and baseline.get("failed") == 5,
        "local_gate_passed_five_of_five": gate.get("passed") is True and report.get("summary", {}).get("passed") == 5,
        "all_states_distinguishable": report.get("summary", {}).get("states_observed") == ["active", "expired", "reload", "reset", "restarted"],
        "zero_fabricated_archived_facts": report.get("summary", {}).get("fabricated_archived_facts") == 0,
        "host_docker_controlled_restart_passed": runtime_boundary.get("passed") is True and all(runtime_boundary.get("checks", {}).values()),
        "browser_regression_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "desktop_mobile_no_overflow": (
            browser.get("desktop", {}).get("horizontalOverflow") is False
            and browser.get("mobile", {}).get("horizontalOverflow") is False
        ),
        "console_errors_zero": browser.get("desktop", {}).get("consoleErrors") == 0 and browser.get("mobile", {}).get("consoleErrors") == 0,
        "evaluator_and_semantic_gaps_retained": test_gap.get("evaluator_gap") is True and browser_gap.get("semantic_quality_passed") is False,
        "raw_conversation_persistence_disabled": contract["requirements"].get("raw_conversation_disk_persistence") is False,
        "external_release_closed": contract["requirements"].get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.283 promotion failed: {[key for key, value in checks.items() if not value]}")

    recovery_gate = {
        "decision": "restart_recovery_and_user_visible_continuity_gate_passed",
        "passed": True,
        "baseline_passed": 0,
        "baseline_failed": 5,
        "final_passed": 5,
        "final_failed": 0,
        "states": contract["requirements"]["states_distinguishable"],
        "fabricated_archived_facts": 0,
        "host_controlled_restart": "passed",
        "docker_controlled_restart": "passed",
        "desktop_browser": "passed",
        "mobile_browser": "passed",
        "console_errors": 0,
        "retained_gap_attempts": 2,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.283",
        "previous_formal_version": "psm_v0.282",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "restart_recovery_and_user_visible_continuity_gate_passed",
        "v0_283_restart_recovery_gate": recovery_gate,
        "next_stage": {
            "version": "PSM_V0.284",
            "objective": "对 active、reset、reload、expired、restarted 五类合成恢复回答执行独立外部语义评审，确认状态说明自然、无旧事实臆造且不会扩大持久记忆或外部发布权限。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_283_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_283_baseline": str(BASELINE.relative_to(PSM_ROOT)),
        "v0_283_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_283_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_283_runtime_boundary": str(RUNTIME_BOUNDARY.relative_to(PSM_ROOT)),
        "v0_283_browser_report": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_283_browser_desktop": str((BROWSER_DIR / "desktop-restart-recovery.png").relative_to(PSM_ROOT)),
        "v0_283_browser_mobile": str((BROWSER_DIR / "mobile-restart-recovery.png").relative_to(PSM_ROOT)),
        "v0_283_test_gap": str(TEST_GAP.relative_to(PSM_ROOT)),
        "v0_283_browser_gap": str(BROWSER_GAP.relative_to(PSM_ROOT)),
        "v0_283_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_283_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.283_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_283_restart_recovery_promotion_manifest_v1",
        "version": "PSM_V0.283",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": recovery_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "restart_recovery": recovery_gate,
        "checks": checks,
        "release_boundary": {
            "human_validation_claimed": False,
            "persistent_conversation_memory_enabled": False,
            "public_service_allowed": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "next_stage": target["next_stage"],
    }
    checkpoint = {
        "schema_version": "psm_v0_283_restart_recovery_checkpoint_v1",
        "current_promoted_version": "PSM_V0.283",
        "target_promoted": True,
        "status": "v0_283_promoted_v0_284_external_semantic_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_284_external_restart_recovery_review",
        "required_decision": "无；100万 token 合成外部评审授权仍有效。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.284")


if __name__ == "__main__":
    main()
