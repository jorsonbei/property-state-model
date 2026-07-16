#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.292_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.293_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_293_concurrency_backpressure_contract.json"
BASELINE = RUNTIME / "v0_293_concurrency_backpressure_baseline.json"
REPORT = RUNTIME / "v0_293_concurrency_backpressure_report.json"
GATE = RUNTIME / "v0_293_concurrency_backpressure_gate.json"
BROWSER_DIR = RUNTIME / "v0_293_backpressure_browser_regression"
BROWSER = BROWSER_DIR / "report.json"
BROWSER_GAP = RUNTIME / "v0_293_backpressure_browser_attempt_1_evaluator_gap.json"
REGRESSION = RUNTIME / "v0_293_regression_report.json"
POST_PROMOTION_FAILURE = RUNTIME / "v0_293_post_promotion_regression_failure.json"
CHECKPOINT = RUNTIME / "v0_293_concurrency_backpressure_checkpoint.json"
MANIFEST = RUNTIME / "v0_293_concurrency_backpressure_promotion_manifest.json"


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
    browser = read(BROWSER)
    regression = read(REGRESSION)
    waves = [wave for runtime in report["runtimes"] for wave in runtime["waves"]]
    checks = {
        "source_version_is_v0_292": source.get("current_version") == "psm_v0.292",
        "contract_frozen_before_implementation": contract.get("frozen_before_implementation") is True,
        "baseline_retains_unbounded_gap": baseline.get("observed", {}).get("operational_active_chat_limit") is None,
        "runtime_gate_passed": report.get("passed") is True and gate.get("passed") is True,
        "four_of_four_waves_passed": len(waves) == 4 and all(wave["passed"] for wave in waves),
        "sixteen_of_sixteen_active_requests_cancelled": sum(
            item.get("status") == 499 for wave in waves for item in wave["chat_results"]
        ) == 16,
        "all_capacity_probes_503": all(wave["capacity_probe"]["status"] == 503 for wave in waves),
        "all_duplicate_probes_409": all(wave["duplicate_probe"]["status"] == 409 for wave in waves),
        "capacity_recovery_passed": all(wave["checks"]["capacity_recovers"] for wave in waves),
        "browser_report_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "browser_evaluator_gap_retained": BROWSER_GAP.exists(),
        "regression_252_or_more_passed": regression.get("passed") is True and regression.get("tests_passed", 0) >= 252,
        "post_promotion_regression_failure_retained": POST_PROMOTION_FAILURE.exists(),
        "raw_content_not_persisted": report.get("disk_sentinel_hits") == [],
        "network_streaming_not_overclaimed": browser.get("network_token_streaming_claimed") is False,
        "external_release_closed": browser.get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.293 promotion failed: {[key for key, value in checks.items() if not value]}")
    concurrency_gate = {
        "decision": "concurrency_backpressure_gate_passed",
        "passed": True,
        "checks": checks,
        "max_active_chat_requests": contract["admission"]["max_active_chat_requests"],
        "queue_enabled": False,
        "host_capacity_max_ms": gate["host_capacity_max_ms"],
        "docker_capacity_max_ms": gate["docker_capacity_max_ms"],
        "host_cancel_storm_max_ms": gate["host_cancel_storm_max_ms"],
        "docker_cancel_storm_max_ms": gate["docker_cancel_storm_max_ms"],
        "browser_capacity_ui_ms": browser["desktop"]["capacityUiMs"],
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.293",
        "previous_formal_version": "psm_v0.292",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "concurrency_backpressure_gate_passed",
        "v0_293_concurrency_backpressure_gate": concurrency_gate,
        "next_stage": {
            "version": "PSM_V0.294",
            "objective": "加入内容为空的运行遥测与健康快照，统计 accepted、capacity-rejected、duplicate、cancelled、completed 和延迟，不记录 prompt、answer、session_id 或 request_id。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_293_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_293_baseline": str(BASELINE.relative_to(PSM_ROOT)),
        "v0_293_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_293_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_293_browser": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_293_browser_desktop": str((BROWSER_DIR / "desktop-capacity-recovery.png").relative_to(PSM_ROOT)),
        "v0_293_browser_mobile": str((BROWSER_DIR / "mobile-idle.png").relative_to(PSM_ROOT)),
        "v0_293_browser_evaluator_gap": str(BROWSER_GAP.relative_to(PSM_ROOT)),
        "v0_293_regression": str(REGRESSION.relative_to(PSM_ROOT)),
        "v0_293_post_promotion_failure": str(POST_PROMOTION_FAILURE.relative_to(PSM_ROOT)),
        "v0_293_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_293_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.293_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_293_concurrency_backpressure_promotion_manifest_v1",
        "version": "PSM_V0.293",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": concurrency_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "concurrency_backpressure_gate": concurrency_gate,
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    checkpoint = {
        "schema_version": "psm_v0_293_concurrency_backpressure_checkpoint_v1",
        "current_promoted_version": "PSM_V0.293",
        "target_promoted": True,
        "status": "v0_293_promoted_v0_294_content_free_telemetry_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_294_content_free_telemetry_contract",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.294")


if __name__ == "__main__":
    main()
