from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


def read(path: str) -> dict:
    return json.loads((PSM_ROOT / path).read_text(encoding="utf-8"))


class LongContextStateV272Tests(unittest.TestCase):
    def test_all_long_context_families_pass(self) -> None:
        report = read("runtime/v0_272_long_context_state_report.json")
        summary = report["summary"]
        self.assertTrue(report["passed"])
        self.assertEqual(summary["cases"], summary["passed"])
        self.assertEqual(summary["cases"], 10)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(len(summary["families"]), 5)
        self.assertTrue(all(item["cases"] == item["passed"] == 2 for item in summary["families"].values()))

    def test_initial_failures_and_domain_errata_are_retained(self) -> None:
        ledger = read("runtime/v0_272_long_context_initial_failure_ledger.json")
        errata = read("benchmarks/v0_272_long_context_state_errata.json")
        gate = read("runtime/v0_272_long_context_state_gate.json")
        self.assertTrue(ledger["append_only"])
        self.assertEqual(ledger["initial_failure_count"], 10)
        self.assertTrue(ledger["first_run_completed_before_candidate_changes"])
        self.assertTrue(errata["source_contract_unchanged"])
        self.assertTrue(errata["created_after_initial_run"])
        self.assertEqual(len(errata["corrections"]), 1)
        self.assertTrue(gate["passed"])

    def test_state_and_release_boundaries_remain_closed(self) -> None:
        report = read("runtime/v0_272_long_context_state_report.json")
        contract = read("benchmarks/v0_272_long_context_state_contract.json")
        self.assertEqual(report["summary"]["assistant_history_contamination"], 0)
        self.assertEqual(report["summary"]["stale_state_violations"], 0)
        self.assertFalse(any(contract["source_isolation"].values()))
        self.assertFalse(any(contract["release_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
