from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path

from psm_v0.state_annotation_contract import (
    assign_grouped_splits,
    candidate_input_view,
    load_contract,
    split_for_timestamp,
    validate_candidate_view,
    validate_record,
)

from scripts.evaluate_v0_256_annotation_contract import build_fixture


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_261_state_annotation_contract_v2.json"


class StateAnnotationContractV261Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(CONTRACT_PATH)
        self.record = build_fixture()[0]

    def test_closed_record_rejects_aliases_at_multiple_levels(self) -> None:
        self.assertEqual(validate_record(self.record, self.contract), [])
        mutations = []
        top = deepcopy(self.record)
        top["release_approval"] = True
        mutations.append(top)
        nested = deepcopy(self.record)
        nested["input"]["hidden_labels"] = {"omega": "medium"}
        mutations.append(nested)
        annotation = deepcopy(self.record)
        annotation["annotations"][0]["adjudicated_truth"] = True
        mutations.append(annotation)
        target = deepcopy(self.record)
        target["annotations"][0]["targets"]["omega"]["judge_score"] = 1
        mutations.append(target)
        target_container = deepcopy(self.record)
        target_container["annotations"][0]["targets"]["hidden_judge_target"] = {"verdict": "pass"}
        mutations.append(target_container)
        for mutation in mutations:
            self.assertTrue(validate_record(mutation, self.contract))

    def test_candidate_projection_is_exclusive(self) -> None:
        view = candidate_input_view(self.record)
        self.assertEqual(validate_candidate_view(view, self.contract), [])
        view["input"]["evidence"][0]["consensus_hint"] = "pass"
        self.assertTrue(validate_candidate_view(view, self.contract))

    def test_leaf_types_block_nested_side_channels(self) -> None:
        nested_request = candidate_input_view(self.record)
        nested_request["input"]["request"] = {"concealed_signal": "pass"}
        self.assertTrue(validate_candidate_view(nested_request, self.contract))

        nested_evidence = candidate_input_view(self.record)
        nested_evidence["input"]["evidence"][0]["status"] = {"judge_hint": "pass"}
        self.assertTrue(validate_candidate_view(nested_evidence, self.contract))

    def test_malformed_objects_fail_closed_without_exception(self) -> None:
        malformed_input = deepcopy(self.record)
        malformed_input["input"] = "not-an-object"
        self.assertTrue(validate_record(malformed_input, self.contract))

        malformed_annotation = deepcopy(self.record)
        malformed_annotation["annotations"] = ["not-an-object"]
        self.assertTrue(validate_record(malformed_annotation, self.contract))

        missing_role = deepcopy(self.record)
        del missing_role["annotations"][0]["role"]
        self.assertTrue(validate_record(missing_role, self.contract))

    def test_split_boundaries_are_mutually_exclusive(self) -> None:
        self.assertEqual(split_for_timestamp("2026-04-30T23:59:59Z", self.contract), "train")
        self.assertEqual(split_for_timestamp("2026-05-01T00:00:00Z", self.contract), "validation")
        self.assertEqual(split_for_timestamp("2026-06-01T00:00:00Z", self.contract), "test")

    def test_source_group_crossing_time_boundary_is_rejected(self) -> None:
        records = build_fixture()[:2]
        for item in records:
            item["source"]["source_family"] = "same"
            item["source"]["source_id"] = "same"
        records[1]["source"]["source_created_at"] = "2026-05-01T00:00:00Z"
        with self.assertRaises(ValueError):
            assign_grouped_splits(records, self.contract)


if __name__ == "__main__":
    unittest.main()
