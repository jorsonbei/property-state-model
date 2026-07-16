#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.294_project_status.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_294_content_free_telemetry_checkpoint.json"
AMENDMENT = PSM_ROOT / "runtime" / "v0_295_no_human_decision_amendment.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_295_synthetic_deployment_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_295_synthetic_deployment_baseline.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    checkpoint = read(CHECKPOINT)
    if source.get("current_version") != "psm_v0.294":
        raise SystemExit("V0.295 requires the promoted V0.294 source status.")
    if checkpoint.get("current_promoted_version") != "PSM_V0.294":
        raise SystemExit("V0.295 requires the V0.294 checkpoint.")

    amendment = {
        "schema_version": "psm_v0_295_no_human_decision_amendment_v1",
        "recorded_at": "2026-07-16",
        "source_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "user_decision": "omit_invite_only_adult_participant_step",
        "supersedes_requirement": "invite_only_up_to_five_adults",
        "human_participant_recruitment_required": False,
        "adult_verification_required": False,
        "participant_consent_workflow_required": False,
        "real_user_validation_claimed": False,
        "replacement_evidence": "synthetic_roles_and_automated_runtime_checks_only",
        "public_service_allowed": False,
        "external_release_authority": False,
    }
    contract = {
        "schema_version": "psm_v0_295_synthetic_deployment_contract_v1",
        "version": "PSM_V0.295-candidate",
        "frozen_before_implementation": True,
        "decision_amendment": str(AMENDMENT.relative_to(PSM_ROOT)),
        "human_boundary": {
            "human_participants": 0,
            "participant_recruitment_enabled": False,
            "adult_verification_enabled": False,
            "participant_consent_workflow_enabled": False,
            "real_user_satisfaction_claimed": False,
            "synthetic_role_proxies_allowed": True,
        },
        "active_product": {
            "enrollment_link_present": False,
            "trial_static_surface_served": False,
            "trial_api_served": False,
            "retired_endpoints_status": 410,
        },
        "continuous_integration": {
            "workflow": ".github/workflows/ci.yml",
            "python_versions": ["3.11", "3.12"],
            "full_project_check": True,
            "docker_build": True,
            "container_health_check": True,
            "non_root_check": True,
            "external_model_calls": False,
            "secrets_required": False,
        },
        "container": {
            "default_bind": "127.0.0.1",
            "runtime_uid": 10001,
            "health_endpoint": "/api/health",
            "invite_notice_in_image": False,
        },
        "release_boundary": {
            "synthetic_only": True,
            "human_validation_claimed": False,
            "public_service_allowed": False,
            "external_network_deployment_allowed": False,
            "persistent_conversation_memory_enabled": False,
            "external_release_authority": False,
        },
    }
    baseline = {
        "schema_version": "psm_v0_295_synthetic_deployment_baseline_v1",
        "source_version": "PSM_V0.294",
        "captured_before_implementation": True,
        "observed": {
            "active_enrollment_link_present": True,
            "trial_endpoints_served": True,
            "invite_notice_copied_into_container": True,
            "container_healthcheck_uses_content_free_health": False,
            "github_ci_present": False,
            "package_version": "0.274.0",
        },
        "baseline_decision": "human_trial_surface_active_synthetic_deployment_ci_absent",
    }

    source["next_stage"] = {
        "version": "PSM_V0.295",
        "objective": "退役活动真人登记入口，以纯合成角色和自动化检查完成本地与容器部署演练",
        "blocked": False,
        "requires_user_input": False,
    }
    checkpoint.update(
        {
            "status": "v0_295_synthetic_deployment_open_no_human_participants",
            "requires_user_input": False,
            "next_action": "build_v0_295_synthetic_deployment_contract",
            "required_decision": "无；用户已明确取消邀请制真人步骤。",
            "decision_amendment": str(AMENDMENT.relative_to(PSM_ROOT)),
        }
    )
    write(AMENDMENT, amendment)
    write(CONTRACT, contract)
    write(BASELINE, baseline)
    write(SOURCE, source)
    write(CHECKPOINT, checkpoint)
    print(f"amendment: {AMENDMENT.relative_to(ROOT)}")
    print(f"contract: {CONTRACT.relative_to(ROOT)}")
    print("human_participants: 0")
    print("v0_295_blocked: false")


if __name__ == "__main__":
    main()
