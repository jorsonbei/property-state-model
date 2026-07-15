from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.openai_external_trial_protocol_judge import (
    build_request_payload,
    review_protocol,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_262_external_trial_protocol_review_package.json"


def package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def passing_review(value: dict) -> dict:
    return {
        "protocol_sha256": value["protocol_sha256"],
        "verdict": "pass",
        "failed_checks": [],
        "critical_findings": [],
        "recommended_repairs": [],
        "question_reviews": [
            {"question": question, "verdict": "pass", "finding": "Boundary is explicit and fail closed."}
            for question in value["independent_review_questions"]
        ],
    }


class OpenAIExternalTrialProtocolJudgeTests(unittest.TestCase):
    def test_checked_in_package_is_synthetic_authorized_and_hash_locked(self) -> None:
        validate_review_package(package())

    def test_private_or_tampered_package_is_rejected(self) -> None:
        value = package()
        value["privacy"]["contains_participant_content"] = True
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = package()
        value["protocol"]["deployment"]["public_internet_exposure"] = True
        with self.assertRaises(ValueError):
            build_request_payload(value)

    def test_review_parses_without_persisting_secret(self) -> None:
        value = package()

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "sk-test-secret")
            self.assertFalse(payload["store"])
            return (
                {
                    "id": "resp_test", "status": "completed", "model": "gpt-5.4-test",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(passing_review(value))}]}],
                    "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                },
                {"x-request-id": "req_test"},
                200,
            )

        result = review_protocol(value, api_key="sk-test-secret", transport=transport)
        self.assertTrue(result["passed"])
        self.assertNotIn("sk-test-secret", json.dumps(result))
        self.assertFalse(result["release_boundary"]["participant_content_submitted"])

    def test_question_coverage_and_verdict_contradictions_fail_closed(self) -> None:
        value = package()
        review = passing_review(value)
        review["question_reviews"][0]["question"] = "paraphrased"
        with self.assertRaises(ValueError):
            validate_external_review(review, value)
        review = passing_review(value)
        review["critical_findings"] = ["critical gap"]
        with self.assertRaises(ValueError):
            validate_external_review(review, value)


if __name__ == "__main__":
    unittest.main()
