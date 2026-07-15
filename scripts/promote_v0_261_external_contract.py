from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.260_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.261_project_status.json"
INITIAL_REVIEW = RUNTIME / "v0_261_openai_external_contract_judge_attempt_1_failed.json"
INTERMEDIATE_REVIEW = RUNTIME / "v0_261_openai_external_contract_judge_attempt_2_passed_pre_leaf_hardening.json"
REPAIR_GATE = RUNTIME / "v0_261_annotation_contract_repair_gate.json"
PACKAGE = RUNTIME / "v0_261_external_contract_review_package.json"
FINAL_REVIEW = RUNTIME / "v0_261_openai_external_contract_judge.json"
CHECKPOINT = RUNTIME / "v0_261_external_contract_checkpoint.json"
MANIFEST = RUNTIME / "v0_261_external_contract_promotion_manifest.json"
BROWSER = RUNTIME / "v0_261_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_261_docker_verification.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_core(initial: dict, intermediate: dict, gate: dict, package: dict, final: dict) -> None:
    if initial.get("passed") is not False or initial.get("review", {}).get("verdict") != "fail":
        raise SystemExit("V0.261 initial failed review was not retained.")
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.261 local contract repair gate is not passing.")
    if intermediate.get("passed") is not True or intermediate.get("review", {}).get("verdict") != "pass":
        raise SystemExit("V0.261 intermediate external pass was not retained.")
    if package.get("privacy") != {
        "contains_private_data": False,
        "contains_user_documents": False,
        "contains_secrets": False,
        "synthetic_only": True,
    }:
        raise SystemExit("V0.261 external package privacy scope changed.")
    if canonical_sha256(package.get("contract")) != package.get("contract_sha256"):
        raise SystemExit("V0.261 repaired contract hash does not match its package.")
    if final.get("passed") is not True or final.get("review", {}).get("verdict") != "pass":
        raise SystemExit("V0.261 final external review is not passing.")
    if final.get("contract_sha256") != package.get("contract_sha256"):
        raise SystemExit("V0.261 final external review covers the wrong contract.")
    if not all((final.get("gate_checks") or {}).values()):
        raise SystemExit("V0.261 final external review contains a failed gate check.")
    if len(final.get("review", {}).get("question_reviews") or []) != 5:
        raise SystemExit("V0.261 final external review lacks exact question coverage.")
    if final.get("review", {}).get("failed_checks") or final.get("review", {}).get("critical_findings"):
        raise SystemExit("V0.261 final external review retains failures.")
    if final.get("api_key_persisted_in_artifact") is not False:
        raise SystemExit("V0.261 external review did not retain the no-secret boundary.")
    boundaries = final.get("release_boundary") or {}
    if any(boundaries.get(name) is not False for name in ("training_authority", "rule_replacement_authority", "external_user_trial_allowed", "public_service_allowed", "external_release_authority")):
        raise SystemExit("V0.261 external review opened a prohibited authority.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    initial = read_json(INITIAL_REVIEW)
    intermediate = read_json(INTERMEDIATE_REVIEW)
    repair_gate = read_json(REPAIR_GATE)
    package = read_json(PACKAGE)
    final = read_json(FINAL_REVIEW)
    validate_core(initial, intermediate, repair_gate, package, final)

    browser = read_json(BROWSER) if BROWSER.exists() else None
    docker = read_json(DOCKER) if DOCKER.exists() else None
    integration_ready = bool(browser and browser.get("passed") is True and browser.get("real_backend", {}).get("ran") is True and docker and docker.get("passed") is True)
    review_gate = {
        "decision": "external_contract_review_passed",
        "passed": True,
        "provider": final["provider"],
        "model": final["actual_model"],
        "initial_external_verdict": initial["review"]["verdict"],
        "initial_failed_checks": len(initial["review"]["failed_checks"]),
        "intermediate_external_verdict": intermediate["review"]["verdict"],
        "post_pass_leaf_type_hardening": True,
        "local_repair_gate": repair_gate["decision"],
        "mutation_checks_passed": sum(repair_gate["mutation_checks"].values()),
        "final_external_verdict": final["review"]["verdict"],
        "final_question_passes": sum(item["verdict"] == "pass" for item in final["review"]["question_reviews"]),
        "final_failed_checks": len(final["review"]["failed_checks"]),
        "final_critical_findings": len(final["review"]["critical_findings"]),
        "contract_sha256": final["contract_sha256"],
        "synthetic_only": True,
        "private_data_submitted": False,
        "secret_persisted": False,
    }
    checkpoint = {
        "schema_version": "psm_v0_261_external_contract_checkpoint_v1",
        "current_promoted_version": "PSM_V0.261" if integration_ready else "PSM_V0.260",
        "target_version": "PSM_V0.261",
        "target_promoted": integration_ready,
        "status": "blocked_on_v0_262_external_user_trial_scope" if integration_ready else "staged_for_browser_and_docker_verification",
        "requires_user_input": True,
        "external_contract_review_gate": review_gate,
        "completed_engineering": [
            "OpenAI Responses API external judge with strict structured output, Keychain retrieval, and no secret persistence",
            "initial external fail retained with five failed checks and three critical findings",
            "closed-world V2 annotation contract with exact candidate projection and object-level unknown-field rejection",
            "leaf-type enforcement preventing nested side channels inside otherwise allowed fields",
            "mutually exclusive train, validation, and test time windows with source-group crossing rejection",
            "append-only per-annotator provenance and unanimous train-only label derivation",
            "explicit validation, test, blind, judge-only, evaluation, rule, controller, and authority no-backflow policy",
            "repaired local gate passed with zero candidate leaks and zero protected backflow",
            "final independent OpenAI rejudge passed five of five questions with no failures or repairs",
        ],
        "integration_evidence": {
            "browser": str(BROWSER.relative_to(PSM_ROOT)) if browser else None,
            "docker": str(DOCKER.relative_to(PSM_ROOT)) if docker else None,
            "passed": integration_ready,
        },
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_contract_review_passed": True,
            "training_started": False,
            "external_user_trial_allowed": False,
            "privacy_compliance_claimed": False,
            "public_service_allowed": False,
            "medical_legal_trading_authority": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_261_promoted": integration_ready,
        },
        "required_decision": (
            "PSM V0.262 确实需要用户介入：请决定是否启动外部用户试用准备，并确定参与者范围、允许提交的数据类型、"
            "数据处理/隐私要求、隐私告知与同意、保存/删除期限、部署方式与预算。API 已配置且合成契约评审已完成，"
            "不再是阻碍；在上述用户决策完成前，外部用户与公开服务保持关闭。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.261"
    target["previous_formal_version"] = "psm_v0.260"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "external_contract_review_passed_after_closed_world_repair"
    target["external_contract_review_gate"] = review_gate
    target["next_stage"] = {
        "version": "PSM_V0.262",
        "objective": (
            "Define and authorize an external-user trial protocol: participant scope, allowed data classes, privacy notice and consent, "
            "retention/deletion, deployment mode, budget, incident handling, and explicit stop conditions. Keep external access closed "
            "until the user-owned protocol is approved."
        ),
        "blocked": True,
        "requires_user_input": True,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "v0_261_initial_external_review": "runtime/v0_261_openai_external_contract_judge_attempt_1_failed.json",
            "v0_261_repaired_contract": "benchmarks/v0_261_state_annotation_contract_v2.json",
            "v0_261_intermediate_external_review": "runtime/v0_261_openai_external_contract_judge_attempt_2_passed_pre_leaf_hardening.json",
            "v0_261_repair_gate": "runtime/v0_261_annotation_contract_repair_gate.json",
            "v0_261_external_review_package": "runtime/v0_261_external_contract_review_package.json",
            "v0_261_final_external_review": "runtime/v0_261_openai_external_contract_judge.json",
            "v0_261_checkpoint": "runtime/v0_261_external_contract_checkpoint.json",
            "project_status": "project_status_out/psm_v0.261_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    if integration_ready:
        manifest = {
            "schema_version": "psm_v0_261_external_contract_promotion_manifest_v1",
            "version": "PSM_V0.261",
            "promoted_at": "2026-07-15",
            "promoted": True,
            "decision": review_gate["decision"],
            "formal_core_source": "PSM_V0.251",
            "formal_core_records": source["core_metrics"]["eval"]["cases"],
            "external_contract_review_gate": review_gate,
            "integration_evidence": checkpoint["integration_evidence"],
            "boundaries": checkpoint["release_boundary"],
            "next_stage": target["next_stage"],
        }
        write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"integration_ready: {integration_ready}")


if __name__ == "__main__":
    main()
