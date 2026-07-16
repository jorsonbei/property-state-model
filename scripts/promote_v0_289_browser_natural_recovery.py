#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.288_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.289_project_status.json"
BROWSER_DIR = RUNTIME / "v0_289_natural_recovery_browser_regression"
BROWSER = BROWSER_DIR / "report.json"
CHECKPOINT = RUNTIME / "v0_289_browser_natural_recovery_checkpoint.json"
MANIFEST = RUNTIME / "v0_289_browser_natural_recovery_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    browser = read(BROWSER)
    checks = {
        "source_version_is_v0_288": source.get("current_version") == "psm_v0.288",
        "browser_report_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "reset_reference_recovers": browser.get("desktop", {}).get("reset", {}).get("continuity") == "reset",
        "new_task_returns_to_active": browser.get("desktop", {}).get("newTask", {}).get("continuity") == "active",
        "reload_reference_recovers": browser.get("desktop", {}).get("reload", {}).get("continuity") == "reload",
        "restarted_reference_recovers": browser.get("desktop", {}).get("restarted", {}).get("continuity") == "restarted",
        "mobile_interaction_passed": browser.get("mobile", {}).get("recovery", {}).get("continuity") == "reset",
        "desktop_and_mobile_no_overflow": (
            browser.get("desktop", {}).get("horizontalOverflow") is False
            and browser.get("mobile", {}).get("horizontalOverflow") is False
        ),
        "console_errors_zero": (
            browser.get("desktop", {}).get("consoleErrors") == 0
            and browser.get("mobile", {}).get("consoleErrors") == 0
        ),
        "human_feedback_zero": browser.get("human_feedback_collected") is False,
        "external_release_closed": browser.get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.289 promotion failed: {[key for key, value in checks.items() if not value]}")
    browser_gate = {
        "decision": "natural_recovery_real_browser_gate_passed",
        "passed": True,
        "checks": checks,
        "desktop_interactions": 4,
        "mobile_interactions": 1,
        "desktop_horizontal_overflow": False,
        "mobile_horizontal_overflow": False,
        "console_errors": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.289",
        "previous_formal_version": "psm_v0.288",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "natural_recovery_real_browser_gate_passed",
        "v0_289_browser_natural_recovery_gate": browser_gate,
        "next_stage": {
            "version": "PSM_V0.290",
            "objective": "冻结并测量正常聊天、自然指代恢复与 Docker 生成的延迟预算，区分确定性恢复路径和本地模型生成瓶颈。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_289_browser_report": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_289_browser_desktop": str((BROWSER_DIR / "desktop-natural-recovery.png").relative_to(PSM_ROOT)),
        "v0_289_browser_mobile": str((BROWSER_DIR / "mobile-natural-recovery.png").relative_to(PSM_ROOT)),
        "v0_289_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_289_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.289_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_289_browser_natural_recovery_promotion_manifest_v1",
        "version": "PSM_V0.289",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": browser_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "browser_natural_recovery": browser_gate,
        "evidence": {
            "browser_report": str(BROWSER.relative_to(PSM_ROOT)),
            "desktop_screenshot": str((BROWSER_DIR / "desktop-natural-recovery.png").relative_to(PSM_ROOT)),
            "mobile_screenshot": str((BROWSER_DIR / "mobile-natural-recovery.png").relative_to(PSM_ROOT)),
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
        "schema_version": "psm_v0_289_browser_natural_recovery_checkpoint_v1",
        "current_promoted_version": "PSM_V0.289",
        "target_promoted": True,
        "status": "v0_289_promoted_v0_290_latency_budget_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_290_latency_budget_contract",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.290")


if __name__ == "__main__":
    main()
