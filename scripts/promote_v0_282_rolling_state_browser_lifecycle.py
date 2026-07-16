#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.281_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.282_project_status.json"
BROWSER_DIR = RUNTIME / "v0_282_rolling_state_browser_regression"
BROWSER = BROWSER_DIR / "report.json"
CHECKPOINT = RUNTIME / "v0_282_rolling_state_browser_lifecycle_checkpoint.json"
MANIFEST = RUNTIME / "v0_282_rolling_state_browser_lifecycle_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    browser = read(BROWSER)
    checks = {
        "source_version_is_v0_281": source.get("current_version") == "psm_v0.281",
        "browser_report_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "cross_window_answer_visible": browser.get("desktop", {}).get("visibleAnswer") == "白砾",
        "browser_window_bounded_to_120": browser.get("desktop", {}).get("boundedMessages") == 120,
        "reset_rotates_session": browser.get("desktop", {}).get("resetRotatedSession") is True,
        "reload_rotates_session": browser.get("desktop", {}).get("reloadRotatedSession") is True,
        "reload_does_not_persist_memory": browser.get("browser_memory_persisted_after_reload") is False,
        "desktop_and_mobile_no_overflow": (
            browser.get("desktop", {}).get("horizontalOverflow") is False
            and browser.get("mobile", {}).get("horizontalOverflow") is False
        ),
        "console_errors_zero": (
            browser.get("desktop", {}).get("consoleErrors") == 0
            and browser.get("mobile", {}).get("consoleErrors") == 0
        ),
        "human_feedback_zero": browser.get("human_feedback_collected") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.282 promotion failed: {[key for key, value in checks.items() if not value]}")

    browser_gate = {
        "decision": "rolling_state_browser_lifecycle_gate_passed",
        "passed": True,
        "checks": checks,
        "cross_window_answer": "白砾",
        "browser_window_messages": 120,
        "reset_rotates_session": True,
        "reload_rotates_session": True,
        "browser_memory_persisted_after_reload": False,
        "desktop_horizontal_overflow": False,
        "mobile_horizontal_overflow": False,
        "console_errors": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.282",
        "previous_formal_version": "psm_v0.281",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "rolling_state_real_browser_lifecycle_gate_passed",
        "v0_282_rolling_state_browser_lifecycle_gate": browser_gate,
        "next_stage": {
            "version": "PSM_V0.283",
            "objective": "验证服务重启导致临时记忆失效时的故障恢复和用户可见边界，保持隐私优先且不把原始对话写入磁盘。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_282_browser_report": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_282_browser_desktop": str((BROWSER_DIR / "desktop-rolling-state.png").relative_to(PSM_ROOT)),
        "v0_282_browser_mobile": str((BROWSER_DIR / "mobile-rolling-state.png").relative_to(PSM_ROOT)),
        "v0_282_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_282_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.282_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_282_rolling_state_browser_lifecycle_promotion_manifest_v1",
        "version": "PSM_V0.282",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": browser_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "rolling_state_browser_lifecycle": browser_gate,
        "evidence": {
            "browser_report": str(BROWSER.relative_to(PSM_ROOT)),
            "desktop_screenshot": str((BROWSER_DIR / "desktop-rolling-state.png").relative_to(PSM_ROOT)),
            "mobile_screenshot": str((BROWSER_DIR / "mobile-rolling-state.png").relative_to(PSM_ROOT)),
        },
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
        "schema_version": "psm_v0_282_rolling_state_browser_lifecycle_checkpoint_v1",
        "current_promoted_version": "PSM_V0.282",
        "target_promoted": True,
        "status": "v0_282_promoted_v0_283_restart_recovery_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_283_restart_recovery_contract",
        "required_decision": "无；继续保持临时记忆和无原文磁盘持久化。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.283")


if __name__ == "__main__":
    main()
