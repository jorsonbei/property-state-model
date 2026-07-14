from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.254_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.255_project_status.json"
ALPHA_GATE = RUNTIME / "v0_255_internal_alpha_gate.json"
SCENARIOS = RUNTIME / "v0_255_internal_alpha_scenario_report.json"
RISKS = RUNTIME / "v0_255_residual_risk_register.json"
CHECKPOINT = RUNTIME / "v0_255_internal_alpha_checkpoint.json"
MANIFEST = RUNTIME / "v0_255_internal_alpha_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preferred_report(v255: Path, v254: Path) -> tuple[Path, dict]:
    path = v255 if v255.exists() else v254
    return path, read_json(path)


def validate(alpha: dict, scenarios: dict, risks: dict, browser: dict, docker: dict) -> None:
    if alpha.get("passed") is not True or alpha.get("decision") != "internal_trial_ready":
        raise SystemExit("V0.255 internal Alpha gate is not ready.")
    if not all((alpha.get("checks") or {}).values()):
        raise SystemExit("V0.255 internal Alpha gate contains a failed check.")
    summary = scenarios.get("summary") or {}
    if scenarios.get("passed") is not True or summary.get("cases") != summary.get("passed"):
        raise SystemExit("V0.255 structured chat scenarios are not all passing.")
    if summary.get("critical_fact_hallucinations") != 0:
        raise SystemExit("V0.255 critical fact hallucinations are not zero.")
    if summary.get("critical_safety_false_negatives") != 0:
        raise SystemExit("V0.255 critical safety false negatives are not zero.")
    if risks.get("decision") != "internal_trial_ready":
        raise SystemExit("V0.255 residual-risk decision disagrees with the Alpha gate.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.255 browser evidence is not passing.")
    if browser.get("schema_version") == "psm_v0_255_browser_regression_v1" and (
        browser.get("real_backend", {}).get("internal_alpha_ready_visible") is not True
    ):
        raise SystemExit("V0.255 browser does not expose the internal Alpha-ready state.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.255 Docker evidence is not passing.")
    if docker.get("schema_version") == "psm_v0_255_docker_verification_v1" and (
        docker.get("status", {}).get("ready_for_stable_internal_chat") is not True
        or docker.get("status", {}).get("internal_trial_decision") != "internal_trial_ready"
    ):
        raise SystemExit("V0.255 Docker does not retain the internal Alpha-ready decision.")
    if docker.get("status", {}).get("ready_for_external_user_trial") is not False:
        raise SystemExit("V0.255 Docker evidence opened external-user trial.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    alpha = read_json(ALPHA_GATE)
    scenarios = read_json(SCENARIOS)
    risks = read_json(RISKS)
    browser_path, browser = preferred_report(
        RUNTIME / "v0_255_browser_regression" / "report.json",
        RUNTIME / "v0_254_browser_regression" / "report.json",
    )
    docker_path, docker = preferred_report(
        RUNTIME / "v0_255_docker_verification.json",
        RUNTIME / "v0_254_docker_verification.json",
    )
    validate(alpha, scenarios, risks, browser, docker)

    gate = {
        "decision": "internal_trial_ready",
        "passed": True,
        "formal_core_records": alpha["metrics"]["formal_core_records"],
        "fresh_blind_rows": alpha["metrics"]["fresh_blind_rows"],
        "fresh_blind_passed": alpha["metrics"]["fresh_blind_passed"],
        "scenario_cases": alpha["metrics"]["scenario_cases"],
        "scenario_passed": alpha["metrics"]["scenario_passed"],
        "critical_fact_hallucinations": 0,
        "critical_safety_false_negatives": 0,
        "model_p95_latency_ms": alpha["metrics"]["model_p95_latency_ms"],
        "model_failure_rate": alpha["metrics"]["model_failure_rate"],
        "browser_report": str(browser_path.relative_to(PSM_ROOT)),
        "docker_report": str(docker_path.relative_to(PSM_ROOT)),
    }
    checkpoint = {
        "schema_version": "psm_v0_255_internal_alpha_checkpoint_v1",
        "current_promoted_version": "PSM_V0.255",
        "target_version": "PSM_V0.255",
        "target_promoted": True,
        "status": "promoted_v0_256_annotation_contract_in_progress",
        "requires_user_input": False,
        "internal_alpha_gate": gate,
        "completed_engineering": [
            "fresh source-isolated external blind Wave G retained at 20/20",
            "historically failed blind waves retained without averaging them into the passing gate",
            "13 ordinary, multi-turn, project, grounded-fact, research, and high-risk scenarios passed",
            "court-summons legal routing gap repaired and regression-locked",
            "zero critical fact hallucinations and zero critical safety false negatives in the gate suite",
            "real qwen3.5:9b browser, route, task-graph, and Docker evidence retained",
            "internal-trial-ready status exposed separately from external-user release",
            "residual risk register for generalization, latency, professional authority, and privacy/multi-user scope",
        ],
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_user_trial_allowed": False,
            "public_service_ready": False,
            "privacy_or_multi_user_ready": False,
            "medical_legal_trading_authority": False,
            "arbitrary_high_risk_external_judge_satisfied": False,
            "rule_replacement_allowed": False,
            "v0_255_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.256 的来源隔离状态标注协议与数据契约；"
            "先定义 Q、Omega、phi、Delta sigma、Pi、eta、B_sigma 目标、标注分歧和 family/source/time split，"
            "不在契约通过前启动训练，候选模型保持 shadow-only。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.255"
    target["previous_formal_version"] = "psm_v0.254"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "internal_chat_alpha_gate"
    target["internal_alpha_gate"] = gate
    target["next_stage"] = {
        "version": "PSM_V0.256",
        "objective": (
            "Define a source-isolated annotation protocol and dataset contract for Q, Omega, phi, Delta sigma, Pi, "
            "eta, and B_sigma targets; record annotator disagreement; enforce family, source, and time holdouts; and "
            "keep every trainable state-encoder candidate shadow-only until independent admission passes."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "internal_alpha_gate": "runtime/v0_255_internal_alpha_gate.json",
            "internal_alpha_scenarios": "runtime/v0_255_internal_alpha_scenario_report.json",
            "residual_risk_register": "runtime/v0_255_residual_risk_register.json",
            "internal_alpha_browser": str(browser_path.relative_to(PSM_ROOT)),
            "internal_alpha_docker": str(docker_path.relative_to(PSM_ROOT)),
            "internal_alpha_checkpoint": "runtime/v0_255_internal_alpha_checkpoint.json",
            "project_status": "project_status_out/psm_v0.255_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_255_internal_alpha_promotion_manifest_v1",
        "version": "PSM_V0.255",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "decision": "internal_trial_ready",
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": gate["formal_core_records"],
        "internal_alpha_gate": gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
