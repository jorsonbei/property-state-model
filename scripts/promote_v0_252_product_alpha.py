from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.251_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.252_project_status.json"
BROWSER_REPORT = PSM_ROOT / "runtime" / "v0_252_browser_regression" / "report.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_252_product_checkpoint.json"
MANIFEST = PSM_ROOT / "runtime" / "v0_252_product_promotion_manifest.json"


REQUIRED_BROWSER_CHECKS = (
    "generating_state",
    "cancel_and_input_preservation",
    "retry_without_duplicate_user_message",
    "progressive_answer_display",
    "debug_isolated_from_main_chat",
    "keyboard_enter_submit",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_browser_report(report: dict) -> None:
    if not report.get("passed"):
        raise SystemExit("V0.252 browser report is not passing.")
    checks = report.get("checks") or {}
    missing = [name for name in REQUIRED_BROWSER_CHECKS if checks.get(name) is not True]
    if missing:
        raise SystemExit(f"V0.252 browser report is missing required checks: {missing}")
    if checks.get("desktop_overflow") is not False or checks.get("mobile_overflow") is not False:
        raise SystemExit("V0.252 browser report contains layout overflow.")
    if checks.get("console_errors") != 0:
        raise SystemExit("V0.252 browser report contains console errors.")
    real = report.get("real_backend") or {}
    if real.get("ran") is not True or real.get("console_errors") != 0:
        raise SystemExit("V0.252 real-backend browser smoke did not pass.")
    if real.get("internal_debug_leakage") is not False:
        raise SystemExit("V0.252 real-backend answer leaked internal debug state.")
    if not real.get("selected_model_visible") or int(real.get("answer_characters") or 0) < 80:
        raise SystemExit("V0.252 real-backend answer contract is incomplete.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    browser = read_json(BROWSER_REPORT)
    validate_browser_report(browser)

    checkpoint = {
        "schema_version": "psm_v0_252_product_checkpoint_v1",
        "current_promoted_version": "PSM_V0.252",
        "target_version": "PSM_V0.252",
        "target_promoted": True,
        "status": "promoted_v0_253_real_omega_routes_in_progress",
        "requires_user_input": False,
        "product_gate": {
            "browser_report": "runtime/v0_252_browser_regression/report.json",
            "browser_base_url": browser.get("base_url"),
            "desktop_passed": True,
            "mobile_passed": True,
            "real_backend_passed": True,
            "selected_model": "qwen3.5:9b",
            "answer_minimum_80_characters": True,
            "console_errors": 0,
            "layout_overflow": 0,
            "duplicate_user_messages_after_retry": 0,
            "internal_debug_leakage": False,
        },
        "completed_engineering": [
            "explicit generation phases with elapsed time",
            "AbortController cancellation and 70-second client timeout",
            "retry with preserved input and no duplicate user turn",
            "progressive display after audited answer acceptance",
            "debug evidence isolated from the main conversation",
            "desktop and mobile browser regression",
            "keyboard submission and focus controls",
            "basic ARIA live regions and accessible labels",
            "host and Docker real-backend UI smoke tests",
            "reproducible npm and Makefile browser-test entrypoints",
        ],
        "release_boundary": {
            "external_user_trial_allowed": False,
            "internal_local_demo_only": True,
            "v0_252_promoted": True,
            "v0_253_route_work_allowed": True,
        },
        "required_decision": (
            "No user decision is currently required. Execute V0.253 real Omega route and tool-evidence work "
            "while keeping external user trial and rule replacement closed."
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.252"
    target["previous_formal_version"] = "psm_v0.251"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "product_ux_and_browser_regression"
    target["product_ux_gate"] = checkpoint["product_gate"]
    target["next_stage"] = {
        "version": "PSM_V0.253",
        "objective": (
            "Replace route labels with executable local state, source/retrieval, code-check, and file-evidence "
            "adapters; record provenance and failures without allowing tool output to bypass PSM gating."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {})["product_ux_gate"] = (
        "runtime/v0_252_browser_regression/report.json"
    )
    target["primary_artifacts"]["product_checkpoint"] = "runtime/v0_252_product_checkpoint.json"
    target["primary_artifacts"]["project_status"] = "project_status_out/psm_v0.252_project_status.json"
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_252_product_promotion_manifest_v1",
        "version": "PSM_V0.252",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "core_source_version": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "selected_model": "qwen3.5:9b",
        "product_gate": checkpoint["product_gate"],
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)

    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
