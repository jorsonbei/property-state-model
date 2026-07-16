#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.294_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.295_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_295_synthetic_deployment_contract.json"
AMENDMENT = RUNTIME / "v0_295_no_human_decision_amendment.json"
BASELINE = RUNTIME / "v0_295_synthetic_deployment_baseline.json"
REPORT = RUNTIME / "v0_295_synthetic_deployment_report.json"
GATE = RUNTIME / "v0_295_synthetic_deployment_gate.json"
REGRESSION = RUNTIME / "v0_295_regression_report.json"
POST_PROMOTION_FAILURE = RUNTIME / "v0_295_post_promotion_regression_failure.json"
EVALUATOR_GAP = RUNTIME / "v0_295_attempt_1_status_evaluator_gap.json"
CHECKPOINT = RUNTIME / "v0_295_synthetic_deployment_checkpoint.json"
MANIFEST = RUNTIME / "v0_295_synthetic_deployment_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    contract = read(CONTRACT)
    amendment = read(AMENDMENT)
    baseline = read(BASELINE)
    report = read(REPORT)
    gate = read(GATE)
    regression = read(REGRESSION)
    checks = {
        "source_version_is_v0_294": source.get("current_version") == "psm_v0.294",
        "contract_frozen": contract.get("frozen_before_implementation") is True,
        "user_cancelled_human_step": amendment.get("user_decision") == "omit_invite_only_adult_participant_step",
        "zero_human_participants": contract.get("human_boundary", {}).get("human_participants") == 0,
        "baseline_retains_active_human_surface": baseline.get("observed", {}).get("active_enrollment_link_present") is True,
        "runtime_gate_passed": report.get("passed") is True and gate.get("passed") is True,
        "both_runtimes_passed": len(report.get("runtimes", [])) == 2
        and all(item.get("passed") is True for item in report["runtimes"]),
        "all_nine_retired_paths_passed": gate.get("retired_endpoint_count_per_runtime") == 9,
        "regression_262_or_more_passed": regression.get("passed") is True
        and regression.get("tests_passed", 0) >= 262,
        "post_promotion_regression_failure_retained": POST_PROMOTION_FAILURE.exists(),
        "attempt_1_status_evaluator_gap_retained": EVALUATOR_GAP.exists(),
        "human_validation_not_claimed": report.get("human_validation_claimed") is False,
        "external_release_closed": report.get("external_release_authority") is False,
    }
    if not all(checks.values()):
        failed = [key for key, value in checks.items() if not value]
        raise SystemExit(f"V0.295 promotion failed: {failed}")

    deployment_gate = {
        "decision": "synthetic_deployment_gate_passed",
        "passed": True,
        "checks": checks,
        "human_participants": 0,
        "retired_endpoint_count_per_runtime": 9,
        "container_uid": report["container_uid"],
        "invite_notice_in_container": report["invite_notice_in_container"],
        "synthetic_only": True,
        "human_validation_claimed": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update(
        {
            "current_version": "psm_v0.295",
            "previous_formal_version": "psm_v0.294",
            "source_evidence_version": "psm_v0.251",
            "completed_result": "synthetic_deployment_gate_passed",
            "v0_295_synthetic_deployment_gate": deployment_gate,
            "next_stage": {
                "version": "PSM_V0.296",
                "objective": "决定是否建立外部网络托管；真人招募与成年核验不再是该路线的前置步骤",
                "blocked": True,
                "requires_user_input": True,
            },
        }
    )
    target.setdefault("primary_artifacts", {}).update(
        {
            "v0_295_contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "v0_295_amendment": str(AMENDMENT.relative_to(PSM_ROOT)),
            "v0_295_baseline": str(BASELINE.relative_to(PSM_ROOT)),
            "v0_295_report": str(REPORT.relative_to(PSM_ROOT)),
            "v0_295_gate": str(GATE.relative_to(PSM_ROOT)),
            "v0_295_regression": str(REGRESSION.relative_to(PSM_ROOT)),
            "v0_295_post_promotion_failure": str(POST_PROMOTION_FAILURE.relative_to(PSM_ROOT)),
            "v0_295_evaluator_gap": str(EVALUATOR_GAP.relative_to(PSM_ROOT)),
            "v0_295_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
            "v0_295_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
            "project_status": "project_status_out/psm_v0.295_project_status.json",
        }
    )
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_295_synthetic_deployment_promotion_manifest_v1",
        "version": "PSM_V0.295",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": deployment_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "synthetic_deployment_gate": deployment_gate,
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    checkpoint = {
        "schema_version": "psm_v0_295_synthetic_deployment_checkpoint_v1",
        "current_promoted_version": "PSM_V0.295",
        "target_promoted": True,
        "status": "blocked_v0_296_external_network_hosting_decision_required",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": True,
        "next_action": "obtain_v0_296_external_network_hosting_decision",
        "required_decision": (
            "请决定是否把当前无真人验证声明的产品部署到外部网络；若授权，需要提供或批准托管平台、"
            "域名、月预算和访问范围。邀请制人数、成年核验与真人满意度测试不再要求。"
        ),
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("human_participants: 0")
    print("next_stage: PSM_V0.296 external network hosting decision")


if __name__ == "__main__":
    main()
