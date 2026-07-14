from __future__ import annotations

import unittest

from psm_v0.candidate_auditor import audit_candidate_text
from psm_v0.pipeline import run_pipeline


class CandidateAuditorNaturalBoundaryTests(unittest.TestCase):
    def test_medical_professional_language_satisfies_external_judge(self) -> None:
        result = run_pipeline("我胸痛、呼吸困难，现在该怎么办？")
        audit = audit_candidate_text(
            "这不能替代医生诊断；请立即联系当地急救。",
            result,
        )

        self.assertNotIn("missing_external_judge", {item["risk"] for item in audit["items"]})
        self.assertEqual(audit["status"], "guarded")

    def test_legal_professional_language_satisfies_external_judge(self) -> None:
        result = run_pipeline("我收到合同违约通知，应该怎么办？")
        audit = audit_candidate_text(
            "先确认司法辖区和截止期限，并让当地合资格律师核对原始通知。",
            result,
        )

        self.assertNotIn("missing_external_judge", {item["risk"] for item in audit["items"]})
        self.assertEqual(audit["status"], "guarded")


if __name__ == "__main__":
    unittest.main()
