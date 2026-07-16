#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.275_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.276_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_276_long_horizon_state_compression_contract.json"
REPORT = RUNTIME / "v0_276_long_horizon_state_compression_report.json"
GATE = RUNTIME / "v0_276_long_horizon_state_compression_gate.json"
LEDGER = RUNTIME / "v0_276_long_horizon_state_compression_initial_failure_ledger.json"
EVALUATOR_GAP = RUNTIME / "v0_276_long_horizon_state_compression_evaluator_gap_report.json"
DOCKER = RUNTIME / "v0_276_long_horizon_state_compression_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_276_long_horizon_state_compression_checkpoint.json"
MANIFEST = RUNTIME / "v0_276_long_horizon_state_compression_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, report, gate, ledger, evaluator_gap, docker, checkpoint = map(
        read,
        (SOURCE, CONTRACT, REPORT, GATE, LEDGER, EVALUATOR_GAP, DOCKER, CHECKPOINT),
    )
    summary = report["summary"]
    gap_summary = evaluator_gap["summary"]
    checks = {
        "source_version_is_v0_275": source.get("current_version") == "psm_v0.275",
        "gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "all_ten_cases_passed": report.get("passed") is True and summary.get("cases") == summary.get("passed") == 10,
        "all_five_families_passed": len(summary.get("families") or {}) == 5 and all(item["cases"] == item["passed"] == 2 for item in summary["families"].values()),
        "compression_present_for_all": summary.get("compression_missing") == 0,
        "capsule_recovery_failures_zero": summary.get("capsule_recovery_failures") == 0,
        "historical_window_baseline_fails_all": summary.get("window_baseline_failures") == 10,
        "stale_state_violations_zero": summary.get("stale_state_violations") == 0,
        "initial_failures_retained": ledger.get("initial_failure_count") == 10 and ledger.get("append_only") is True,
        "evaluator_gap_retained": gap_summary.get("failed") == 10 and gap_summary.get("compression_missing") == 0 and gap_summary.get("capsule_recovery_failures") == 10,
        "host_docker_boundary_passed": docker.get("passed") is True and all(docker.get("checks", {}).values()),
        "human_feedback_zero": docker.get("human_feedback_collected") is False,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.276 promotion failed: {[key for key, value in checks.items() if not value]}")

    long_horizon_gate = {
        "decision": gate["decision"],
        "passed": True,
        "cases": 10,
        "cases_passed": 10,
        "families": 5,
        "initial_failure_count": 10,
        "evaluator_gap_failures_retained": 10,
        "historical_window_baseline_failures": 10,
        "compression_missing": 0,
        "capsule_recovery_failures": 0,
        "stale_state_violations": 0,
        "total_duration_ms": summary["total_duration_ms"],
        "maximum_input_messages": max(row["input_messages"] for row in report["rows"]),
        "maximum_retained_user_statements": contract["evaluation"]["maximum_retained_user_statements"],
        "synthetic_only": True,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "contract_sha256": digest(contract),
        "gate_sha256": digest(gate),
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.276",
        "previous_formal_version": "psm_v0.275",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "long_horizon_durable_state_compression_gate_passed_after_retained_0_of_10_baseline",
        "v0_276_long_horizon_state_compression_gate": long_horizon_gate,
        "next_stage": {
            "version": "PSM_V0.277",
            "objective": "对冻结的 V0.276 长时程对话答案和状态恢复结果执行来源隔离的独立外部语义评审；只提交合成长对话与最终答案，不提交规则、私人资料、状态标签或训练字段。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_276_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_276_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_276_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_276_initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
        "v0_276_evaluator_gap": str(EVALUATOR_GAP.relative_to(PSM_ROOT)),
        "v0_276_docker": str(DOCKER.relative_to(PSM_ROOT)),
        "v0_276_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_276_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.276_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_276_long_horizon_state_compression_promotion_manifest_v1",
        "version": "PSM_V0.276",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "long_horizon_state_compression": long_horizon_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "report": str(REPORT.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
            "initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
            "evaluator_gap": str(EVALUATOR_GAP.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.276",
        "target_promoted": True,
        "status": "v0_276_promoted_v0_277_external_long_horizon_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_277_external_long_horizon_review_package",
        "required_decision": "无；合成外部评审可在 1,000,000-token 授权内自动执行。",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.277")


if __name__ == "__main__":
    main()
