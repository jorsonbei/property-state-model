from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from psm_v0.state_annotation_contract import (
    assign_grouped_splits,
    attach_consensus,
    audit_isolation,
    candidate_input_view,
    load_contract,
    sha256_value,
    target_consensus,
    training_export,
    validate_candidate_view,
    validate_record,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_256_state_annotation_contract.json"


def targets(risk: str = "medium", objective: str = "answer with bounded evidence") -> dict:
    return {
        "q_core": {
            "objective": objective,
            "protected_boundaries": ["do not invent evidence"],
            "veto_conditions": ["missing authority"],
        },
        "omega": {
            "risk_level": risk,
            "time_scale": "request",
            "validation_scale": "source_check",
            "cost_scale": "bounded",
        },
        "phi": {"facts": ["synthetic fixture"], "unknowns": ["external outcome"]},
        "delta_sigma": {"pressures": ["time"], "missing_pressure_data": ["deadline"]},
        "pi": {"actors": ["user"], "artifacts": ["request"], "dependencies": ["source"]},
        "eta": {"uncertainties": ["external outcome"], "tail_events": ["source failure"]},
        "b_sigma": {"status": "review", "risks": ["unverified_claim"], "required_actions": ["check source"]},
    }


def record(record_id: str, family: str, source_id: str, created_at: str, request: str) -> dict:
    input_payload = {"request": request, "evidence": [{"ref": f"synthetic:{source_id}", "status": "available"}]}
    common = targets()
    return {
        "schema_version": "psm_state_annotation_record_v1",
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
            {"annotation_id": f"{record_id}:a", "annotator_id": "annotator_a", "targets": deepcopy(common)},
            {"annotation_id": f"{record_id}:b", "annotator_id": "annotator_b", "targets": deepcopy(common)},
        ],
    }


class StateAnnotationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(CONTRACT_PATH)

    def test_contract_keeps_every_property_state_target_and_boundary(self) -> None:
        self.assertEqual(
            set(self.contract["targets"]),
            {"q_core", "omega", "phi", "delta_sigma", "pi", "eta", "b_sigma"},
        )
        boundaries = self.contract["boundaries"]
        self.assertTrue(boundaries["no_target_read"])
        self.assertTrue(boundaries["no_backfit"])
        self.assertTrue(boundaries["judge_only_separate"])
        self.assertTrue(boundaries["candidate_shadow_only"])
        self.assertFalse(boundaries["rule_replacement_allowed"])

    def test_candidate_view_cannot_read_annotations_or_judge_fields(self) -> None:
        item = record("r1", "foundation", "source_1", "2026-04-01T00:00:00Z", "Explain source limits.")
        view = candidate_input_view(item)
        self.assertEqual(validate_candidate_view(view, self.contract), [])
        self.assertNotIn("annotations", json.dumps(view, ensure_ascii=False))
        leaked = deepcopy(view)
        leaked["input"]["judge_labels"] = {"omega": "critical"}
        self.assertEqual(validate_candidate_view(leaked, self.contract), ["judge_labels"])

    def test_disagreement_is_preserved_and_never_becomes_training_truth(self) -> None:
        item = record("r2", "transition", "source_2", "2026-05-10T00:00:00Z", "Assess an uncertain claim.")
        item["annotations"][1]["targets"]["omega"]["risk_level"] = "high"
        consensus = target_consensus(item, self.contract)
        self.assertEqual(consensus["omega"]["status"], "unresolved")
        self.assertIsNone(consensus["omega"]["resolved_value"])
        self.assertEqual(len(consensus["omega"]["vote_distribution"]), 2)

    def test_grouped_family_source_time_split_is_clean(self) -> None:
        records = [
            record("train_1", "foundation", "foundation_1", "2026-04-01T00:00:00Z", "Bound a factual answer."),
            record("train_2", "foundation", "foundation_1", "2026-04-02T00:00:00Z", "List missing evidence."),
            record("validation_1", "transition", "transition_1", "2026-05-10T00:00:00Z", "Review a deployment claim."),
            record("test_1", "holdout", "holdout_1", "2026-06-10T00:00:00Z", "Audit an unseen authority request."),
        ]
        assigned = attach_consensus(assign_grouped_splits(records, self.contract), self.contract)
        audit = audit_isolation(assigned, self.contract)
        self.assertTrue(audit["passed"], audit["errors"])
        self.assertEqual(audit["split_counts"], {"test": 1, "train": 2, "validation": 1})
        exported = training_export(assigned, self.contract)
        self.assertEqual({item["record_id"] for item in exported}, {"train_1", "train_2"})
        self.assertTrue(all(item["boundary"]["shadow_only"] for item in exported))

    def test_family_overlap_and_cross_split_duplicates_fail_closed(self) -> None:
        first = record("train", "shared", "source_train", "2026-04-01T00:00:00Z", "Same protected request")
        second = record("test", "shared", "source_test", "2026-06-10T00:00:00Z", "Same protected request")
        second["source"]["content_sha256"] = first["source"]["content_sha256"]
        assigned = assign_grouped_splits([first, second], self.contract)
        audit = audit_isolation(assigned, self.contract)
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["family_overlap_count"], 1)
        self.assertEqual(audit["content_overlap_count"], 1)
        self.assertEqual(len(audit["near_duplicates"]), 1)

    def test_record_validation_rejects_private_or_tampered_input(self) -> None:
        item = record("r3", "foundation", "source_3", "2026-04-03T00:00:00Z", "Synthetic question")
        self.assertEqual(validate_record(item, self.contract), [])
        item["source"]["contains_private_data"] = True
        item["input"]["request"] = "tampered"
        errors = validate_record(item, self.contract)
        self.assertTrue(any("private" in error for error in errors))
        self.assertTrue(any("hash" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
