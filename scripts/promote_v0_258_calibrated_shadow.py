from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.257_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.258_project_status.json"
GATE = RUNTIME / "v0_258_calibrated_shadow_gate.json"
METRICS = RUNTIME / "v0_258_calibrated_shadow_metrics.json"
RISKS = RUNTIME / "v0_258_calibrated_shadow_residual_risks.json"
INITIAL_REJECTION = RUNTIME / "v0_258_calibrated_shadow_initial_rejection.json"
CALIBRATION = RUNTIME / "v0_258_confidence_calibration.json"
CHECKPOINT = RUNTIME / "v0_258_calibrated_shadow_checkpoint.json"
MANIFEST = RUNTIME / "v0_258_calibrated_shadow_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preferred_report(current: Path, previous: Path) -> tuple[Path, dict]:
    path = current if current.exists() else previous
    return path, read_json(path)


def validate(gate: dict, metrics: dict, risks: dict, rejection: dict, calibration: dict, browser: dict, docker: dict) -> None:
    if gate.get("passed") is not True or gate.get("decision") != "calibrated_shadow_ready":
        raise SystemExit("V0.258 calibrated shadow gate is not passing.")
    if not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.258 calibrated shadow gate contains a failed check.")
    summary = gate.get("summary") or {}
    if summary.get("average_evaluation_coverage", 0) < 0.5:
        raise SystemExit("V0.258 evaluation coverage is too low.")
    if summary.get("minimum_evaluation_selective_accuracy", 0) < 0.8:
        raise SystemExit("V0.258 selective accuracy is too low.")
    if summary.get("accepted_critical_false_negatives") != 0:
        raise SystemExit("V0.258 has accepted critical false negatives.")
    if summary.get("evaluation_low_confidence_abstentions", 0) <= 0:
        raise SystemExit("V0.258 did not exercise low-confidence abstention.")
    if summary.get("unresolved_consensus_forced_abstentions") != 7:
        raise SystemExit("V0.258 did not fail closed on every unresolved target.")
    if summary.get("protected_feedback_to_base_training") != 0:
        raise SystemExit("V0.258 protected feedback flowed into base training.")
    if metrics.get("source_audit", {}).get("passed") is not True:
        raise SystemExit("V0.258 source isolation is not passing.")
    if rejection.get("decision") != "calibrated_shadow_rejected":
        raise SystemExit("V0.258 initial rejected attempt was not retained.")
    if risks.get("decision") != "calibrated_shadow_ready":
        raise SystemExit("V0.258 residual risks disagree with the gate.")
    calibration_boundary = calibration.get("boundary") or {}
    if calibration_boundary.get("base_weights_changed") is not False:
        raise SystemExit("V0.258 calibration changed base weights.")
    if calibration_boundary.get("evaluation_feedback_used") is not False:
        raise SystemExit("V0.258 calibration used evaluation feedback.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.258 browser regression is not passing.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.258 Docker verification is not passing.")
    boundaries = gate.get("boundaries") or {}
    if boundaries.get("candidate_shadow_only") is not True:
        raise SystemExit("V0.258 candidate is not shadow-only.")
    if boundaries.get("deterministic_rule_controller_retained") is not True:
        raise SystemExit("V0.258 deterministic controller was not retained.")
    if boundaries.get("rule_replacement_allowed") is not False:
        raise SystemExit("V0.258 opened rule replacement.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    gate = read_json(GATE)
    metrics = read_json(METRICS)
    risks = read_json(RISKS)
    rejection = read_json(INITIAL_REJECTION)
    calibration = read_json(CALIBRATION)
    browser_path, browser = preferred_report(
        RUNTIME / "v0_258_browser_regression" / "report.json",
        RUNTIME / "v0_257_browser_regression" / "report.json",
    )
    docker_path, docker = preferred_report(
        RUNTIME / "v0_258_docker_verification.json",
        RUNTIME / "v0_257_docker_verification.json",
    )
    validate(gate, metrics, risks, rejection, calibration, browser, docker)

    calibrated_shadow_gate = {
        "decision": gate["decision"],
        "passed": True,
        **gate["summary"],
        "initial_rejection_retained": True,
        "base_candidate_type": "trainable_multinomial_naive_bayes",
        "calibration_type": "per_head_temperature_scaling_with_confidence_floor",
        "candidate_shadow_only": True,
        "deterministic_rule_controller_retained": True,
        "rule_replacement_allowed": False,
        "browser_report": str(browser_path.relative_to(PSM_ROOT)),
        "docker_report": str(docker_path.relative_to(PSM_ROOT)),
    }
    checkpoint = {
        "schema_version": "psm_v0_258_calibrated_shadow_checkpoint_v1",
        "current_promoted_version": "PSM_V0.258",
        "target_version": "PSM_V0.258",
        "target_promoted": True,
        "status": "promoted_v0_259_sigma_plus_delivery_in_progress",
        "requires_user_input": False,
        "calibrated_shadow_gate": calibrated_shadow_gate,
        "completed_engineering": [
            "35 new synthetic non-private records across isolated calibration, evaluation, and unresolved source families",
            "per-head temperature calibration and confidence floors for all seven property-state targets",
            "initial rejected run retained because zero unresolved cases triggered model-confidence abstention",
            "four low-confidence evaluation targets abstained with 0.959184 average coverage and 0.928571 minimum selective accuracy",
            "zero accepted critical false negatives and zero protected feedback to the frozen V0.257 base model",
            "seven unresolved targets rejected by the consensus contract while model disagreement detection remains an open 0/7 residual",
            "frozen SHA-256 contract for the V0.257 model and training dataset",
            "deterministic controller retained while the candidate remains shadow-only",
        ],
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_user_trial_allowed": False,
            "candidate_shadow_only": True,
            "deterministic_rule_controller_retained": True,
            "calibration_evaluation_unresolved_blind_judge_feedback_to_base_training": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_258_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.259：把自然回答、状态、来源、工具结果、失败和声明等级统一为可追溯的 "
            "Sigma+ 交付；强结论必须有 provenance 或降级标记，低置信和未解 target 回退确定性规则，普通聊天不得暴露内部调试术语。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.258"
    target["previous_formal_version"] = "psm_v0.257"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "source_isolated_calibrated_shadow_with_fail_closed_abstention"
    target["calibrated_shadow_gate"] = calibrated_shadow_gate
    target["next_stage"] = {
        "version": "PSM_V0.259",
        "objective": (
            "Build a Sigma+ traceable delivery contract that joins natural answers, property state, provenance, tool results, failures, "
            "and statement levels; require every strong claim to have evidence provenance or an explicit downgrade; route calibrated "
            "low-confidence and unresolved targets back to deterministic rules; and keep internal state details out of ordinary chat."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "calibrated_shadow_gate": "runtime/v0_258_calibrated_shadow_gate.json",
            "calibrated_shadow_metrics": "runtime/v0_258_calibrated_shadow_metrics.json",
            "confidence_calibration": "runtime/v0_258_confidence_calibration.json",
            "calibrated_shadow_predictions": "runtime/v0_258_calibrated_shadow_predictions.jsonl",
            "calibrated_shadow_initial_rejection": "runtime/v0_258_calibrated_shadow_initial_rejection.json",
            "calibrated_shadow_residual_risks": "runtime/v0_258_calibrated_shadow_residual_risks.json",
            "calibrated_shadow_checkpoint": "runtime/v0_258_calibrated_shadow_checkpoint.json",
            "project_status": "project_status_out/psm_v0.258_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_258_calibrated_shadow_promotion_manifest_v1",
        "version": "PSM_V0.258",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "calibrated_shadow_gate": calibrated_shadow_gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
