from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from psm_v0.openai_external_long_context_judge import (
    APPROVED_AUTHORIZATION,
    build_request_payload,
    review_long_context_package,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
PACKAGE_PATH = PSM_ROOT / "runtime" / "v0_273_external_long_context_review_package.json"


def package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def authorized_package() -> dict:
    value = copy.deepcopy(package())
    value["authorization"] = APPROVED_AUTHORIZATION
    value["budget"].update({
        "maximum_api_calls": 1,
        "reserved_usd": 4.0,
        "reserved_total_month_usd": 28.0,
        "monthly_limit_usd": 28.0,
    })
    return value


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
                "finding": "The synthetic final answer preserves the long-context state and release boundary.",
            }
            for item in value["review_payload"]["items"]
        ],
    }


class OpenAIExternalLongContextJudgeTests(unittest.TestCase):
    def test_prepared_package_is_synthetic_hash_locked_and_call_disabled(self) -> None:
        value = package()
        validate_review_package(value, require_authorization=False)
        self.assertEqual(value["budget"]["maximum_api_calls"], 0)
        self.assertFalse(value["privacy"]["contains_participant_content"])
        with self.assertRaises(ValueError):
            build_request_payload(value)

    def test_private_or_tampered_package_is_rejected(self) -> None:
        value = package()
        value["privacy"]["contains_private_data"] = True
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = package()
        value["review_payload"]["items"][0]["final_answer"] += " changed"
        with self.assertRaises(ValueError):
            validate_review_package(value)

    def test_authorized_shape_parses_with_fake_transport_without_secret_persistence(self) -> None:
        value = authorized_package()
        validate_review_package(value, require_authorization=True)

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "sk-test-secret")
            self.assertFalse(payload["store"])
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

        result = review_long_context_package(value, api_key="sk-test-secret", transport=transport)
        self.assertTrue(result["passed"])
        self.assertNotIn("sk-test-secret", json.dumps(result))
        self.assertFalse(result["release_boundary"]["external_release_authority"])

    def test_coverage_contradiction_and_promoted_checkpoint_fail_closed(self) -> None:
        value = authorized_package()
        review = passing_review(value)
        review["item_reviews"][0]["review_id"] = "wrong"
        with self.assertRaises(ValueError):
            validate_external_review(review, value)
        checkpoint = json.loads((PSM_ROOT / "runtime" / "v0_273_external_long_context_checkpoint.json").read_text(encoding="utf-8"))
        final_gate = json.loads((PSM_ROOT / "runtime" / "v0_273_external_long_context_gate.json").read_text(encoding="utf-8"))
        prepared = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
        self.assertFalse(checkpoint["requires_user_input"])
        self.assertTrue(checkpoint["target_promoted"])
        self.assertTrue(final_gate["passed"])
        self.assertEqual(prepared["budget"]["maximum_api_calls"], 0)
        self.assertEqual(checkpoint["additional_authorization_required_usd"], 4.0)
        self.assertEqual(checkpoint["participant_content_calls"], 0)


if __name__ == "__main__":
    unittest.main()
