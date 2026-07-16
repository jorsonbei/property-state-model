#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.285_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.286_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_286_natural_recovery_reference_contract.json"
BASELINE = RUNTIME / "v0_286_natural_recovery_reference_initial_failure_ledger.json"
REPORT = RUNTIME / "v0_286_natural_recovery_reference_report.json"
GATE = RUNTIME / "v0_286_natural_recovery_reference_gate.json"
CHECKPOINT = RUNTIME / "v0_286_natural_recovery_reference_checkpoint.json"
MANIFEST = RUNTIME / "v0_286_natural_recovery_reference_promotion_manifest.json"


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
    summary = report.get("summary", {})
    checks = {
        "source_version_is_v0_285": source.get("current_version") == "psm_v0.285",
        "contract_frozen_and_synthetic": contract.get("frozen") is True and contract.get("synthetic_only") is True,
        "baseline_retained_at_four_of_sixteen": baseline.get("passed") == 4 and baseline.get("failed") == 12,
        "local_gate_passed_sixteen_of_sixteen": gate.get("passed") is True and summary.get("passed") == 16,
        "positive_recall_exact": summary.get("positive_recall") == 1.0,
        "negative_specificity_exact": summary.get("negative_specificity") == 1.0,
        "forty_eight_loss_answers_checked": summary.get("memory_loss_answer_checks") == 48,
        "zero_archived_fact_fabrication": summary.get("archived_fact_fabrications") == 0,
        "external_release_closed": contract["requirements"].get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.286 promotion failed: {[key for key, value in checks.items() if not value]}")

    natural_reference_gate = {
        "decision": "natural_recovery_reference_gate_passed",
        "passed": True,
        "baseline_passed": 4,
        "baseline_failed": 12,
        "final_passed": 16,
        "final_failed": 0,
        "positive_reference_cases": 12,
        "negative_new_task_controls": 4,
        "positive_recall": 1.0,
        "negative_specificity": 1.0,
        "memory_loss_answer_checks": 48,
        "archived_fact_fabrications": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.286",
        "previous_formal_version": "psm_v0.285",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "natural_recovery_reference_gate_passed",
        "v0_286_natural_recovery_reference_gate": natural_reference_gate,
        "next_stage": {
            "version": "PSM_V0.287",
            "objective": "对自然指代恢复回答执行独立外部语义审查，并复核中英文误报、漏报与失忆后事实臆造边界。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_286_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_286_baseline": str(BASELINE.relative_to(PSM_ROOT)),
        "v0_286_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_286_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_286_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_286_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.286_project_status.json",
    })
    write(TARGET, target)

    manifest = {
        "schema_version": "psm_v0_286_natural_recovery_reference_promotion_manifest_v1",
        "version": "PSM_V0.286",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": natural_reference_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "natural_recovery_reference": natural_reference_gate,
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
        "schema_version": "psm_v0_286_natural_recovery_reference_checkpoint_v1",
        "current_promoted_version": "PSM_V0.286",
        "target_promoted": True,
        "status": "v0_286_promoted_v0_287_external_natural_reference_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_287_external_natural_recovery_review",
        "required_decision": "无。合成外部评审在既有 1,000,000 token 授权内自动执行。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.287")


if __name__ == "__main__":
    main()
