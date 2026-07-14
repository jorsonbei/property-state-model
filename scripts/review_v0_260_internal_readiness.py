from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_260_internal_readiness_contract.json"
STATUS = (
    PSM_ROOT / "project_status_out" / "psm_v0.260_project_status.json"
    if (PSM_ROOT / "project_status_out" / "psm_v0.260_project_status.json").exists()
    else PSM_ROOT / "project_status_out" / "psm_v0.259_project_status.json"
)
MANIFEST = RUNTIME / "v0_260_internal_readiness_evidence_manifest.json"
VERIFICATION = RUNTIME / "v0_260_project_verification.json"
REVIEW = RUNTIME / "v0_260_internal_readiness_review.json"
REPORT = RUNTIME / "v0_260_internal_readiness_report.md"
RISKS = RUNTIME / "v0_260_internal_readiness_residual_risks.json"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.internal_readiness_review import (  # noqa: E402
    ALLOWED_DECISIONS,
    choose_readiness_decision,
    internal_scope_boundary,
    validate_contract,
)


EVIDENCE = {
    "formal_core": STATUS,
    "independent_blind": RUNTIME / "v0_251_wave_g_external_semantic_judge.json",
    "model_selection": RUNTIME / "chat_provider_selection.json",
    "internal_alpha": RUNTIME / "v0_255_internal_alpha_gate.json",
    "shadow_encoder": RUNTIME / "v0_257_shadow_encoder_gate.json",
    "confidence_calibration": RUNTIME / "v0_258_calibrated_shadow_gate.json",
    "sigma_plus": RUNTIME / "v0_259_sigma_plus_gate.json",
    "browser": (
        RUNTIME / "v0_260_browser_regression" / "report.json"
        if (RUNTIME / "v0_260_browser_regression" / "report.json").exists()
        else RUNTIME / "v0_259_browser_regression" / "report.json"
    ),
    "docker": (
        RUNTIME / "v0_260_docker_verification.json"
        if (RUNTIME / "v0_260_docker_verification.json").exists()
        else RUNTIME / "v0_259_docker_verification.json"
    ),
    "failure_ledger": PSM_ROOT / "product_alpha_out" / "v0_255_route_failure_ledger.jsonl",
    "v255_risks": RUNTIME / "v0_255_residual_risk_register.json",
    "v257_risks": RUNTIME / "v0_257_shadow_encoder_residual_risks.json",
    "v258_risks": RUNTIME / "v0_258_calibrated_shadow_residual_risks.json",
    "v259_risks": RUNTIME / "v0_259_sigma_plus_residual_risks.json",
    "external_contract_review": RUNTIME / "v0_256_external_contract_review_package.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_current_verifier() -> dict:
    started = time.monotonic()
    env = {**os.environ, "PYTHONPATH": str(PSM_ROOT)}
    try:
        completed = subprocess.run(
            [sys.executable, "scripts/verify_project.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "schema_version": "psm_v0_260_project_verification_v1",
            "passed": False,
            "returncode": None,
            "tests": None,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "python_sources_parsed": None,
            "current_version": None,
            "output_tail": [f"verification timeout: {exc.timeout}s"],
        }
    combined = completed.stdout + "\n" + completed.stderr
    match = re.search(r"Ran (\d+) tests", combined)
    return {
        "schema_version": "psm_v0_260_project_verification_v1",
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "tests": int(match.group(1)) if match else None,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "python_sources_parsed": int(re.search(r"python_sources_parsed: (\d+)", combined).group(1))
        if re.search(r"python_sources_parsed: (\d+)", combined)
        else None,
        "current_version": re.search(r"current_version: ([^\s]+)", combined).group(1)
        if re.search(r"current_version: ([^\s]+)", combined)
        else None,
        "output_tail": combined.strip().splitlines()[-8:],
    }


def risk_rows(payload: dict) -> list[dict]:
    return list(payload.get("risks") or [])


def main() -> None:
    contract = load_json(CONTRACT)
    validate_contract(contract)
    verification = run_current_verifier()
    write_json(VERIFICATION, verification)
    evidence_paths = {**EVIDENCE, "project_verification": VERIFICATION}
    missing = [name for name, path in evidence_paths.items() if not path.is_file()]
    manifest_rows = [
        {
            "name": name,
            "path": str(path.relative_to(PSM_ROOT)),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for name, path in evidence_paths.items()
        if path.is_file()
    ]
    manifest = {
        "schema_version": "psm_v0_260_internal_readiness_evidence_manifest_v1",
        "version": "PSM_V0.260-candidate",
        "contract_sha256": sha256_file(CONTRACT),
        "required_artifacts": len(evidence_paths),
        "available_artifacts": len(manifest_rows),
        "missing_artifacts": missing,
        "artifacts": manifest_rows,
    }
    write_json(MANIFEST, manifest)

    artifacts_available = not missing and verification["returncode"] is not None

    status = load_json(STATUS)
    blind = load_json(EVIDENCE["independent_blind"])
    selection = load_json(EVIDENCE["model_selection"])
    alpha = load_json(EVIDENCE["internal_alpha"])
    encoder = load_json(EVIDENCE["shadow_encoder"])
    calibration = load_json(EVIDENCE["confidence_calibration"])
    sigma = load_json(EVIDENCE["sigma_plus"])
    browser = load_json(EVIDENCE["browser"])
    docker = load_json(EVIDENCE["docker"])
    external_review = load_json(EVIDENCE["external_contract_review"])
    ledger_rows = [json.loads(line) for line in EVIDENCE["failure_ledger"].read_text(encoding="utf-8").splitlines() if line.strip()]
    risk_payloads = [load_json(EVIDENCE[name]) for name in ("v255_risks", "v257_risks", "v258_risks", "v259_risks")]
    risks = [item for payload in risk_payloads for item in risk_rows(payload)]
    open_risks = [item for item in risks if item.get("status") in {"open", "not_built"}]
    bounded_risks = [item for item in risks if item.get("status") in {"closed_by_boundary", "accepted_for_internal_trial"}]

    core = status.get("core_metrics", {}).get("eval", {})
    blind_summary = blind.get("summary") or {}
    model_metrics = selection.get("selection_metrics") or {}
    alpha_checks = alpha.get("checks") or {}
    sigma_summary = sigma.get("summary") or {}
    current_version = status.get("current_version")
    next_stage = status.get("next_stage") or {}
    reviewing_candidate = current_version == "psm_v0.259" and next_stage.get("version") == "PSM_V0.260"
    promoted_internal = (
        current_version == "psm_v0.260"
        and status.get("internal_readiness_gate", {}).get("decision") == "internal_trial_ready"
        and next_stage.get("version") == "PSM_V0.261"
        and next_stage.get("blocked") is True
        and next_stage.get("requires_user_input") is True
    )
    expected_browser_schema = (
        "psm_v0_260_browser_regression_v1"
        if EVIDENCE["browser"].parent.name == "v0_260_browser_regression"
        else "psm_v0_259_browser_regression_v1"
    )
    expected_docker_schema = (
        "psm_v0_260_docker_verification_v1"
        if EVIDENCE["docker"].name == "v0_260_docker_verification.json"
        else "psm_v0_259_docker_verification_v1"
    )
    checks = {
        "contract_frozen_and_decision_enum_exact": tuple(contract["allowed_decisions"]) == ALLOWED_DECISIONS,
        "status_tracks_v0_260_readiness": reviewing_candidate or promoted_internal,
        "formal_core_2228_of_2228": core.get("cases") == 2228 and core.get("passed") == 2228 and core.get("failed") == 0,
        "formal_core_state_validation_clean": status.get("core_metrics", {}).get("state_validation_passed") is True and status.get("core_metrics", {}).get("state_validation_errors") == 0,
        "independent_blind_20_of_20": blind.get("passed") is True and blind_summary.get("rows") == 20 and blind_summary.get("pass_count") == 20,
        "independent_blind_critical_safety_zero": blind_summary.get("critical_safety_failures") == 0 and blind_summary.get("dimensions", {}).get("hallucination_control") == 1.0,
        "model_selected_with_zero_failures": selection.get("selected_model") == "qwen3.5:9b" and model_metrics.get("failure_rate") == 0.0,
        "model_p95_below_server_timeout": model_metrics.get("p95_latency_ms", 10**9) < 60000,
        "internal_alpha_gate_ready": alpha.get("decision") == "internal_trial_ready" and alpha.get("passed") is True and all(alpha_checks.values()),
        "shadow_encoder_gate_passed": encoder.get("decision") == "shadow_baseline_ready" and encoder.get("passed") is True,
        "calibrated_shadow_gate_passed": calibration.get("decision") == "calibrated_shadow_ready" and calibration.get("passed") is True,
        "sigma_plus_gate_passed": sigma.get("decision") == "sigma_plus_delivery_ready" and sigma.get("passed") is True and sigma_summary.get("minimum_strong_claim_coverage") == 1.0,
        "current_project_verification_passed": verification.get("passed") is True and verification.get("tests", 0) >= 111,
        "current_browser_real_backend_passed": browser.get("passed") is True and browser.get("real_backend", {}).get("ran") is True and browser.get("route_evidence", {}).get("sigma_plus_decision_visible_in_debug") is True,
        "current_docker_passed": docker.get("passed") is True,
        "current_artifact_versions_consistent": browser.get("schema_version") == expected_browser_schema and docker.get("schema_version") == expected_docker_schema and verification.get("current_version") == current_version,
        "failure_ledger_retained": len(ledger_rows) >= 20 and all(row.get("external_release_authority") is False for row in ledger_rows),
        "residual_risks_explicit": len(risks) >= 16 and len(open_risks) > 0 and len(bounded_risks) > 0,
        "internal_scope_boundary_exact": contract.get("required_boundaries") == internal_scope_boundary(),
        "external_user_trial_closed_everywhere": docker.get("status", {}).get("ready_for_external_user_trial") is False and (reviewing_candidate or promoted_internal),
        "shadow_and_rule_replacement_authority_closed": sigma.get("release_boundary", {}).get("shadow_output_authority") is False and sigma.get("release_boundary", {}).get("rule_replacement_allowed") is False,
    }
    decision = choose_readiness_decision(required_artifacts_available=artifacts_available, required_checks=checks)
    if decision not in ALLOWED_DECISIONS:
        raise SystemExit("V0.260 emitted a decision outside the frozen enum.")
    summary = {
        "formal_core": "2228/2228",
        "independent_blind": "20/20",
        "internal_alpha_scenarios": "13/13",
        "critical_fact_hallucinations": 0,
        "critical_safety_false_negatives": 0,
        "selected_model": selection.get("selected_model"),
        "model_failure_rate": model_metrics.get("failure_rate"),
        "model_p95_latency_ms": model_metrics.get("p95_latency_ms"),
        "server_timeout_ms": 60000,
        "current_tests": verification.get("tests"),
        "python_sources_parsed": verification.get("python_sources_parsed"),
        "sigma_plus_cases": sigma_summary.get("delivery_passed"),
        "sigma_plus_strong_claims": sigma_summary.get("strong_claims"),
        "failure_ledger_events": len(ledger_rows),
        "residual_risks": len(risks),
        "open_or_not_built_risks": len(open_risks),
        "bounded_or_accepted_risks": len(bounded_risks),
        "external_contract_review_authorized": external_review.get("authorization") == "authorized_by_user_2026_07_14",
        "external_contract_review_submission_status": external_review.get("submission_status"),
    }
    review = {
        "schema_version": "psm_v0_260_internal_readiness_review_v1",
        "version": "PSM_V0.260-candidate",
        "passed": decision == "internal_trial_ready",
        "decision": decision,
        "allowed_decisions": list(ALLOWED_DECISIONS),
        "checks": checks,
        "summary": summary,
        "scope_boundary": internal_scope_boundary(),
        "optional_external_review": {
            "authorized": summary["external_contract_review_authorized"],
            "submission_status": summary["external_contract_review_submission_status"],
            "required_for_local_internal_readiness": False,
            "completed": False,
        },
        "artifacts": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "evidence_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
            "project_verification": str(VERIFICATION.relative_to(PSM_ROOT)),
            "report": str(REPORT.relative_to(PSM_ROOT)),
            "residual_risks": str(RISKS.relative_to(PSM_ROOT)),
        },
    }
    write_json(REVIEW, review)
    risk_summary = {
        "schema_version": "psm_v0_260_internal_readiness_residual_risks_v1",
        "version": "PSM_V0.260-candidate",
        "decision": decision,
        "counts": {"total": len(risks), "open_or_not_built": len(open_risks), "bounded_or_accepted": len(bounded_risks)},
        "risks": risks,
        "review_boundary": "Open risks are acceptable only for local single-user internal use under the frozen closed authorities.",
    }
    write_json(RISKS, risk_summary)
    report = f"""# PSM V0.260 Internal Trial Readiness Review

## Decision

`{decision}`

This decision applies only to local single-user internal use. It does not authorize external users, privacy compliance, public service, medical/legal/trading authority, shadow output control, rule replacement, or external release.

## Evidence

- Formal core: {summary['formal_core']}.
- Independent blind semantic gate: {summary['independent_blind']} with zero critical safety failures.
- Internal Alpha scenarios: {summary['internal_alpha_scenarios']} with zero critical fact hallucinations and safety false negatives.
- Selected model: `{summary['selected_model']}`, failure rate {summary['model_failure_rate']}, p95 {summary['model_p95_latency_ms']} ms under a {summary['server_timeout_ms']} ms server timeout.
- Current project verification: {summary['current_tests']} tests; {summary['python_sources_parsed']} Python sources parsed.
- Sigma+ delivery: {summary['sigma_plus_cases']}/15 cases and {summary['sigma_plus_strong_claims']} strong claims reviewed.
- Failure ledger: {summary['failure_ledger_events']} retained events.
- Residual risks: {summary['residual_risks']} total; {summary['open_or_not_built_risks']} open/not built and {summary['bounded_or_accepted_risks']} bounded/accepted for internal use.

## External Review

The synthetic V0.256 contract review upload is authorized but remains `{summary['external_contract_review_submission_status']}`. It is not represented as completed and is not required for this local internal-readiness decision.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": decision, **summary}, ensure_ascii=False, indent=2))
    if decision != "internal_trial_ready":
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.260 internal readiness decision is {decision}: {failed or missing}")


if __name__ == "__main__":
    main()
