from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


def read(relative: str) -> dict:
    return json.loads((PSM_ROOT / relative).read_text(encoding="utf-8"))


class OpenContextGeneralizationV274Tests(unittest.TestCase):
    def test_frozen_families_and_final_gate_pass(self) -> None:
        contract = read("benchmarks/v0_274_open_context_generalization_contract.json")
        report = read("runtime/v0_274_open_context_generalization_report.json")
        gate = read("runtime/v0_274_open_context_generalization_gate.json")
        self.assertEqual(len(contract["cases"]), 10)
        self.assertEqual(len(contract["evaluation"]["families"]), 5)
        self.assertTrue(report["passed"])
        self.assertEqual(report["summary"]["passed"], 10)
        self.assertEqual(report["summary"]["capsule_missing"], 0)
        self.assertEqual(report["summary"]["stale_state_violations"], 0)
        self.assertTrue(gate["passed"])
        self.assertTrue(all(gate["checks"].values()))

    def test_initial_failures_and_source_isolation_are_retained(self) -> None:
        contract = read("benchmarks/v0_274_open_context_generalization_contract.json")
        ledger = read("runtime/v0_274_open_context_initial_failure_ledger.json")
        self.assertEqual(ledger["initial_failure_count"], 10)
        self.assertTrue(ledger["append_only"])
        self.assertTrue(ledger["first_run_completed_before_candidate_changes"])
        self.assertFalse(any(contract["source_isolation"].values()))
        self.assertFalse(any(contract["release_boundary"].values()))

    def test_browser_docker_and_promotion_boundaries_pass(self) -> None:
        browser = read("runtime/v0_274_open_context_browser_regression/report.json")
        docker = read("runtime/v0_274_open_context_docker_boundary.json")
        manifest = read("runtime/v0_274_open_context_generalization_promotion_manifest.json")
        self.assertTrue(browser["passed"])
        self.assertTrue(all(browser["checks"].values()))
        self.assertTrue(docker["passed"])
        self.assertTrue(all(docker["checks"].values()))
        self.assertTrue(manifest["promoted"])
        self.assertFalse(manifest["open_context_generalization"]["human_validation_claimed"])
        self.assertFalse(manifest["release_boundary"]["external_release_authority"])


if __name__ == "__main__":
    unittest.main()
