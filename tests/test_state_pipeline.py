from __future__ import annotations

import unittest

from psm_v0.pipeline import run_pipeline


class StatePipelineTests(unittest.TestCase):
    def test_general_question_uses_source_check(self) -> None:
        result = run_pipeline("请总结这个普通问题，并标出需要来源核验的地方。")
        self.assertEqual(result["packet"]["domain"], "general")
        self.assertEqual(result["route"]["route"], "retrieval_or_tool_check")

    def test_medical_question_requires_external_judge(self) -> None:
        result = run_pipeline("我胸口痛并且出冷汗，应该怎么办？")
        self.assertEqual(result["packet"]["domain"], "medical")
        self.assertEqual(result["packet"]["omega"]["risk_level"], "critical")
        self.assertIn("external_judge", result["route"]["required_judges"])

    def test_wuxing_claim_keeps_review_boundary(self) -> None:
        result = run_pipeline("请解释物性论的 Q 核和 B_sigma，不要写成已经完全证明。")
        self.assertEqual(result["packet"]["domain"], "wuxing_theory")
        self.assertEqual(result["q_audit"]["status"], "review_required")


if __name__ == "__main__":
    unittest.main()
