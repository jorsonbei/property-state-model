#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.293_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.294_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_294_content_free_telemetry_contract.json"
BASELINE = RUNTIME / "v0_294_content_free_telemetry_baseline.json"
REPORT = RUNTIME / "v0_294_content_free_telemetry_report.json"
GATE = RUNTIME / "v0_294_content_free_telemetry_gate.json"
REGRESSION = RUNTIME / "v0_294_regression_report.json"
CHECKPOINT = RUNTIME / "v0_294_content_free_telemetry_checkpoint.json"
MANIFEST = RUNTIME / "v0_294_content_free_telemetry_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def latency_total(health: dict, series: str) -> int:
    return sum(bucket["count"] for bucket in health["latency_buckets_ms"][series])


def main() -> None:
    source = read(SOURCE)
    contract = read(CONTRACT)
    baseline = read(BASELINE)
    report = read(REPORT)
    gate = read(GATE)
    regression = read(REGRESSION)
    runtimes = report.get("runtimes", [])
    expected_delta = {
        "accepted": 2,
        "capacity_rejected": 0,
        "duplicate_rejected": 1,
        "invalid_rejected": 1,
        "cancel_requests": 2,
        "cancel_active": 1,
        "cancel_inactive": 1,
        "cancelled": 1,
        "completed": 1,
        "failed": 0,
    }
    checks = {
        "source_version_is_v0_293": source.get("current_version") == "psm_v0.293",
        "contract_frozen_before_implementation": contract.get("frozen_before_implementation") is True,
        "baseline_retains_observability_gap": baseline.get("observed", {}).get("health_endpoint_present") is False,
        "runtime_gate_passed": report.get("passed") is True and gate.get("passed") is True,
        "host_and_docker_present": [item.get("runtime_id") for item in runtimes] == ["host", "docker"],
        "counter_deltas_exact": len(runtimes) == 2 and all(
            item.get("observed_counter_delta") == expected_delta for item in runtimes
        ),
        "latency_totals_exact": len(runtimes) == 2 and all(
            latency_total(item["after"], "completed") - latency_total(item["before"], "completed") == 1
            and latency_total(item["after"], "cancelled") - latency_total(item["before"], "cancelled") == 1
            and latency_total(item["after"], "failed") - latency_total(item["before"], "failed") == 0
            for item in runtimes
        ),
        "active_returns_to_zero": len(runtimes) == 2 and all(
            item.get("after", {}).get("active_requests") == 0 for item in runtimes
        ),
        "raw_content_not_persisted": report.get("disk_sentinel_hits") == [],
        "regression_257_or_more_passed": regression.get("passed") is True
        and regression.get("tests_passed", 0) >= 257,
        "external_release_closed": contract.get("release_boundary", {}).get("external_release_authority") is False,
    }
    if not all(checks.values()):
        failed = [key for key, value in checks.items() if not value]
        raise SystemExit(f"V0.294 promotion failed: {failed}")

    telemetry_gate = {
        "decision": "content_free_telemetry_gate_passed",
        "passed": True,
        "checks": checks,
        "health_endpoint": contract["endpoint"]["path"],
        "counter_names": contract["counters"],
        "latency_bucket_upper_bounds_ms": contract["latency"]["bucket_upper_bounds_ms"],
        "host_counter_delta": runtimes[0]["observed_counter_delta"],
        "docker_counter_delta": runtimes[1]["observed_counter_delta"],
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update(
        {
            "current_version": "psm_v0.294",
            "previous_formal_version": "psm_v0.293",
            "source_evidence_version": "psm_v0.251",
            "completed_result": "content_free_telemetry_gate_passed",
            "v0_294_content_free_telemetry_gate": telemetry_gate,
            "next_stage": {
                "version": "PSM_V0.295",
                "objective": "确定是否开启外部部署与真实用户验证路线，并冻结公开范围、数据责任、托管、预算和停止条件",
                "blocked": True,
                "requires_user_input": True,
            },
        }
    )
    target.setdefault("primary_artifacts", {}).update(
        {
            "v0_294_contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "v0_294_baseline": str(BASELINE.relative_to(PSM_ROOT)),
            "v0_294_report": str(REPORT.relative_to(PSM_ROOT)),
            "v0_294_gate": str(GATE.relative_to(PSM_ROOT)),
            "v0_294_regression": str(REGRESSION.relative_to(PSM_ROOT)),
            "v0_294_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
            "v0_294_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
            "project_status": "project_status_out/psm_v0.294_project_status.json",
        }
    )
    write(TARGET, target)

    next_stage = target["next_stage"]
    manifest = {
        "schema_version": "psm_v0_294_content_free_telemetry_promotion_manifest_v1",
        "version": "PSM_V0.294",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": telemetry_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "content_free_telemetry_gate": telemetry_gate,
        "release_boundary": contract["release_boundary"],
        "next_stage": next_stage,
    }
    checkpoint = {
        "schema_version": "psm_v0_294_content_free_telemetry_checkpoint_v1",
        "current_promoted_version": "PSM_V0.294",
        "target_promoted": True,
        "status": "blocked_v0_295_external_deployment_authorization_required",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": True,
        "next_action": "obtain_v0_295_external_deployment_scope_decision",
        "required_decision": (
            "请决定是否授权开启外部部署与真实用户验证路线；若授权，需要同时确定访问范围、"
            "是否允许处理真实对话、托管/域名预算、日志保留期和紧急停止责任人。"
        ),
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.295 blocked on external deployment authorization")


if __name__ == "__main__":
    main()
