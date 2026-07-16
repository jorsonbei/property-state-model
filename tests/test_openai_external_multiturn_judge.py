from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.openai_external_multiturn_judge import (
    build_request_payload,
    review_multiturn_package,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
PACKAGE_PATH = PSM_ROOT / "runtime" / "v0_271_external_multiturn_review_package.json"


def package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def passing_review(value: dict) -> dict:
    return {
        "review_payload_sha256": value["review_payload_sha256"],
        "verdict": "pass",
        "failed_item_ids": [],
        "critical_findings": [],
        "recommended_repairs": [],
        "item_reviews": [
            {"review_id": item["review_id"], "verdict": "pass", "dimension_failures": [], "finding": "The synthetic final answer preserves the multi-turn constraint and release boundary."}
            for item in value["review_payload"]["items"]
        ],
    }


class OpenAIExternalMultiturnJudgeTests(unittest.TestCase):
    def test_checked_in_package_is_synthetic_authorized_and_hash_locked(self) -> None:
        validate_review_package(package())

    def test_private_or_tampered_package_is_rejected(self) -> None:
        value = package()
        value["privacy"]["contains_private_data"] = True
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = package()
        value["review_payload"]["items"][0]["final_answer"] += " changed"
        with self.assertRaises(ValueError):
            build_request_payload(value)

    def test_review_parses_without_persisting_secret(self) -> None:
        value = package()

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "sk-test-secret")
            self.assertFalse(payload["store"])
            self.assertNotIn("expected_markers", payload["input"])
            return (
                {
                    "id": "resp_test",
                    "status": "completed",
                    "model": "gpt-5.4-test",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(passing_review(value))}]}],
                    "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                },
                {"x-request-id": "req_test"},
                200,
            )

        result = review_multiturn_package(value, api_key="sk-test-secret", transport=transport)
        self.assertTrue(result["passed"])
        self.assertNotIn("sk-test-secret", json.dumps(result))
        self.assertFalse(result["release_boundary"]["training_feedback_written"])
        self.assertFalse(result["release_boundary"]["external_release_authority"])

    def test_coverage_and_verdict_contradictions_fail_closed(self) -> None:
        value = package()
        review = passing_review(value)
        review["item_reviews"][0]["review_id"] = "wrong"
        with self.assertRaises(ValueError):
            validate_external_review(review, value)
        review = passing_review(value)
        review["item_reviews"][0]["verdict"] = "fail"
        review["item_reviews"][0]["dimension_failures"] = ["answer_directness"]
        with self.assertRaises(ValueError):
            validate_external_review(review, value)

    def test_external_failure_is_retained_and_local_repairs_are_not_mislabeled(self) -> None:
        judge = json.loads((PSM_ROOT / "runtime" / "v0_271_openai_external_multiturn_judge.json").read_text(encoding="utf-8"))
        repair = json.loads((PSM_ROOT / "runtime" / "v0_271_external_multiturn_repair_report.json").read_text(encoding="utf-8"))
        repaired = json.loads((PSM_ROOT / "runtime" / "v0_271_external_multiturn_repaired_candidate.json").read_text(encoding="utf-8"))
        checkpoint = json.loads((PSM_ROOT / "runtime" / "v0_271_external_multiturn_checkpoint.json").read_text(encoding="utf-8"))
        self.assertFalse(judge["passed"])
        self.assertEqual(judge["review"]["failed_item_ids"], ["M07", "M08"])
        self.assertTrue(repair["passed"])
        self.assertFalse(repair["external_rejudge_completed"])
        self.assertEqual(repaired["budget"]["maximum_api_calls"], 0)
        self.assertTrue(checkpoint["requires_user_input"])


if __name__ == "__main__":
    unittest.main()
