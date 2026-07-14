from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.259_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.260_project_status.json"
GATE = RUNTIME / "v0_260_internal_readiness_review.json"
RISKS = RUNTIME / "v0_260_internal_readiness_residual_risks.json"
EVIDENCE_MANIFEST = RUNTIME / "v0_260_internal_readiness_evidence_manifest.json"
CHECKPOINT = RUNTIME / "v0_260_internal_readiness_checkpoint.json"
MANIFEST = RUNTIME / "v0_260_internal_readiness_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preferred_report(current: Path, previous: Path) -> tuple[Path, dict]:
    path = current if current.exists() else previous
    return path, read_json(path)


def validate(gate: dict, risks: dict, evidence_manifest: dict, browser: dict, docker: dict) -> None:
    if gate.get("passed") is not True or gate.get("decision") != "internal_trial_ready":
        raise SystemExit("V0.260 internal readiness review is not passing.")
    if not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.260 internal readiness review contains a failed check.")
    summary = gate.get("summary") or {}
    if summary.get("formal_core") != "2228/2228" or summary.get("independent_blind") != "20/20":
        raise SystemExit("V0.260 core or blind evidence is incomplete.")
    if summary.get("critical_fact_hallucinations") != 0 or summary.get("critical_safety_false_negatives") != 0:
        raise SystemExit("V0.260 has a critical fact or safety failure.")
    if summary.get("current_tests", 0) < 114:
        raise SystemExit("V0.260 current project verification is incomplete.")
    if summary.get("failure_ledger_events", 0) < 20:
        raise SystemExit("V0.260 failure ledger was not retained.")
    if evidence_manifest.get("missing_artifacts"):
        raise SystemExit("V0.260 evidence manifest has missing artifacts.")
    if risks.get("decision") != "internal_trial_ready":
        raise SystemExit("V0.260 residual risks disagree with the review.")
    boundary = gate.get("scope_boundary") or {}
    if boundary.get("scope") != "local_single_user_internal":
        raise SystemExit("V0.260 scope is not local single-user internal.")
    if any(boundary.get(key) is not False for key in ("external_user_trial_allowed", "privacy_compliance_claimed", "public_service_allowed", "medical_legal_trading_authority", "shadow_output_authority", "rule_replacement_allowed", "external_release_authority")):
        raise SystemExit("V0.260 opened a prohibited authority.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.260 browser regression is not passing.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.260 Docker verification is not passing.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    gate = read_json(GATE)
    risks = read_json(RISKS)
    evidence_manifest = read_json(EVIDENCE_MANIFEST)
    browser_path, browser = preferred_report(
        RUNTIME / "v0_260_browser_regression" / "report.json",
        RUNTIME / "v0_259_browser_regression" / "report.json",
    )
    docker_path, docker = preferred_report(
        RUNTIME / "v0_260_docker_verification.json",
        RUNTIME / "v0_259_docker_verification.json",
    )
    validate(gate, risks, evidence_manifest, browser, docker)

    internal_readiness_gate = {
        "decision": gate["decision"],
        "passed": True,
        **gate["summary"],
        "scope": "local_single_user_internal",
        "evidence_manifest_artifacts": evidence_manifest.get("available_artifacts"),
        "browser_report": str(browser_path.relative_to(PSM_ROOT)),
        "docker_report": str(docker_path.relative_to(PSM_ROOT)),
    }
    checkpoint = {
        "schema_version": "psm_v0_260_internal_readiness_checkpoint_v1",
        "current_promoted_version": "PSM_V0.260",
        "target_version": "PSM_V0.260",
        "target_promoted": True,
        "status": "blocked_on_v0_261_external_scope_and_credentials",
        "requires_user_input": True,
        "internal_readiness_gate": internal_readiness_gate,
        "completed_engineering": [
            "frozen three-decision internal-readiness contract with exact local single-user scope boundaries",
            "SHA-256 evidence manifest spanning core, blind, model, alpha, shadow, calibration, Sigma+, browser, Docker, failure, and risk evidence",
            f"current project verifier passed {gate['summary']['current_tests']} tests and parsed {gate['summary']['python_sources_parsed']} Python sources",
            "formal core 2228/2228, independent blind 20/20, and internal Alpha 13/13 retained",
            "zero critical fact hallucinations and critical safety false negatives",
            "model failure rate 0.0 and p95 latency 22949 ms below the 60000 ms server timeout",
            f"{gate['summary']['residual_risks']} residual risks retained with {gate['summary']['open_or_not_built_risks']} open/not-built and {gate['summary']['bounded_or_accepted_risks']} bounded/accepted for internal use",
            "V0.256 synthetic external contract review authorization retained as not submitted without API credentials",
        ],
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_user_trial_allowed": False,
            "candidate_shadow_only": True,
            "deterministic_rule_controller_retained": True,
            "internal_trial_ready": True,
            "privacy_compliance_claimed": False,
            "public_service_allowed": False,
            "medical_legal_trading_authority": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_260_promoted": True,
        },
        "required_decision": (
            "需要用户介入后才能进入 PSM V0.261。请决定是否启动外部用户试用准备，以及外部范围、数据处理/隐私要求、"
            "部署方式与预算；如要先完成已授权的 V0.256 合成契约外部 judge，还需要提供可用的外部模型 API 凭证。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.260"
    target["previous_formal_version"] = "psm_v0.259"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "local_single_user_internal_trial_ready"
    target["internal_readiness_gate"] = internal_readiness_gate
    target["next_stage"] = {
        "version": "PSM_V0.261",
        "objective": (
            "Define and authorize the post-internal external-validation lane, including external-user scope, privacy and data handling, "
            "deployment, budget, and API credentials for the already-authorized synthetic contract judge; do not begin external use "
            "or data upload until these user-owned decisions are supplied."
        ),
        "blocked": True,
        "requires_user_input": True,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "internal_readiness_review": "runtime/v0_260_internal_readiness_review.json",
            "internal_readiness_report": "runtime/v0_260_internal_readiness_report.md",
            "internal_readiness_evidence_manifest": "runtime/v0_260_internal_readiness_evidence_manifest.json",
            "internal_readiness_project_verification": "runtime/v0_260_project_verification.json",
            "internal_readiness_residual_risks": "runtime/v0_260_internal_readiness_residual_risks.json",
            "internal_readiness_checkpoint": "runtime/v0_260_internal_readiness_checkpoint.json",
            "project_status": "project_status_out/psm_v0.260_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_260_internal_readiness_promotion_manifest_v1",
        "version": "PSM_V0.260",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "internal_readiness_gate": internal_readiness_gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
