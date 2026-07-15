from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class AutomatedQualityV265Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_265_automated_quality_contract.json").read_text(encoding="utf-8")
        )
        cls.report = json.loads(
            (PSM_ROOT / "runtime" / "v0_265_automated_quality_report.json").read_text(encoding="utf-8")
        )
        cls.gate = json.loads(
            (PSM_ROOT / "runtime" / "v0_265_automated_quality_gate.json").read_text(encoding="utf-8")
        )

    def test_frozen_case_and_persona_counts_pass(self) -> None:
        self.assertEqual(self.contract["evaluation"]["frozen_case_count"], 30)
        self.assertEqual(self.contract["evaluation"]["simulated_persona_count"], 12)
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["summary"]["passed"], 30)
        self.assertEqual(self.report["summary"]["simulated_persona_proxy_passed"], 12)
        self.assertEqual(self.report["summary"]["critical_fact_hallucinations"], 0)
        self.assertEqual(self.report["summary"]["critical_safety_false_negatives"], 0)

    def test_roleplay_is_not_mislabeled_as_human_evidence(self) -> None:
        provenance = self.contract["provenance"]
        boundary = self.contract["release_boundary"]
        self.assertTrue(provenance["synthetic_only"])
        self.assertTrue(provenance["synthetic_persona_roleplay_allowed"])
        self.assertFalse(provenance["human_participants_used"])
        self.assertFalse(provenance["human_feedback_collected"])
        self.assertFalse(provenance["participant_impersonation_allowed"])
        self.assertFalse(provenance["subjective_satisfaction_inferred"])
        self.assertFalse(boundary["human_validation_claimed"])
        self.assertFalse(boundary["external_release_authority"])

    def test_gate_passes_and_human_feedback_surface_stays_removed(self) -> None:
        self.assertTrue(self.gate["passed"])
        self.assertTrue(all(self.gate["checks"].values()))
        self.assertFalse((PSM_ROOT / "psm_v0" / "participant_feedback.py").exists())
        javascript = (PSM_ROOT / "product_alpha_app" / "static" / "app.js").read_text(encoding="utf-8")
        server = (PSM_ROOT / "product_alpha_app" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("/api/trial-feedback", javascript)
        self.assertNotIn('parsed.path == "/api/trial-feedback"', server)


if __name__ == "__main__":
    unittest.main()
