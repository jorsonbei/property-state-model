from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.261_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.262_project_status.json"
PROTOCOL = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"
LOCAL_GATE = RUNTIME / "v0_262_external_trial_protocol_gate.json"
BUDGET = RUNTIME / "v0_262_api_budget_ledger.json"
INITIAL_REVIEW = RUNTIME / "v0_262_openai_external_trial_protocol_judge_attempt_1_failed.json"
FINAL_REVIEW = RUNTIME / "v0_262_openai_external_trial_protocol_judge.json"
BROWSER = RUNTIME / "v0_262_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_262_docker_verification.json"
CHECKPOINT = RUNTIME / "v0_262_external_trial_protocol_checkpoint.json"
MANIFEST = RUNTIME / "v0_262_external_trial_protocol_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_core(protocol: dict, local: dict, budget: dict, initial: dict, final: dict) -> None:
    if protocol.get("authorization", {}).get("approved_plan") != "v0_262_conservative_invite_only":
        raise SystemExit("V0.262 conservative protocol authorization is missing.")
    if local.get("passed") is not True or not all((local.get("checks") or {}).values()):
        raise SystemExit("V0.262 local protocol gate is not passing.")
    if local.get("protocol_sha256") != canonical_sha256(protocol):
        raise SystemExit("V0.262 local gate covers a different protocol.")
    if initial.get("passed") is not False or initial.get("review", {}).get("verdict") != "fail":
        raise SystemExit("V0.262 initial external failure is not retained.")
    if final.get("passed") is not True or final.get("review", {}).get("verdict") != "pass":
        raise SystemExit("V0.262 final external protocol review is not passing.")
    if final.get("protocol_sha256") != canonical_sha256(protocol) or not all((final.get("gate_checks") or {}).values()):
        raise SystemExit("V0.262 final external review does not cover the frozen protocol.")
    if len(final.get("review", {}).get("question_reviews") or []) != 7:
        raise SystemExit("V0.262 final external review lacks seven-question coverage.")
    if final.get("review", {}).get("failed_checks") or final.get("review", {}).get("critical_findings") or final.get("review", {}).get("recommended_repairs"):
        raise SystemExit("V0.262 final external review retains unresolved findings.")
    if final.get("submission_scope", {}).get("contains_participant_content") is not False:
        raise SystemExit("V0.262 external review contains participant content.")
    if final.get("api_key_persisted_in_artifact") is not False:
        raise SystemExit("V0.262 external review persisted a secret.")
    if Decimal(str(budget.get("reserved_usd"))) > Decimal(str(budget.get("limit_usd"))):
        raise SystemExit("V0.262 API reservations exceed the approved budget.")
    if budget.get("participant_content_calls") != 0:
        raise SystemExit("V0.262 budget ledger contains a participant-content call.")
    boundary = protocol.get("release_boundary") or {}
    prohibited = (
        "participant_enrollment_completed", "public_service_allowed", "privacy_compliance_claimed",
        "production_readiness_claimed", "medical_legal_trading_authority",
        "training_on_trial_data_allowed", "rule_replacement_allowed", "external_release_authority",
    )
    if any(boundary.get(name) is not False for name in prohibited):
        raise SystemExit("V0.262 protocol opens a prohibited authority.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    protocol = read_json(PROTOCOL)
    local = read_json(LOCAL_GATE)
    budget = read_json(BUDGET)
    initial = read_json(INITIAL_REVIEW)
    final = read_json(FINAL_REVIEW)
    validate_core(protocol, local, budget, initial, final)
    browser = read_json(BROWSER) if BROWSER.exists() else None
    docker = read_json(DOCKER) if DOCKER.exists() else None
    integration_ready = bool(
        browser and browser.get("passed") is True and browser.get("real_backend", {}).get("ran") is True
        and docker and docker.get("passed") is True
    )
    protocol_gate = {
        "decision": "invite_only_trial_protocol_ready",
        "passed": True,
        "approved_plan": protocol["authorization"]["approved_plan"],
        "participant_minimum": protocol["trial_scope"]["participant_minimum"],
        "participant_maximum": protocol["trial_scope"]["participant_maximum"],
        "local_checks_passed": sum(local["checks"].values()),
        "synthetic_attacks_rejected": local["metrics"]["attack_prompts_rejected"],
        "initial_external_verdict": initial["review"]["verdict"],
        "initial_external_failed_checks": len(initial["review"]["failed_checks"]),
        "final_external_verdict": final["review"]["verdict"],
        "final_external_question_passes": sum(item["verdict"] == "pass" for item in final["review"]["question_reviews"]),
        "final_external_findings": len(final["review"]["failed_checks"]) + len(final["review"]["critical_findings"]),
        "metadata_retention_days": protocol["retention"]["operational_metadata_days"],
        "monthly_api_budget_usd": protocol["api_budget"]["calendar_month_limit"],
        "api_budget_reserved_usd": float(budget["reserved_usd"]),
        "participant_content_external_calls": budget["participant_content_calls"],
        "protocol_sha256": canonical_sha256(protocol),
    }
    checkpoint = {
        "schema_version": "psm_v0_262_external_trial_protocol_checkpoint_v1",
        "current_promoted_version": "PSM_V0.262" if integration_ready else "PSM_V0.261",
        "target_version": "PSM_V0.262",
        "target_promoted": integration_ready,
        "status": "blocked_on_v0_263_real_participant_enrollment" if integration_ready else "staged_for_browser_and_docker_verification",
        "requires_user_input": True,
        "external_trial_protocol_gate": protocol_gate,
        "completed_engineering": [
            "user-approved conservative protocol for three to five invited adults under operator supervision",
            "operator-verified adulthood and one-to-one secret-HMAC invitee-to-pseudonym binding",
            "strict notice-display, acknowledgment, consent, and session-enablement timestamp sequence",
            "raw participant prompts retained zero days and never sent to external APIs",
            "content-free salted-HMAC audit events with seven-day metadata expiry and withdrawal deletion",
            "20 USD calendar-month API reservation gate with participant-content calls prohibited",
            "sensitive, secret, medical, legal, trading, private-document, and minor prompts rejected",
            "Docker host publishing bound to 127.0.0.1 instead of all interfaces",
            "initial external fail retained and final independent review passed seven of seven questions",
        ],
        "integration_evidence": {
            "browser": str(BROWSER.relative_to(PSM_ROOT)) if browser else None,
            "docker": str(DOCKER.relative_to(PSM_ROOT)) if docker else None,
            "passed": integration_ready,
        },
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "invite_only_trial_protocol_ready": True,
            "real_participant_enrollment_completed": False,
            "external_user_trial_active": False,
            "public_service_allowed": False,
            "privacy_compliance_claimed": False,
            "production_readiness_claimed": False,
            "training_on_trial_data_allowed": False,
            "medical_legal_trading_authority": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_262_promoted": integration_ready,
        },
        "required_decision": (
            "PSM V0.263 需要真实参与者介入：请安排 3 至 5 名受邀成年人进行现场监督试用。不要在聊天或 GitHub 中提交其姓名、"
            "联系方式或证件；系统将在本机生成化名邀请，并由操作员线下核验成年、展示告知、收集明确同意后才启用会话。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.262"
    target["previous_formal_version"] = "psm_v0.261"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "invite_only_external_trial_protocol_ready_participants_not_enrolled"
    target["external_trial_protocol_gate"] = protocol_gate
    target["next_stage"] = {
        "version": "PSM_V0.263",
        "objective": (
            "Enroll three to five real invited adults without collecting direct identity in project artifacts: create local pseudonymous "
            "invitations, complete operator adulthood verification, display the frozen notice, record explicit consent, and enable only "
            "supervised sessions. Do not activate the trial until every participant passes the enrollment gate."
        ),
        "blocked": True,
        "requires_user_input": True,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "v0_262_protocol": "benchmarks/v0_262_invite_only_external_trial_protocol.json",
            "v0_262_trial_notice": "V0_262_INVITE_ONLY_TRIAL_NOTICE.md",
            "v0_262_local_gate": "runtime/v0_262_external_trial_protocol_gate.json",
            "v0_262_attack_matrix": "runtime/v0_262_external_trial_attack_matrix.json",
            "v0_262_budget_ledger": "runtime/v0_262_api_budget_ledger.json",
            "v0_262_initial_external_review": "runtime/v0_262_openai_external_trial_protocol_judge_attempt_1_failed.json",
            "v0_262_final_external_review": "runtime/v0_262_openai_external_trial_protocol_judge.json",
            "v0_262_checkpoint": "runtime/v0_262_external_trial_protocol_checkpoint.json",
            "project_status": "project_status_out/psm_v0.262_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)
    if integration_ready:
        manifest = {
            "schema_version": "psm_v0_262_external_trial_protocol_promotion_manifest_v1",
            "version": "PSM_V0.262",
            "promoted_at": "2026-07-15",
            "promoted": True,
            "decision": protocol_gate["decision"],
            "formal_core_source": "PSM_V0.251",
            "formal_core_records": source["core_metrics"]["eval"]["cases"],
            "external_trial_protocol_gate": protocol_gate,
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
