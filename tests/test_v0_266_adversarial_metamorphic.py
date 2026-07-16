from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class AdversarialMetamorphicV266Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((PSM_ROOT / "benchmarks" / "v0_266_adversarial_metamorphic_contract.json").read_text(encoding="utf-8"))
        cls.report = json.loads((PSM_ROOT / "runtime" / "v0_266_adversarial_metamorphic_report.json").read_text(encoding="utf-8"))
        cls.gate = json.loads((PSM_ROOT / "runtime" / "v0_266_adversarial_metamorphic_gate.json").read_text(encoding="utf-8"))
        cls.ledger = json.loads((PSM_ROOT / "runtime" / "v0_266_adversarial_initial_failure_ledger.json").read_text(encoding="utf-8"))
        cls.errata = json.loads((PSM_ROOT / "benchmarks" / "v0_266_adversarial_metamorphic_errata.json").read_text(encoding="utf-8"))

    def test_frozen_families_and_counts(self) -> None:
        self.assertEqual(self.contract["evaluation"]["frozen_pair_count"], 15)
        self.assertEqual(self.contract["evaluation"]["frozen_variant_count"], 30)
        self.assertEqual(
            {pair["family"] for pair in self.contract["pairs"]},
            {"paraphrase_equivalence", "role_history_isolation", "negation_scope", "event_time_order", "release_boundary_preservation"},
        )

    def test_all_variants_and_invariants_pass(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["summary"]["pairs_failed"], 0)
        self.assertEqual(self.report["summary"]["variants_failed"], 0)
        self.assertEqual(self.report["summary"]["critical_fact_hallucinations"], 0)
        self.assertEqual(self.report["summary"]["critical_safety_false_negatives"], 0)

    def test_evaluation_isolation_and_initial_failures_are_preserved(self) -> None:
        source = self.contract["source_isolation"]
        self.assertFalse(source["evaluation_rows_used_for_training"])
        self.assertFalse(source["blind_or_evaluation_backflow_allowed"])
        self.assertTrue(self.ledger["append_only"])
        self.assertTrue(self.ledger["first_run_completed_before_candidate_changes"])
        self.assertEqual(self.ledger["contract_sha256"], self.report["contract_sha256"])
        self.assertTrue(self.errata["source_contract_unchanged"])
        self.assertEqual(len(self.errata["corrections"]), 3)

    def test_release_and_model_authority_stay_closed(self) -> None:
        self.assertTrue(self.gate["passed"])
        self.assertTrue(all(self.gate["checks"].values()))
        self.assertFalse(any(self.contract["release_boundary"].values()))
        self.assertTrue(self.contract["authority"]["deterministic_controller_authoritative"])
        self.assertFalse(self.contract["authority"]["shadow_model_may_control_release"])


if __name__ == "__main__":
    unittest.main()
