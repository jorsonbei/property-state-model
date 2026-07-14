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

    def test_wuxing_research_activity_uses_research_evidence_boundary(self) -> None:
        result = run_pipeline("请用物性论解释实验，但必须保留 NoTargetRead、NoBackfit 和外部裁判边界。")
        self.assertEqual(result["packet"]["domain"], "research")
        self.assertIn("backfit", {item["risk"] for item in result["packet"]["bsigma_risks"]})

    def test_wuxing_roadmap_reference_stays_in_theory_domain(self) -> None:
        result = run_pipeline("物性项目后续路线图必须引用当前阶段和已写入计划。")
        self.assertEqual(result["packet"]["domain"], "wuxing_theory")


if __name__ == "__main__":
    unittest.main()
