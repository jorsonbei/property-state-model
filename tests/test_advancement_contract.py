from __future__ import annotations

import sys
import unittest
from pathlib import Path

from psm_v0.case_pack_validator import build_validation, evaluate_candidate_audit
from psm_v0.eval_runner import evaluate_case
from psm_v0.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "outputs" / "psm_v0" / "work"
sys.path.insert(0, str(WORK_ROOT))

import advance_to_v235 as advancement  # noqa: E402


class AdvancementContractTests(unittest.TestCase):
    def test_v249_chat_quality_preview_passes(self) -> None:
        family = advancement.family_by_version(249)
        cases = advancement.build_cases(family)
        rows = []

        for case in cases:
            result = run_pipeline(case["request"])
            rows.append(
                {
                    "case": case,
                    "result": result,
                    "eval": evaluate_case(case, result),
                    "candidate_audit_eval": evaluate_candidate_audit(case, result),
                }
            )

        validation = build_validation(rows, Path("v249_chat_quality_preview.json"))
        self.assertEqual(validation["summary"]["cases"], 18)
        self.assertTrue(validation["passed"])

    def test_v248_refresh_has_an_explicit_next_family(self) -> None:
        next_family = advancement.base.next_family_after_even(248)
        self.assertIsNotNone(next_family)
        self.assertEqual(next_family.version, 249)

    def test_v251_blind_set_boundary_preview_passes(self) -> None:
        family = advancement.family_by_version(251)
        cases = advancement.build_cases(family)
        rows = []
        for case in cases:
            result = run_pipeline(case["request"])
            rows.append(
                {
                    "case": case,
                    "result": result,
                    "eval": evaluate_case(case, result),
                    "candidate_audit_eval": evaluate_candidate_audit(case, result),
                }
            )
        validation = build_validation(rows, Path("v251_blind_boundary_preview.json"))
        self.assertEqual(validation["summary"]["cases"], 18)
        self.assertTrue(validation["passed"])

    def test_v250_refresh_has_an_explicit_next_family(self) -> None:
        next_family = advancement.base.next_family_after_even(250)
        self.assertIsNotNone(next_family)
        self.assertEqual(next_family.version, 251)


if __name__ == "__main__":
    unittest.main()
