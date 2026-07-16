from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class MultiturnConstraintV270Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((PSM_ROOT / "benchmarks" / "v0_270_multiturn_constraint_contract.json").read_text(encoding="utf-8"))
        cls.errata = json.loads((PSM_ROOT / "benchmarks" / "v0_270_multiturn_constraint_errata.json").read_text(encoding="utf-8"))
        cls.report = json.loads((PSM_ROOT / "runtime" / "v0_270_multiturn_constraint_report.json").read_text(encoding="utf-8"))
        cls.gate = json.loads((PSM_ROOT / "runtime" / "v0_270_multiturn_constraint_gate.json").read_text(encoding="utf-8"))
        cls.ledger = json.loads((PSM_ROOT / "runtime" / "v0_270_multiturn_initial_failure_ledger.json").read_text(encoding="utf-8"))
        cls.evaluator_gap = json.loads((PSM_ROOT / "runtime" / "v0_270_evaluator_gap_report.json").read_text(encoding="utf-8"))

    def test_all_multiturn_families_pass(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(summary["cases"], summary["passed"])
        self.assertEqual(summary["cases"], 12)
        self.assertEqual(len(summary["families"]), 4)
        self.assertTrue(all(item["cases"] == item["passed"] == 3 for item in summary["families"].values()))
        self.assertEqual(summary["assistant_history_contamination"], 0)
        self.assertEqual(summary["stale_constraint_violations"], 0)

    def test_initial_failures_and_evaluator_corrections_are_retained(self) -> None:
        self.assertEqual(self.ledger["initial_failure_count"], 5)
        self.assertTrue(self.ledger["append_only"])
        self.assertEqual(self.ledger["contract_sha256"], self.report["contract_sha256"])
        self.assertTrue(self.errata["source_contract_unchanged"])
        self.assertEqual(len(self.errata["corrections"]), 3)
        self.assertFalse(self.evaluator_gap["passed"])
        self.assertFalse(self.evaluator_gap["source_contract_changed"])

    def test_release_and_training_authority_stay_closed(self) -> None:
        self.assertTrue(self.gate["passed"])
        self.assertTrue(all(self.gate["checks"].values()))
        self.assertFalse(any(self.contract["source_isolation"].values()))
        self.assertFalse(any(self.contract["release_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
