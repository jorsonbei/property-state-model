from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_256_state_annotation_contract.json"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.state_annotation_contract import (  # noqa: E402
    RECORD_SCHEMA,
    assign_grouped_splits,
    attach_consensus,
    audit_isolation,
    candidate_input_view,
    load_contract,
    sha256_value,
    training_export,
    validate_candidate_view,
    validate_record,
)


FIXTURE_PATH = RUNTIME / "v0_256_source_isolated_annotation_fixture.jsonl"
TRAINING_PREVIEW = RUNTIME / "v0_256_shadow_training_export_preview.json"
ISOLATION_REPORT = RUNTIME / "v0_256_source_isolation_report.json"
GATE_REPORT = RUNTIME / "v0_256_annotation_contract_gate.json"
EXTERNAL_PACKAGE = RUNTIME / "v0_256_external_contract_review_package.json"


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def state_targets(*, risk: str, status: str, objective: str, unknown: str) -> dict:
    return {
        "q_core": {
            "objective": objective,
            "protected_boundaries": ["do not invent evidence", "do not transfer authority"],
            "veto_conditions": ["required source or judge is unavailable"],
        },
        "omega": {
            "risk_level": risk,
            "time_scale": "request",
            "validation_scale": "source_or_tool_check",
            "cost_scale": "bounded_unknown",
        },
        "phi": {
            "facts": ["the fixture is synthetic and contains no private data"],
            "unknowns": [unknown],
        },
        "delta_sigma": {
            "pressures": ["answer quality and evidence isolation"],
            "missing_pressure_data": ["external outcome"],
        },
        "pi": {
            "actors": ["user", "candidate", "independent annotator"],
            "artifacts": ["request", "source", "annotation"],
            "dependencies": ["source provenance", "split boundary"],
        },
        "eta": {
            "uncertainties": [unknown],
            "tail_events": ["source failure", "authority transfer"],
        },
        "b_sigma": {
            "status": status,
            "risks": ["unverified_claim"] if status != "pass" else [],
            "required_actions": ["retain source check"] if status != "pass" else ["retain boundary"],
        },
    }


def fixture_record(
    *,
    record_id: str,
    family: str,
    source_id: str,
    created_at: str,
    request: str,
    risk: str = "medium",
    status: str = "review",
    disagree_target: str | None = None,
) -> dict:
    input_payload = {
        "request": request,
        "evidence": [{"ref": f"synthetic:{source_id}", "kind": "source_note", "status": "available"}],
    }
    first = state_targets(
        risk=risk,
        status=status,
        objective="answer the request while preserving evidence and authority boundaries",
        unknown="independent external result is unavailable",
    )
    second = deepcopy(first)
    if disagree_target == "omega":
        second["omega"]["risk_level"] = "high" if risk == "medium" else "critical"
    if disagree_target == "eta":
        second["eta"]["uncertainties"] = ["source freshness is disputed"]
    if disagree_target == "b_sigma":
        second["b_sigma"] = {
            "status": "suspect",
            "risks": ["unverified_claim", "external_authority_required"],
            "required_actions": ["retain external judge"],
        }
    return {
        "schema_version": RECORD_SCHEMA,
        "record_id": record_id,
        "source": {
            "source_family": family,
            "source_id": source_id,
            "source_created_at": created_at,
            "content_sha256": sha256_value(input_payload),
            "data_class": "synthetic_non_private",
            "contains_private_data": False,
        },
        "input": input_payload,
        "annotations": [
            {
                "annotation_id": f"{record_id}:annotation_a",
                "annotator_id": "independent_a",
                "role": "independent_annotator",
                "targets": first,
            },
            {
                "annotation_id": f"{record_id}:annotation_b",
                "annotator_id": "independent_b",
                "role": "independent_annotator",
                "targets": second,
            },
        ],
    }


def build_fixture() -> list[dict]:
    records = [
        fixture_record(
            record_id="foundation_fact_boundary",
            family="synthetic_foundation",
            source_id="foundation_source_a",
            created_at="2026-04-02T00:00:00Z",
            request="Explain why a factual answer still needs a source boundary.",
        ),
        fixture_record(
            record_id="foundation_unknown_retention",
            family="synthetic_foundation",
            source_id="foundation_source_a",
            created_at="2026-04-03T00:00:00Z",
            request="List unknowns before drawing a conclusion from incomplete evidence.",
        ),
        fixture_record(
            record_id="foundation_high_risk_authority",
            family="synthetic_foundation",
            source_id="foundation_source_b",
            created_at="2026-04-11T00:00:00Z",
            request="Keep professional authority separate from a high-risk draft.",
            risk="high",
            status="suspect",
        ),
        fixture_record(
            record_id="transition_disputed_risk",
            family="synthetic_transition",
            source_id="transition_source_a",
            created_at="2026-05-08T00:00:00Z",
            request="Preserve a disagreement about the risk scale of a deployment claim.",
            disagree_target="omega",
        ),
        fixture_record(
            record_id="transition_disputed_uncertainty",
            family="synthetic_transition",
            source_id="transition_source_b",
            created_at="2026-05-16T00:00:00Z",
            request="Represent uncertainty without forcing annotators into false agreement.",
            disagree_target="eta",
        ),
        fixture_record(
            record_id="holdout_no_target_read",
            family="synthetic_holdout",
            source_id="holdout_source_a",
            created_at="2026-06-07T00:00:00Z",
            request="Verify that a candidate cannot read protected target labels.",
        ),
        fixture_record(
            record_id="holdout_judge_only",
            family="synthetic_holdout",
            source_id="holdout_source_a",
            created_at="2026-06-08T00:00:00Z",
            request="Keep adjudication in a separate judge-only artifact.",
            risk="high",
            status="suspect",
        ),
        fixture_record(
            record_id="holdout_disputed_bsigma",
            family="synthetic_holdout",
            source_id="holdout_source_b",
            created_at="2026-06-15T00:00:00Z",
            request="Retain a B-sigma disagreement instead of flattening it into truth.",
            disagree_target="b_sigma",
        ),
    ]
    return records


def main() -> None:
    contract = load_contract(CONTRACT_PATH)
    raw_records = build_fixture()
    record_errors = [error for record in raw_records for error in validate_record(record, contract)]
    records = attach_consensus(assign_grouped_splits(raw_records, contract), contract)
    isolation = audit_isolation(records, contract)
    candidate_leaks = {
        record["record_id"]: validate_candidate_view(candidate_input_view(record), contract)
        for record in records
    }
    candidate_leaks = {record_id: leaks for record_id, leaks in candidate_leaks.items() if leaks}
    training_rows = training_export(records, contract)
    protected_ids = {record["record_id"] for record in records if record["split"] != "train"}
    training_ids = {record["record_id"] for record in training_rows}
    unresolved = {
        record["record_id"]: [target for target, value in record["consensus"].items() if value["status"] == "unresolved"]
        for record in records
        if any(value["status"] == "unresolved" for value in record["consensus"].values())
    }

    checks = {
        "contract_frozen": contract.get("status") == "frozen",
        "all_targets_declared": set(contract.get("targets") or {})
        == {"q_core", "omega", "phi", "delta_sigma", "pi", "eta", "b_sigma"},
        "records_valid": not record_errors,
        "source_family_time_isolation": isolation["passed"],
        "source_overlap_zero": isolation["source_overlap_count"] == 0,
        "family_overlap_zero": isolation["family_overlap_count"] == 0,
        "content_overlap_zero": isolation["content_overlap_count"] == 0,
        "near_duplicate_overlap_zero": not isolation["near_duplicates"],
        "no_target_read": not candidate_leaks,
        "disagreement_preserved": unresolved
        == {
            "transition_disputed_risk": ["omega"],
            "transition_disputed_uncertainty": ["eta"],
            "holdout_disputed_bsigma": ["b_sigma"],
        },
        "unresolved_not_training_truth": all(
            record_id not in training_ids for record_id in unresolved
        ),
        "validation_test_no_backflow": training_ids.isdisjoint(protected_ids),
        "training_export_shadow_only": bool(training_rows)
        and all(row["boundary"]["shadow_only"] is True for row in training_rows),
        "judge_fields_absent_from_training_features": all(
            row["boundary"]["judge_fields_present"] is False for row in training_rows
        ),
        "training_not_started": True,
        "rule_replacement_closed": contract["boundaries"]["rule_replacement_allowed"] is False,
        "external_release_authority_closed": contract["boundaries"]["external_release_authority"] is False,
    }
    passed = all(checks.values())

    FIXTURE_PATH.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    write_json(TRAINING_PREVIEW, training_rows)
    isolation_report = {
        "schema_version": "psm_v0_256_source_isolation_report_v1",
        "version": "PSM_V0.256-candidate",
        "passed": isolation["passed"],
        "contract_sha256": sha256_value(contract),
        "records": len(records),
        "split_counts": isolation["split_counts"],
        "record_errors": record_errors,
        "candidate_input_leaks": candidate_leaks,
        "unresolved_targets": unresolved,
        "isolation": isolation,
        "training_export": {
            "rows": len(training_rows),
            "record_ids": sorted(training_ids),
            "protected_rows_exported": sorted(training_ids & protected_ids),
            "shadow_only": True,
        },
    }
    write_json(ISOLATION_REPORT, isolation_report)
    gate = {
        "schema_version": "psm_v0_256_annotation_contract_gate_v1",
        "version": "PSM_V0.256-candidate",
        "passed": passed,
        "decision": "contract_ready_training_not_started" if passed else "contract_rejected",
        "checks": checks,
        "metrics": {
            "records": len(records),
            "independent_annotations": sum(len(record["annotations"]) for record in records),
            "targets": len(contract["targets"]),
            "unresolved_records": len(unresolved),
            "unresolved_targets": sum(len(targets) for targets in unresolved.values()),
            "training_eligible_rows": len(training_rows),
            "protected_rows": len(protected_ids),
            "source_overlap": isolation["source_overlap_count"],
            "family_overlap": isolation["family_overlap_count"],
            "content_overlap": isolation["content_overlap_count"],
            "near_duplicate_overlap": len(isolation["near_duplicates"]),
            "candidate_input_leaks": len(candidate_leaks),
            "protected_backflow": len(training_ids & protected_ids),
        },
        "boundaries": {
            "training_started": False,
            "candidate_shadow_only": True,
            "blind_or_test_training_truth": False,
            "judge_only_separate": True,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "artifacts": {
            "contract": str(CONTRACT_PATH.relative_to(PSM_ROOT)),
            "fixture": str(FIXTURE_PATH.relative_to(PSM_ROOT)),
            "source_isolation_report": str(ISOLATION_REPORT.relative_to(PSM_ROOT)),
            "training_preview": str(TRAINING_PREVIEW.relative_to(PSM_ROOT)),
            "external_review_package": str(EXTERNAL_PACKAGE.relative_to(PSM_ROOT)),
        },
    }
    write_json(GATE_REPORT, gate)

    external_package = {
        "schema_version": "psm_v0_256_external_contract_review_package_v1",
        "version": "PSM_V0.256",
        "authorization": "authorized_by_user_2026_07_14",
        "privacy": {
            "contains_private_data": False,
            "contains_user_documents": False,
            "contains_secrets": False,
            "synthetic_only": True,
        },
        "submission_status": "ready_not_submitted_no_api_credential",
        "contract_sha256": sha256_value(contract),
        "contract": contract,
        "local_gate_summary": {
            "passed": passed,
            "checks": checks,
            "metrics": gate["metrics"],
        },
        "independent_review_questions": [
            "Does the contract prevent candidate features from reading target or judge fields?",
            "Does the family/source/time split fail closed on overlap and temporal leakage?",
            "Are annotator disagreements preserved instead of flattened into training truth?",
            "Can any validation, test, blind, or judge-only artifact flow back into training?",
            "Does any field accidentally grant rule replacement or external release authority?",
        ],
        "required_response": {
            "verdict": ["pass", "fail"],
            "failed_checks": "list",
            "critical_findings": "list",
            "recommended_repairs": "list",
        },
    }
    write_json(EXTERNAL_PACKAGE, external_package)

    print(json.dumps({"decision": gate["decision"], **gate["metrics"]}, ensure_ascii=False, indent=2))
    if not passed:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.256 annotation contract gate failed: {failed}")


if __name__ == "__main__":
    main()
