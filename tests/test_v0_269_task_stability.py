from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class TaskStabilityV269Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((PSM_ROOT / "benchmarks" / "v0_269_task_stability_contract.json").read_text(encoding="utf-8"))
        cls.report = json.loads((PSM_ROOT / "runtime" / "v0_269_task_stability_report.json").read_text(encoding="utf-8"))
        cls.gate = json.loads((PSM_ROOT / "runtime" / "v0_269_task_stability_gate.json").read_text(encoding="utf-8"))
        cls.recovery = json.loads((PSM_ROOT / "runtime" / "v0_269_recovery_report.json").read_text(encoding="utf-8"))
        cls.ledger = json.loads((PSM_ROOT / "runtime" / "v0_269_task_stability_initial_failure_ledger.json").read_text(encoding="utf-8"))

    def test_repeated_semantic_and_provider_stability_passes(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(summary["selected_cases"], 7)
        self.assertEqual(summary["families"], 7)
        self.assertEqual(summary["runs"], summary["passed_runs"])
        self.assertEqual(summary["runs"], 21)
        self.assertEqual(summary["provider_drift_events"], 0)
        self.assertEqual(summary["deterministic_drift_events"], 0)

    def test_latency_and_recovery_stay_inside_frozen_budget(self) -> None:
        summary = self.report["summary"]
        budget = self.contract["performance_budget"]
        self.assertLessEqual(summary["p50_ms"], budget["p50_max_ms"])
        self.assertLessEqual(summary["p95_ms"], budget["p95_max_ms"])
        self.assertLessEqual(summary["max_ms"], budget["single_run_max_ms"])
        self.assertTrue(self.recovery["passed"])
        self.assertTrue(all(self.recovery["checks"].values()))

    def test_failure_history_and_release_boundaries_are_retained(self) -> None:
        self.assertTrue(self.ledger["append_only"])
        self.assertEqual(self.ledger["contract_sha256"], self.report["contract_sha256"])
        self.assertTrue(self.gate["passed"])
        self.assertTrue(all(self.gate["checks"].values()))
        self.assertFalse(any(self.contract["source_isolation"].values()))
        self.assertFalse(any(self.contract["release_boundary"].values()))
        self.assertFalse(self.recovery["human_actions_executed"])


if __name__ == "__main__":
    unittest.main()
