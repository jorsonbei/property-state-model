from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class TaskCompletionV268Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((PSM_ROOT / "benchmarks" / "v0_268_task_completion_contract.json").read_text(encoding="utf-8"))
        cls.errata = [
            json.loads((PSM_ROOT / "benchmarks" / name).read_text(encoding="utf-8"))
            for name in (
                "v0_268_task_completion_errata.json",
                "v0_268_task_completion_errata_2.json",
                "v0_268_task_completion_errata_3.json",
            )
        ]
        cls.report = json.loads((PSM_ROOT / "runtime" / "v0_268_task_completion_report.json").read_text(encoding="utf-8"))
        cls.gate = json.loads((PSM_ROOT / "runtime" / "v0_268_task_completion_gate.json").read_text(encoding="utf-8"))
        cls.ledger = json.loads((PSM_ROOT / "runtime" / "v0_268_task_completion_initial_failure_ledger.json").read_text(encoding="utf-8"))

    def test_frozen_family_coverage_and_final_pass(self) -> None:
        self.assertEqual(self.contract["evaluation"]["frozen_case_count"], 21)
        self.assertEqual(len(self.contract["evaluation"]["families"]), 7)
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["summary"]["passed"], 21)
        self.assertEqual(self.report["summary"]["failed"], 0)
        self.assertTrue(all(item["cases"] == item["passed"] == 3 for item in self.report["summary"]["families"].values()))

    def test_initial_failures_and_transparent_errata_are_retained(self) -> None:
        self.assertEqual(self.ledger["initial_failure_count"], 5)
        self.assertTrue(self.ledger["append_only"])
        self.assertEqual(self.ledger["contract_sha256"], self.report["contract_sha256"])
        self.assertTrue(all(item["source_contract_unchanged"] for item in self.errata))
        self.assertEqual(self.errata[1]["applies_after"], "v0_268_task_completion_errata.json")
        self.assertEqual(self.errata[2]["applies_after"], "v0_268_task_completion_errata_2.json")

    def test_task_completion_has_no_failure_template_or_release_authority(self) -> None:
        self.assertEqual(self.report["summary"]["provider_failure_templates"], 0)
        self.assertEqual(self.report["summary"]["task_restatements_without_completion"], 0)
        self.assertTrue(self.gate["passed"])
        self.assertTrue(all(self.gate["checks"].values()))
        self.assertFalse(any(self.contract["release_boundary"].values()))
        self.assertFalse(self.contract["source_isolation"]["evaluation_rows_used_for_training"])


if __name__ == "__main__":
    unittest.main()
