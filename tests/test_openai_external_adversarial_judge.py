from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.openai_external_adversarial_judge import (
    build_request_payload,
    review_adversarial_package,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_267_external_adversarial_review_package.json"


def package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def passing_review(value: dict) -> dict:
    return {
        "review_payload_sha256": value["review_payload_sha256"],
        "verdict": "pass",
        "failed_pair_ids": [],
        "critical_findings": [],
        "recommended_repairs": [],
        "pair_reviews": [
            {
                "review_id": pair["review_id"],
                "verdict": "pass",
                "dimension_failures": [],
                "finding": "Both synthetic variants preserve the relevant semantic and release boundary.",
            }
            for pair in value["review_payload"]["pairs"]
        ],
    }


class OpenAIExternalAdversarialJudgeTests(unittest.TestCase):
    def test_checked_in_package_is_synthetic_authorized_and_hash_locked(self) -> None:
        validate_review_package(package())

    def test_private_candidate_or_tampered_package_is_rejected(self) -> None:
        value = package()
        value["privacy"]["contains_private_data"] = True
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = package()
        value["review_payload"]["pairs"][0]["variants"][0]["answer"] += " changed"
        with self.assertRaises(ValueError):
            build_request_payload(value)
        value = package()
        value["review_payload"]["pairs"][0]["variants"][0]["answer"] = "/Users/private/file"
        value["review_payload_sha256"] = __import__("hashlib").sha256(
            json.dumps(value["review_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.assertRaises(ValueError):
            validate_review_package(value)

    def test_review_parses_without_persisting_secret(self) -> None:
        value = package()

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "sk-test-secret")
            self.assertFalse(payload["store"])
            self.assertNotIn("expected_markers", payload["input"])
            self.assertIn(value["review_payload_sha256"], payload["input"])
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

        result = review_adversarial_package(value, api_key="sk-test-secret", transport=transport)
        self.assertTrue(result["passed"])
        self.assertNotIn("sk-test-secret", json.dumps(result))
        self.assertFalse(result["release_boundary"]["training_feedback_written"])
        self.assertFalse(result["release_boundary"]["external_release_authority"])

    def test_pair_coverage_and_verdict_contradictions_fail_closed(self) -> None:
        value = package()
        review = passing_review(value)
        review["pair_reviews"][0]["review_id"] = "wrong"
        with self.assertRaises(ValueError):
            validate_external_review(review, value)
        review = passing_review(value)
        review["pair_reviews"][0]["verdict"] = "fail"
        review["pair_reviews"][0]["dimension_failures"] = ["semantic_correctness"]
        with self.assertRaises(ValueError):
            validate_external_review(review, value)


if __name__ == "__main__":
    unittest.main()
