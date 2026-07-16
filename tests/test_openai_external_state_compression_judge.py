from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.openai_external_state_compression_judge import (
    build_request_payload,
    review_state_compression_package,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_277_external_state_compression_review_package.json"
ROLLING_PACKAGE_PATH = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_281_external_rolling_state_review_package.json"


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
            {
                "review_id": item["review_id"],
                "verdict": "pass",
                "dimension_failures": [],
                "finding": "The synthetic final answer preserves the relevant long-horizon user state.",
            }
            for item in value["review_payload"]["items"]
        ],
    }


class OpenAIExternalStateCompressionJudgeTests(unittest.TestCase):
    def test_package_is_synthetic_hash_locked_and_authorized_by_tokens(self) -> None:
        value = package()
        validate_review_package(value)
        self.assertEqual(value["budget"]["token_authority_limit"], 1_000_000)
        self.assertFalse(value["budget"]["approval_required"])
        self.assertFalse(value["privacy"]["contains_state_capsules"])
        self.assertEqual(len(value["review_payload"]["items"]), 10)
        self.assertTrue(all(len(item["conversation"]) >= 40 for item in value["review_payload"]["items"]))

    def test_private_tampered_or_over_budget_package_is_rejected(self) -> None:
        value = package()
        value["privacy"]["contains_private_data"] = True
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = package()
        value["review_payload"]["items"][0]["final_answer"] += " changed"
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = package()
        value["budget"]["reserved_total_tokens"] = 1_000_001
        with self.assertRaises(ValueError):
            validate_review_package(value)

    def test_fake_transport_parses_without_secret_persistence(self) -> None:
        value = package()

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "sk-test-secret")
            self.assertFalse(payload["store"])
            return (
                {
                    "id": "resp_v277_test",
                    "status": "completed",
                    "model": "gpt-5.4-test",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": json.dumps(passing_review(value))}],
                        }
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                },
                {"x-request-id": "req_v277_test"},
                200,
            )

        result = review_state_compression_package(value, api_key="sk-test-secret", transport=transport)
        self.assertTrue(result["passed"])
        self.assertNotIn("sk-test-secret", json.dumps(result))
        self.assertFalse(result["release_boundary"]["external_release_authority"])

    def test_coverage_and_verdict_contradictions_fail_closed(self) -> None:
        value = package()
        request = build_request_payload(value)
        self.assertEqual(request["reasoning"]["effort"], "high")
        review = passing_review(value)
        review["item_reviews"][0]["review_id"] = "wrong"
        with self.assertRaises(ValueError):
            validate_external_review(review, value)

    def test_rolling_package_uses_four_long_synthetic_items(self) -> None:
        value = json.loads(ROLLING_PACKAGE_PATH.read_text(encoding="utf-8"))
        validate_review_package(value)
        self.assertEqual([item["review_id"] for item in value["review_payload"]["items"]], ["R01", "R02", "R03", "R04"])
        self.assertTrue(all(len(item["conversation"]) >= 160 for item in value["review_payload"]["items"]))
        request = build_request_payload(value)
        self.assertEqual(request["text"]["format"]["schema"]["properties"]["item_reviews"]["minItems"], 4)
        review = passing_review(value)
        review["item_reviews"][0]["verdict"] = "fail"
        with self.assertRaises(ValueError):
            validate_external_review(review, value)


if __name__ == "__main__":
    unittest.main()
