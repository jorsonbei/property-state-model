from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.256_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.257_project_status.json"
GATE = RUNTIME / "v0_257_shadow_encoder_gate.json"
METRICS = RUNTIME / "v0_257_shadow_encoder_metrics.json"
RISKS = RUNTIME / "v0_257_shadow_encoder_residual_risks.json"
INITIAL_REJECTION = RUNTIME / "v0_257_shadow_encoder_initial_rejection.json"
CHECKPOINT = RUNTIME / "v0_257_shadow_encoder_checkpoint.json"
MANIFEST = RUNTIME / "v0_257_shadow_encoder_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preferred_report(v257: Path, v256: Path) -> tuple[Path, dict]:
    path = v257 if v257.exists() else v256
    return path, read_json(path)


def validate(gate: dict, metrics: dict, risks: dict, rejection: dict, browser: dict, docker: dict) -> None:
    if gate.get("passed") is not True or gate.get("decision") != "shadow_baseline_ready":
        raise SystemExit("V0.257 shadow encoder gate is not passing.")
    if not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.257 shadow encoder gate contains a failed check.")
    summary = gate.get("summary") or {}
    if summary.get("candidate_validation_exact_match", 0) <= summary.get("majority_validation_exact_match", 0):
        raise SystemExit("V0.257 candidate does not beat majority on validation.")
    if summary.get("candidate_test_exact_match", 0) <= summary.get("majority_test_exact_match", 0):
        raise SystemExit("V0.257 candidate does not beat majority on test.")
    if summary.get("candidate_validation_critical_false_negatives") != 0:
        raise SystemExit("V0.257 candidate has validation critical false negatives.")
    if summary.get("candidate_test_critical_false_negatives") != 0:
        raise SystemExit("V0.257 candidate has test critical false negatives.")
    if summary.get("protected_backflow") != 0:
        raise SystemExit("V0.257 protected rows flowed into training.")
    if metrics.get("dataset", {}).get("isolation", {}).get("passed") is not True:
        raise SystemExit("V0.257 source isolation is not passing.")
    if rejection.get("decision") != "shadow_baseline_rejected":
        raise SystemExit("V0.257 initial rejected attempt was not retained.")
    if rejection.get("repair_boundary", {}).get("validation_or_test_rows_added_to_training") is not False:
        raise SystemExit("V0.257 repair used protected feedback as training data.")
    if risks.get("decision") != "shadow_baseline_ready":
        raise SystemExit("V0.257 residual risks disagree with the gate.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.257 browser regression is not passing.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.257 Docker verification is not passing.")
    boundaries = gate.get("boundaries") or {}
    if boundaries.get("candidate_shadow_only") is not True:
        raise SystemExit("V0.257 candidate is not shadow-only.")
    if boundaries.get("deterministic_rule_controller_retained") is not True:
        raise SystemExit("V0.257 deterministic controller was not retained.")
    if boundaries.get("rule_replacement_allowed") is not False:
        raise SystemExit("V0.257 opened rule replacement.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    gate = read_json(GATE)
    metrics = read_json(METRICS)
    risks = read_json(RISKS)
    rejection = read_json(INITIAL_REJECTION)
    browser_path, browser = preferred_report(
        RUNTIME / "v0_257_browser_regression" / "report.json",
        RUNTIME / "v0_256_browser_regression" / "report.json",
    )
    docker_path, docker = preferred_report(
        RUNTIME / "v0_257_docker_verification.json",
        RUNTIME / "v0_256_docker_verification.json",
    )
    validate(gate, metrics, risks, rejection, browser, docker)

    shadow_gate = {
        "decision": gate["decision"],
        "passed": True,
        **gate["summary"],
        "initial_rejection_retained": True,
        "candidate_type": "trainable_multinomial_naive_bayes",
        "candidate_shadow_only": True,
        "deterministic_rule_controller_retained": True,
        "rule_replacement_allowed": False,
        "browser_report": str(browser_path.relative_to(PSM_ROOT)),
        "docker_report": str(docker_path.relative_to(PSM_ROOT)),
    }
    checkpoint = {
        "schema_version": "psm_v0_257_shadow_encoder_checkpoint_v1",
        "current_promoted_version": "PSM_V0.257",
        "target_version": "PSM_V0.257",
        "target_promoted": True,
        "status": "promoted_v0_258_calibrated_shadow_admission_in_progress",
        "requires_user_input": False,
        "shadow_encoder_gate": shadow_gate,
        "completed_engineering": [
            "42-record source-isolated synthetic encoder benchmark with 14 train, 14 validation, and 14 test rows",
            "seven trainable target heads for Q, Omega, phi, Delta sigma, Pi, eta, and B_sigma projections",
            "request and evidence-status feature policy excluding source identity, time, split, labels, consensus, and judges",
            "majority, transparent-rule, and trainable probabilistic baseline comparison",
            "initial rejected run retained with three critical false negatives per protected split",
            "out-of-vocabulary likelihood bug repaired without adding protected rows to training",
            "candidate validation exact 0.928571 and test exact 1.0 with zero critical false negatives",
            "deterministic controller retained while the candidate remains shadow-only",
        ],
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_user_trial_allowed": False,
            "candidate_shadow_only": True,
            "deterministic_rule_controller_retained": True,
            "validation_test_blind_judge_feedback_to_training": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_257_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.258：在来源隔离下扩展新的来源 family，加入置信度校准、abstention 和 "
            "unresolved 分歧评估；保持 family/source/time split 与 NoTargetRead，不把 validation/test/blind/judge-only 反馈用于训练，"
            "候选继续 shadow-only，规则控制器不替换。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.257"
    target["previous_formal_version"] = "psm_v0.256"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "source_isolated_trainable_shadow_encoder_baseline"
    target["shadow_encoder_gate"] = shadow_gate
    target["next_stage"] = {
        "version": "PSM_V0.258",
        "objective": (
            "Expand the shadow encoder to new source families and add confidence calibration, abstention, and unresolved-"
            "disagreement evaluation; keep family/source/time isolation and NoTargetRead; prohibit validation, test, blind, "
            "or judge-only feedback from training; and retain the deterministic controller without rule replacement."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "shadow_encoder_gate": "runtime/v0_257_shadow_encoder_gate.json",
            "shadow_encoder_metrics": "runtime/v0_257_shadow_encoder_metrics.json",
            "shadow_encoder_model": "runtime/v0_257_shadow_encoder_model.json",
            "shadow_encoder_predictions": "runtime/v0_257_shadow_encoder_predictions.jsonl",
            "shadow_encoder_initial_rejection": "runtime/v0_257_shadow_encoder_initial_rejection.json",
            "shadow_encoder_residual_risks": "runtime/v0_257_shadow_encoder_residual_risks.json",
            "shadow_encoder_checkpoint": "runtime/v0_257_shadow_encoder_checkpoint.json",
            "project_status": "project_status_out/psm_v0.257_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_257_shadow_encoder_promotion_manifest_v1",
        "version": "PSM_V0.257",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "shadow_encoder_gate": shadow_gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
