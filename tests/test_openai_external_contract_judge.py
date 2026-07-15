from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.openai_external_contract_judge import (
    build_request_payload,
    canonical_sha256,
    review_contract,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_256_external_contract_review_package.json"


def package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def passing_review(review_package: dict) -> dict:
    return {
        "contract_sha256": review_package["contract_sha256"],
        "verdict": "pass",
        "failed_checks": [],
        "critical_findings": [],
        "recommended_repairs": [],
        "question_reviews": [
            {"question": question, "verdict": "pass", "finding": "The boundary is explicit and fail closed."}
            for question in review_package["independent_review_questions"]
        ],
    }


class OpenAIExternalContractJudgeTests(unittest.TestCase):
    def test_checked_in_package_is_authorized_and_hash_locked(self) -> None:
        review_package = package()
        validate_review_package(review_package)
        self.assertEqual(canonical_sha256(review_package["contract"]), review_package["contract_sha256"])

    def test_package_tampering_fails_before_request_build(self) -> None:
        review_package = package()
        review_package["contract"]["boundaries"]["rule_replacement_allowed"] = True
        with self.assertRaises(ValueError):
            build_request_payload(review_package)

    def test_private_or_unapproved_package_is_rejected(self) -> None:
        review_package = package()
        review_package["privacy"]["contains_private_data"] = True
        with self.assertRaises(ValueError):
            validate_review_package(review_package)
        review_package = package()
        review_package["authorization"] = "not_authorized"
        with self.assertRaises(ValueError):
            validate_review_package(review_package)

    def test_real_transport_shape_is_parsed_without_persisting_secret(self) -> None:
        review_package = package()

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "sk-test-secret")
            self.assertFalse(payload["store"])
            return (
                {
                    "id": "resp_test",
                    "status": "completed",
                    "model": "gpt-5.4-test",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(passing_review(review_package)),
                                }
                            ],
                        }
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                },
                {"x-request-id": "req_test"},
                200,
            )

        result = review_contract(review_package, api_key="sk-test-secret", transport=transport)
        self.assertTrue(result["passed"])
        self.assertEqual(result["request_id"], "req_test")
        self.assertNotIn("sk-test-secret", json.dumps(result))

    def test_question_coverage_and_verdict_consistency_fail_closed(self) -> None:
        review_package = package()
        review = passing_review(review_package)
        review["question_reviews"][0]["question"] = "paraphrased"
        with self.assertRaises(ValueError):
            validate_external_review(review, review_package)

        review = passing_review(review_package)
        review["failed_checks"] = ["leakage"]
        with self.assertRaises(ValueError):
            validate_external_review(review, review_package)


if __name__ == "__main__":
    unittest.main()
