#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.290_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.291_project_status.json"
BROWSER_DIR = RUNTIME / "v0_291_cancel_retry_browser_regression"
BROWSER = BROWSER_DIR / "report.json"
CHECKPOINT = RUNTIME / "v0_291_cancel_retry_checkpoint.json"
MANIFEST = RUNTIME / "v0_291_cancel_retry_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    browser = read(BROWSER)
    checks = {
        "source_version_is_v0_290": source.get("current_version") == "psm_v0.290",
        "browser_report_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "cancel_under_one_second": browser.get("desktop", {}).get("cancellationMs", 1000) < 1000,
        "prompt_preserved": browser.get("desktop", {}).get("cancelled", {}).get("promptValue") != "",
        "cancelled_turn_not_duplicated": browser.get("desktop", {}).get("cancelled", {}).get("userMessages") == 1,
        "retry_single_turn_completed": browser.get("desktop", {}).get("retried", {}).get("userMessages") == 1 and browser.get("desktop", {}).get("retried", {}).get("assistantMessages") == 1,
        "mobile_no_overflow": browser.get("mobile", {}).get("horizontalOverflow") is False,
        "console_errors_zero": browser.get("desktop", {}).get("consoleErrors") == 0 and browser.get("mobile", {}).get("consoleErrors") == 0,
        "server_cancel_not_overclaimed": browser.get("server_generation_cancellation_claimed") is False,
        "network_streaming_not_overclaimed": browser.get("network_streaming_claimed") is False,
        "external_release_closed": browser.get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.291 promotion failed: {[key for key, value in checks.items() if not value]}")
    interaction_gate = {
        "decision": "client_cancel_retry_interaction_gate_passed",
        "passed": True,
        "checks": checks,
        "cancellation_scope": "client_transport_wait_only",
        "cancel_p95_claimed": False,
        "observed_cancel_ms": browser["desktop"]["cancellationMs"],
        "server_generation_cancellation_claimed": False,
        "network_streaming_claimed": False,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.291",
        "previous_formal_version": "psm_v0.290",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "client_cancel_retry_interaction_gate_passed",
        "v0_291_cancel_retry_gate": interaction_gate,
        "next_stage": {
            "version": "PSM_V0.292",
            "objective": "评估服务端生成取消与真正网络流式输出，先验证 Ollama 协议和线程资源回收，不把客户端 abort 误写成推理已停止。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_291_browser_report": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_291_browser_desktop": str((BROWSER_DIR / "desktop-cancel-retry.png").relative_to(PSM_ROOT)),
        "v0_291_browser_mobile": str((BROWSER_DIR / "mobile-cancel-controls.png").relative_to(PSM_ROOT)),
        "v0_291_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_291_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.291_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_291_cancel_retry_promotion_manifest_v1",
        "version": "PSM_V0.291",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": interaction_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "cancel_retry_interaction": interaction_gate,
        "evidence": {
            "browser_report": str(BROWSER.relative_to(PSM_ROOT)),
            "desktop_screenshot": str((BROWSER_DIR / "desktop-cancel-retry.png").relative_to(PSM_ROOT)),
            "mobile_screenshot": str((BROWSER_DIR / "mobile-cancel-controls.png").relative_to(PSM_ROOT)),
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
        "schema_version": "psm_v0_291_cancel_retry_checkpoint_v1",
        "current_promoted_version": "PSM_V0.291",
        "target_promoted": True,
        "status": "v0_291_promoted_v0_292_server_cancel_streaming_research_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_292_server_cancel_streaming_contract",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.292")


if __name__ == "__main__":
    main()
