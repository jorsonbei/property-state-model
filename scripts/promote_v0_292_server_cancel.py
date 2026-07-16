#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.291_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.292_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_292_server_cancel_contract.json"
BASELINE = RUNTIME / "v0_292_server_cancel_baseline.json"
RUNTIME_REPORT = RUNTIME / "v0_292_server_cancel_runtime_report.json"
RUNTIME_GATE = RUNTIME / "v0_292_server_cancel_runtime_gate.json"
BROWSER_DIR = RUNTIME / "v0_292_server_cancel_browser_regression"
BROWSER = BROWSER_DIR / "report.json"
REGRESSION = RUNTIME / "v0_292_regression_report.json"
REGRESSION_GAP = RUNTIME / "v0_292_regression_attempt_1_evaluator_gap.json"
CHECKPOINT = RUNTIME / "v0_292_server_cancel_checkpoint.json"
MANIFEST = RUNTIME / "v0_292_server_cancel_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    contract = read(CONTRACT)
    baseline = read(BASELINE)
    runtime = read(RUNTIME_REPORT)
    runtime_gate = read(RUNTIME_GATE)
    browser = read(BROWSER)
    regression = read(REGRESSION)
    checks = {
        "source_version_is_v0_291": source.get("current_version") == "psm_v0.291",
        "contract_frozen_before_implementation": contract.get("frozen_before_implementation") is True,
        "baseline_retains_client_only_gap": baseline.get("observed", {}).get("ollama_generation_cooperatively_cancelled") is False,
        "runtime_gate_passed": runtime.get("passed") is True and runtime_gate.get("passed") is True,
        "host_three_of_three_cancelled": sum(row["passed"] for row in runtime["runtimes"][0]["cancel_rows"]) == 3,
        "docker_three_of_three_cancelled": sum(row["passed"] for row in runtime["runtimes"][1]["cancel_rows"]) == 3,
        "server_stop_under_two_seconds": max(item["cancel_max_ms"] for item in runtime["runtimes"]) <= 2000,
        "host_and_docker_retry_pass": all(item["retry"]["passed"] for item in runtime["runtimes"]),
        "cancelled_content_not_persisted": runtime.get("disk_sentinel_hits") == [],
        "browser_report_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "desktop_and_mobile_server_ack": browser["desktop"]["cancelled"]["serverCancel"]["generationWasActive"] is True and browser["mobile"]["cancelled"]["serverCancel"]["generationWasActive"] is True,
        "regression_249_or_more_passed": regression.get("passed") is True and regression.get("tests_passed", 0) >= 249,
        "regression_evaluator_gap_retained": REGRESSION_GAP.exists(),
        "raw_chunks_not_visible": contract["delivery_contract"]["raw_model_chunks_user_visible"] is False,
        "network_streaming_not_overclaimed": browser.get("network_token_streaming_claimed") is False,
        "external_release_closed": browser.get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.292 promotion failed: {[key for key, value in checks.items() if not value]}")

    server_cancel_gate = {
        "decision": "server_cancel_and_review_before_display_gate_passed",
        "passed": True,
        "checks": checks,
        "host_cancel_max_ms": runtime["runtimes"][0]["cancel_max_ms"],
        "docker_cancel_max_ms": runtime["runtimes"][1]["cancel_max_ms"],
        "browser_cancel_ms": browser["desktop"]["cancellationMs"],
        "server_generation_cancellation_claimed": True,
        "cancellation_claim_scope": "server_owned_ollama_http_connection_and_chat_worker",
        "model_compute_stop_directly_instrumented": False,
        "raw_model_chunks_user_visible": False,
        "network_token_streaming_claimed": False,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.292",
        "previous_formal_version": "psm_v0.291",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "server_cancel_and_review_before_display_gate_passed",
        "v0_292_server_cancel_gate": server_cancel_gate,
        "next_stage": {
            "version": "PSM_V0.293",
            "objective": "冻结并验证并发容量、backpressure、重复 request_id、取消风暴与断线竞态；容量满时必须拒绝新请求而不是驱逐在途任务。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_292_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_292_baseline": str(BASELINE.relative_to(PSM_ROOT)),
        "v0_292_runtime_report": str(RUNTIME_REPORT.relative_to(PSM_ROOT)),
        "v0_292_runtime_gate": str(RUNTIME_GATE.relative_to(PSM_ROOT)),
        "v0_292_browser_report": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_292_browser_desktop": str((BROWSER_DIR / "desktop-server-cancel-retry.png").relative_to(PSM_ROOT)),
        "v0_292_browser_mobile": str((BROWSER_DIR / "mobile-server-cancel.png").relative_to(PSM_ROOT)),
        "v0_292_regression": str(REGRESSION.relative_to(PSM_ROOT)),
        "v0_292_regression_evaluator_gap": str(REGRESSION_GAP.relative_to(PSM_ROOT)),
        "v0_292_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_292_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.292_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_292_server_cancel_promotion_manifest_v1",
        "version": "PSM_V0.292",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": server_cancel_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "server_cancel_gate": server_cancel_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "baseline": str(BASELINE.relative_to(PSM_ROOT)),
            "runtime_report": str(RUNTIME_REPORT.relative_to(PSM_ROOT)),
            "browser_report": str(BROWSER.relative_to(PSM_ROOT)),
            "regression_report": str(REGRESSION.relative_to(PSM_ROOT)),
        },
        "release_boundary": {
            "model_compute_stop_directly_instrumented": False,
            "network_token_streaming_claimed": False,
            "human_validation_claimed": False,
            "persistent_conversation_memory_enabled": False,
            "public_service_allowed": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "next_stage": target["next_stage"],
    }
    checkpoint = {
        "schema_version": "psm_v0_292_server_cancel_checkpoint_v1",
        "current_promoted_version": "PSM_V0.292",
        "target_promoted": True,
        "status": "v0_292_promoted_v0_293_concurrency_backpressure_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_293_concurrency_backpressure_contract",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.293")


if __name__ == "__main__":
    main()
