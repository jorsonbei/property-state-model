from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.258_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.259_project_status.json"
GATE = RUNTIME / "v0_259_sigma_plus_gate.json"
METRICS = RUNTIME / "v0_259_sigma_plus_metrics.json"
RISKS = RUNTIME / "v0_259_sigma_plus_residual_risks.json"
CHECKPOINT = RUNTIME / "v0_259_sigma_plus_checkpoint.json"
MANIFEST = RUNTIME / "v0_259_sigma_plus_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preferred_report(current: Path, previous: Path) -> tuple[Path, dict]:
    path = current if current.exists() else previous
    return path, read_json(path)


def validate(gate: dict, metrics: dict, risks: dict, browser: dict, docker: dict) -> None:
    if gate.get("passed") is not True or gate.get("decision") != "sigma_plus_delivery_ready":
        raise SystemExit("V0.259 Sigma+ gate is not passing.")
    if not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.259 Sigma+ gate contains a failed check.")
    summary = gate.get("summary") or {}
    if summary.get("delivery_passed") != 15:
        raise SystemExit("V0.259 did not pass every frozen delivery case.")
    if summary.get("minimum_strong_claim_coverage") != 1.0:
        raise SystemExit("V0.259 strong claim coverage is incomplete.")
    if summary.get("ordinary_internal_debug_leaks") != 0:
        raise SystemExit("V0.259 leaked internal debug terms into ordinary chat.")
    if summary.get("candidate_controlled_outputs") != 0:
        raise SystemExit("V0.259 let the shadow candidate control output.")
    if summary.get("deterministic_controller_rows") != 15:
        raise SystemExit("V0.259 did not retain deterministic control on every case.")
    if summary.get("external_release_authority_rows") != 0:
        raise SystemExit("V0.259 opened external release authority.")
    boundary = metrics.get("boundary") or {}
    if boundary.get("base_model_weights_changed") is not False or boundary.get("shadow_training_feedback_written") is not False:
        raise SystemExit("V0.259 changed the shadow model or wrote training feedback.")
    if risks.get("decision") != "sigma_plus_delivery_ready":
        raise SystemExit("V0.259 residual risks disagree with the gate.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.259 browser regression is not passing.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.259 Docker verification is not passing.")
    boundaries = gate.get("release_boundary") or {}
    if boundaries.get("shadow_output_authority") is not False:
        raise SystemExit("V0.259 shadow authority is not closed.")
    if boundaries.get("deterministic_rule_controller_retained") is not True:
        raise SystemExit("V0.259 deterministic controller was not retained.")
    if boundaries.get("rule_replacement_allowed") is not False:
        raise SystemExit("V0.259 opened rule replacement.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    gate = read_json(GATE)
    metrics = read_json(METRICS)
    risks = read_json(RISKS)
    browser_path, browser = preferred_report(
        RUNTIME / "v0_259_browser_regression" / "report.json",
        RUNTIME / "v0_258_browser_regression" / "report.json",
    )
    docker_path, docker = preferred_report(
        RUNTIME / "v0_259_docker_verification.json",
        RUNTIME / "v0_258_docker_verification.json",
    )
    validate(gate, metrics, risks, browser, docker)

    sigma_plus_gate = {
        "decision": gate["decision"],
        "passed": True,
        **gate["summary"],
        "delivery_contract": "natural_answer_plus_developer_trace",
        "statement_policy": "strong_claim_requires_provenance_or_explicit_downgrade",
        "candidate_shadow_only": True,
        "deterministic_rule_controller_retained": True,
        "rule_replacement_allowed": False,
        "browser_report": str(browser_path.relative_to(PSM_ROOT)),
        "docker_report": str(docker_path.relative_to(PSM_ROOT)),
    }
    checkpoint = {
        "schema_version": "psm_v0_259_sigma_plus_checkpoint_v1",
        "current_promoted_version": "PSM_V0.259",
        "target_version": "PSM_V0.259",
        "target_promoted": True,
        "status": "promoted_v0_260_internal_readiness_review_in_progress",
        "requires_user_input": False,
        "sigma_plus_gate": sigma_plus_gate,
        "completed_engineering": [
            "Sigma+ API contract separating natural user answers from developer state, provenance, tools, failures, and statement audit",
            "rule-based strong-claim audit requiring provenance or an explicit downgrade in the visible answer",
            "fail-closed repair before user delivery for unsupported strong claims or ordinary-chat debug leakage",
            "V0.258 calibrated shadow observation integrated into developer evidence with zero output authority",
            "15 frozen synthetic non-private delivery cases with 22 strong claims and 1.0 minimum coverage",
            "six provenance cases, two retained failure events, 25 retained unresolved judges, and 19 shadow fallback target events",
            "zero ordinary debug leaks, candidate-controlled outputs, or external release authority rows",
        ],
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_user_trial_allowed": False,
            "candidate_shadow_only": True,
            "deterministic_rule_controller_retained": True,
            "shadow_training_feedback_written": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_259_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.260 内部试用就绪评审：汇总安全、聊天质量、盲测、模型对照、性能、"
            "失败账本与剩余风险，只允许 internal_trial_ready、needs_more_work 或 blocked 三种结论；外部用户试用不自动开放。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.259"
    target["previous_formal_version"] = "psm_v0.258"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "traceable_sigma_plus_candidate_delivery"
    target["sigma_plus_gate"] = sigma_plus_gate
    target["next_stage"] = {
        "version": "PSM_V0.260",
        "objective": (
            "Run the internal trial readiness review by consolidating safety, chat quality, blind-set, model comparison, performance, "
            "failure-ledger, and residual-risk evidence; issue only internal_trial_ready, needs_more_work, or blocked; keep external "
            "user trial, privacy compliance, public service, and professional authority closed."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "sigma_plus_gate": "runtime/v0_259_sigma_plus_gate.json",
            "sigma_plus_metrics": "runtime/v0_259_sigma_plus_metrics.json",
            "sigma_plus_evaluation": "runtime/v0_259_sigma_plus_evaluation.jsonl",
            "sigma_plus_residual_risks": "runtime/v0_259_sigma_plus_residual_risks.json",
            "sigma_plus_checkpoint": "runtime/v0_259_sigma_plus_checkpoint.json",
            "project_status": "project_status_out/psm_v0.259_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_259_sigma_plus_promotion_manifest_v1",
        "version": "PSM_V0.259",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "sigma_plus_gate": sigma_plus_gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
