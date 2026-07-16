#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.277_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.278_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_278_incremental_long_horizon_stress_contract.json"
REPORT = RUNTIME / "v0_278_incremental_long_horizon_stress_report.json"
GATE = RUNTIME / "v0_278_incremental_long_horizon_stress_gate.json"
DOCKER = RUNTIME / "v0_278_incremental_long_horizon_stress_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_278_incremental_long_horizon_stress_checkpoint.json"
MANIFEST = RUNTIME / "v0_278_incremental_long_horizon_stress_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, report, gate, docker, checkpoint = map(read, (SOURCE, CONTRACT, REPORT, GATE, DOCKER, CHECKPOINT))
    summary = report["summary"]
    checks = {
        "source_version_is_v0_277": source.get("current_version") == "psm_v0.277",
        "gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "all_ten_cases_passed": report.get("passed") is True and summary.get("cases") == summary.get("passed") == 10,
        "all_five_families_passed": len(summary.get("families") or {}) == 5 and all(item["cases"] == item["passed"] == 2 for item in summary["families"].values()),
        "stress_levels_exact": summary.get("message_levels") == [81, 119],
        "compression_present_for_all": summary.get("compression_missing") == 0,
        "capsule_recovery_failures_zero": summary.get("capsule_recovery_failures") == 0,
        "historical_window_baseline_fails_all": summary.get("window_baseline_failures") == 10,
        "stale_state_violations_zero": summary.get("stale_state_violations") == 0,
        "latency_within_contract": (
            summary.get("total_duration_ms", 10_001) <= contract["evaluation"]["maximum_total_duration_ms"]
            and summary.get("p95_duration_ms", 3_001) <= contract["evaluation"]["maximum_p95_duration_ms"]
        ),
        "host_docker_boundary_passed": docker.get("passed") is True and all(docker.get("checks", {}).values()),
        "human_feedback_zero": docker.get("human_feedback_collected") is False,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.278 promotion failed: {[key for key, value in checks.items() if not value]}")

    stress_gate = {
        "decision": gate["decision"],
        "passed": True,
        "cases": 10,
        "cases_passed": 10,
        "families": 5,
        "message_levels": summary["message_levels"],
        "maximum_messages": summary["maximum_messages"],
        "historical_window_baseline_failures": 10,
        "compression_missing": 0,
        "capsule_recovery_failures": 0,
        "stale_state_violations": 0,
        "total_duration_ms": summary["total_duration_ms"],
        "p95_duration_ms": summary["p95_duration_ms"],
        "maximum_retained_user_statements": contract["evaluation"]["maximum_retained_user_statements"],
        "synthetic_only": True,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "contract_sha256": digest(contract),
        "gate_sha256": digest(gate),
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.278",
        "previous_formal_version": "psm_v0.277",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "incremental_long_horizon_stress_gate_passed_at_81_and_119_messages",
        "v0_278_incremental_long_horizon_stress_gate": stress_gate,
        "next_stage": {
            "version": "PSM_V0.279",
            "objective": "对冻结的 81 与 119 消息压力测试执行来源隔离的独立外部语义评审，只提交合成长对话与最终答案。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_278_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_278_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_278_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_278_docker": str(DOCKER.relative_to(PSM_ROOT)),
        "v0_278_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_278_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.278_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_278_incremental_long_horizon_stress_promotion_manifest_v1",
        "version": "PSM_V0.278",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "incremental_long_horizon_stress": stress_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "report": str(REPORT.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.278",
        "target_promoted": True,
        "status": "v0_278_promoted_v0_279_external_stress_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_279_external_stress_review_package",
        "required_decision": "无；合成外部评审可在 1,000,000-token 授权内自动执行。",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.279")


if __name__ == "__main__":
    main()
