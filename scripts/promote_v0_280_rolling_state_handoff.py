#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.279_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.280_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_280_rolling_state_handoff_contract.json"
LEDGER = RUNTIME / "v0_280_window_truncation_initial_failure_ledger.json"
REPORT = RUNTIME / "v0_280_rolling_state_handoff_report.json"
GATE = RUNTIME / "v0_280_rolling_state_handoff_gate.json"
DOCKER = RUNTIME / "v0_280_rolling_state_handoff_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_280_rolling_state_handoff_checkpoint.json"
MANIFEST = RUNTIME / "v0_280_rolling_state_handoff_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, ledger, report, gate, docker, checkpoint = map(
        read,
        (SOURCE, CONTRACT, LEDGER, REPORT, GATE, DOCKER, CHECKPOINT),
    )
    summary = report["summary"]
    checks = {
        "source_version_is_v0_279": source.get("current_version") == "psm_v0.279",
        "gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "all_four_cases_passed": report.get("passed") is True and summary.get("cases") == summary.get("passed") == 4,
        "initial_four_failures_retained": ledger.get("failed") == 4 and ledger.get("append_only") is True,
        "rolling_state_present_for_all": summary.get("rolling_state_missing") == 0,
        "rolling_recovery_failures_zero": summary.get("rolling_recovery_failures") == 0,
        "stale_state_violations_zero": summary.get("stale_state_violations") == 0,
        "host_docker_boundary_passed": docker.get("passed") is True and all(docker.get("checks", {}).values()),
        "ephemeral_memory_only": contract["privacy"].get("ephemeral_memory_only") is True,
        "disk_persistence_disabled": contract["privacy"].get("disk_persistence_of_user_statements_allowed") is False,
        "human_feedback_zero": docker.get("human_feedback_collected") is False,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.280 promotion failed: {[key for key, value in checks.items() if not value]}")

    rolling_gate = {
        "decision": gate["decision"],
        "passed": True,
        "cases": 4,
        "cases_passed": 4,
        "families": 4,
        "initial_window_truncation_failures": 4,
        "window_messages": contract["evaluation"]["window_messages"],
        "maximum_effective_context_messages": summary["maximum_effective_context_messages"],
        "maximum_rolling_user_statements": contract["evaluation"]["maximum_rolling_user_statements"],
        "rolling_recovery_failures": 0,
        "stale_state_violations": 0,
        "ephemeral_idle_seconds": contract["privacy"]["maximum_session_idle_seconds"],
        "maximum_sessions": contract["privacy"]["maximum_sessions"],
        "disk_persistence_of_user_statements": False,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "contract_sha256": digest(contract),
        "gate_sha256": digest(gate),
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.280",
        "previous_formal_version": "psm_v0.279",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "rolling_state_handoff_gate_passed_after_retained_4_of_4_window_truncation_failure",
        "v0_280_rolling_state_handoff_gate": rolling_gate,
        "next_stage": {
            "version": "PSM_V0.281",
            "objective": "对跨窗口滚动状态恢复执行来源隔离的独立外部语义评审，并验证会话过期、重置与并发隔离边界。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_280_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_280_initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
        "v0_280_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_280_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_280_docker": str(DOCKER.relative_to(PSM_ROOT)),
        "v0_280_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_280_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.280_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_280_rolling_state_handoff_promotion_manifest_v1",
        "version": "PSM_V0.280",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "rolling_state_handoff": rolling_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
            "report": str(REPORT.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "privacy": contract["privacy"],
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.280",
        "target_promoted": True,
        "status": "v0_280_promoted_v0_281_external_and_isolation_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_281_external_rolling_state_review_and_isolation_contract",
        "required_decision": "无；合成外部评审可在 1,000,000-token 授权内自动执行。",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.281")


if __name__ == "__main__":
    main()
