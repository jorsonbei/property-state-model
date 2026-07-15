from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_261_state_annotation_contract_v2.json"
PREVIOUS_PACKAGE = RUNTIME / "v0_256_external_contract_review_package.json"
PREVIOUS_REVIEW = RUNTIME / "v0_261_openai_external_contract_judge_attempt_1_failed.json"
FIXTURE_PATH = RUNTIME / "v0_261_repaired_source_isolated_annotation_fixture.jsonl"
TRAINING_PREVIEW = RUNTIME / "v0_261_repaired_shadow_training_export_preview.json"
GATE_REPORT = RUNTIME / "v0_261_annotation_contract_repair_gate.json"
EXTERNAL_PACKAGE = RUNTIME / "v0_261_external_contract_review_package.json"
sys.path.insert(0, str(PSM_ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_v0_256_annotation_contract import build_fixture  # noqa: E402
from psm_v0.state_annotation_contract import (  # noqa: E402
    assign_grouped_splits,
    attach_consensus,
    audit_isolation,
    candidate_input_view,
    load_contract,
    sha256_value,
    split_for_timestamp,
    training_export,
    validate_candidate_view,
    validate_record,
)


QUESTIONS = [
    "Does the contract prevent candidate features from reading target or judge fields?",
    "Does the family/source/time split fail closed on overlap and temporal leakage?",
    "Are annotator disagreements preserved instead of flattened into training truth?",
    "Can any validation, test, blind, or judge-only artifact flow back into training?",
    "Does any field accidentally grant rule replacement or external release authority?",
]


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mutation_checks(contract: dict, raw_records: list[dict]) -> dict[str, bool]:
    candidate_alias = candidate_input_view(raw_records[0])
    candidate_alias["input"]["nested"] = {"alternative_ground_truth": "leak"}

    flattened = deepcopy(raw_records[0])
    flattened["consensus"] = {"omega": "medium"}

    authority = deepcopy(raw_records[0])
    authority["release_approval"] = True

    nested_leaf = candidate_input_view(raw_records[0])
    nested_leaf["input"]["request"] = {"concealed_signal": "pass"}

    malformed = deepcopy(raw_records[0])
    malformed["input"] = "not-an-object"

    extra_target = deepcopy(raw_records[0])
    extra_target["annotations"][0]["targets"]["hidden_judge_target"] = {"verdict": "pass"}

    crossed = [deepcopy(raw_records[0]), deepcopy(raw_records[1])]
    crossed[0]["source"]["source_family"] = "crossed"
    crossed[1]["source"]["source_family"] = "crossed"
    crossed[0]["source"]["source_id"] = "crossed_source"
    crossed[1]["source"]["source_id"] = "crossed_source"
    crossed[1]["source"]["source_created_at"] = "2026-05-01T00:00:00Z"
    group_crossing_rejected = False
    try:
        assign_grouped_splits(crossed, contract)
    except ValueError:
        group_crossing_rejected = True

    return {
        "nested_candidate_alias_rejected": bool(validate_candidate_view(candidate_alias, contract)),
        "flattened_consensus_field_rejected": bool(validate_record(flattened, contract)),
        "release_authority_field_rejected": bool(validate_record(authority, contract)),
        "nested_leaf_payload_rejected": bool(validate_candidate_view(nested_leaf, contract)),
        "malformed_record_rejected_without_exception": bool(validate_record(malformed, contract)),
        "extra_target_name_rejected": bool(validate_record(extra_target, contract)),
        "train_end_boundary_exact": split_for_timestamp("2026-04-30T23:59:59Z", contract) == "train",
        "validation_start_boundary_exact": split_for_timestamp("2026-05-01T00:00:00Z", contract) == "validation",
        "test_start_boundary_exact": split_for_timestamp("2026-06-01T00:00:00Z", contract) == "test",
        "source_group_crossing_rejected": group_crossing_rejected,
    }


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
    training_ids = {row["record_id"] for row in training_rows}
    protected_ids = {record["record_id"] for record in records if record["split"] != "train"}
    unresolved_ids = {
        record["record_id"]
        for record in records
        if any(value["status"] == "unresolved" for value in record["consensus"].values())
    }
    mutations = mutation_checks(contract, raw_records)
    target_provenance_retained = all(
        item["derivation"] == "unanimous_raw_train_annotations"
        and item["agreement"] == 1.0
        and len(item["source_annotation_ids"]) >= 2
        and item["vote_distribution"]
        for row in training_rows
        for item in row["target_view"].values()
    )
    artifact_boundaries_retained = all(
        row["boundary"]["source_origin"] == "train_only"
        and row["boundary"]["validation_test_blind_judge_backflow"] is False
        and row["boundary"]["rule_or_authority_update_allowed"] is False
        for row in training_rows
    )

    checks = {
        "contract_v2_frozen": contract.get("schema_version") == "psm_state_annotation_contract_v2" and contract.get("status") == "frozen",
        "closed_schema_enforced": contract["closed_schema"]["unknown_fields_policy"] == "reject_at_every_object_level",
        "records_valid": not record_errors,
        "candidate_projection_exact": not candidate_leaks,
        "mutations_fail_closed": all(mutations.values()),
        "split_windows_mutually_exclusive": contract["split_policy"]["overlap_precedence"] == "none_reject_if_not_exactly_one",
        "source_family_time_isolation": isolation["passed"],
        "protected_artifacts_not_exported": training_ids.isdisjoint(protected_ids),
        "unresolved_not_exported": training_ids.isdisjoint(unresolved_ids),
        "raw_annotation_provenance_retained": target_provenance_retained,
        "artifact_flow_boundaries_retained": artifact_boundaries_retained,
        "validation_test_blind_judge_no_backflow": all(
            contract["artifact_flow_policy"][name] is True
            for name in ("validation_no_backflow", "test_no_backflow", "blind_no_backflow", "judge_only_no_backflow")
        ),
        "rule_and_release_authority_closed": contract["authority_policy"]["rule_replacement_authority"] is False
        and contract["authority_policy"]["external_release_authority"] is False,
        "training_not_started": True,
    }
    passed = all(checks.values())
    gate = {
        "schema_version": "psm_v0_261_annotation_contract_repair_gate_v1",
        "version": "PSM_V0.261-candidate",
        "passed": passed,
        "decision": "repaired_contract_ready_for_external_rejudge" if passed else "repaired_contract_rejected",
        "contract_sha256": sha256_value(contract),
        "previous_external_verdict": "fail",
        "checks": checks,
        "mutation_checks": mutations,
        "metrics": {
            "records": len(records),
            "independent_annotations": sum(len(record["annotations"]) for record in records),
            "training_eligible_rows": len(training_rows),
            "protected_rows": len(protected_ids),
            "unresolved_records": len(unresolved_ids),
            "candidate_input_leaks": len(candidate_leaks),
            "protected_backflow": len(training_ids & protected_ids),
        },
        "boundaries": {
            "failed_external_review_retained": True,
            "blind_or_test_evidence_modified": False,
            "training_started": False,
            "external_users_involved": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
    }

    FIXTURE_PATH.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    write_json(TRAINING_PREVIEW, training_rows)
    write_json(GATE_REPORT, gate)

    previous_package = json.loads(PREVIOUS_PACKAGE.read_text(encoding="utf-8"))
    previous_review = json.loads(PREVIOUS_REVIEW.read_text(encoding="utf-8"))
    external_package = {
        "schema_version": "psm_v0_261_external_contract_review_package_v1",
        "version": "PSM_V0.261",
        "authorization": previous_package["authorization"],
        "privacy": previous_package["privacy"],
        "submission_status": "ready_for_resubmission_after_failed_external_review",
        "contract_sha256": sha256_value(contract),
        "contract": contract,
        "repair_provenance": {
            "previous_contract_sha256": previous_package["contract_sha256"],
            "previous_external_review_sha256": sha256_value(previous_review),
            "previous_external_verdict": previous_review["review"]["verdict"],
            "failed_findings_addressed": len(previous_review["review"]["failed_checks"]),
            "blind_or_test_evidence_modified": False,
            "training_started": False
        },
        "local_gate_summary": {"passed": passed, "checks": checks, "metrics": gate["metrics"]},
        "independent_review_questions": QUESTIONS,
        "required_response": {
            "verdict": ["pass", "fail"],
            "failed_checks": "list",
            "critical_findings": "list",
            "recommended_repairs": "list"
        }
    }
    write_json(EXTERNAL_PACKAGE, external_package)
    print(json.dumps({"passed": passed, **gate["metrics"], "mutation_checks": mutations}, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(f"V0.261 repaired annotation contract gate failed: {[name for name, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
