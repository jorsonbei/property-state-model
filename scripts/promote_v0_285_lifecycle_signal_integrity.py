#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.284_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.285_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_285_lifecycle_signal_integrity_contract.json"
BASELINE = RUNTIME / "v0_285_lifecycle_signal_integrity_initial_failure_ledger.json"
REPORT = RUNTIME / "v0_285_lifecycle_signal_integrity_report.json"
GATE = RUNTIME / "v0_285_lifecycle_signal_integrity_gate.json"
RUNTIME_BOUNDARY = RUNTIME / "v0_285_host_docker_integrity_boundary.json"
CHECKPOINT = RUNTIME / "v0_285_lifecycle_signal_integrity_checkpoint.json"
MANIFEST = RUNTIME / "v0_285_lifecycle_signal_integrity_promotion_manifest.json"


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
    checks = {
        "source_version_is_v0_284": source.get("current_version") == "psm_v0.284",
        "contract_frozen_and_synthetic": contract.get("frozen") is True and contract.get("synthetic_only") is True,
        "baseline_retained_at_five_of_eight": baseline.get("passed") == 5 and baseline.get("failed") == 3,
        "local_gate_passed_eight_of_eight": gate.get("passed") is True and report.get("summary", {}).get("passed") == 8,
        "zero_memory_resurrection": report.get("summary", {}).get("memory_resurrection_events") == 0,
        "zero_cross_session_leaks": report.get("summary", {}).get("cross_session_leaks") == 0,
        "host_docker_runtime_passed": runtime_boundary.get("passed") is True and all(runtime_boundary.get("checks", {}).values()),
        "persistent_memory_closed": runtime_boundary["checks"].get("persistent_memory_closed") is True,
        "external_release_closed": contract["requirements"].get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.285 promotion failed: {[key for key, value in checks.items() if not value]}")
    integrity_gate = {
        "decision": "lifecycle_signal_integrity_and_runtime_gate_passed",
        "passed": True,
        "baseline_passed": 5,
        "baseline_failed": 3,
        "final_passed": 8,
        "final_failed": 0,
        "memory_resurrection_events": 0,
        "cross_session_leaks": 0,
        "concurrent_sessions": 32,
        "maximum_tombstones": 128,
        "host_runtime": "passed",
        "docker_runtime": "passed",
        "user_statement_disk_writes": 0,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.285",
        "previous_formal_version": "psm_v0.284",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "lifecycle_signal_integrity_and_runtime_gate_passed",
        "v0_285_lifecycle_signal_integrity_gate": integrity_gate,
        "next_stage": {
            "version": "PSM_V0.286",
            "objective": "冻结并验证失忆后的自然指代改写，包括不含“之前、刚才、最早”等固定词的代号、文件、安排和未完成事项追问，防止改写绕过恢复边界。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_285_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_285_baseline": str(BASELINE.relative_to(PSM_ROOT)),
        "v0_285_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_285_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_285_runtime_boundary": str(RUNTIME_BOUNDARY.relative_to(PSM_ROOT)),
        "v0_285_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_285_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.285_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_promotion_manifest_v1",
        "version": "PSM_V0.285",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": integrity_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "lifecycle_signal_integrity": integrity_gate,
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
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_checkpoint_v1",
        "current_promoted_version": "PSM_V0.285",
        "target_promoted": True,
        "status": "v0_285_promoted_v0_286_natural_recovery_reference_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_286_natural_recovery_reference_contract",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.286")


if __name__ == "__main__":
    main()
