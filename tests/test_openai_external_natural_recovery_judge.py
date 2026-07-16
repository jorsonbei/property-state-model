from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from psm_v0.openai_external_natural_recovery_judge import (
    build_request_payload,
    review_natural_recovery_package,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_287_external_natural_recovery_review_package.json"


class OpenAIExternalNaturalRecoveryJudgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    def test_package_is_synthetic_hash_locked_and_authorized(self) -> None:
        validate_review_package(self.package)
        self.assertEqual(len(self.package["review_payload"]["items"]), 16)
        self.assertFalse(self.package["budget"]["approval_required"])
        self.assertFalse(self.package["privacy"]["contains_private_data"])

    def test_private_tampered_or_over_budget_package_is_rejected(self) -> None:
        for mutate in (
            lambda value: value["privacy"].__setitem__("contains_private_data", True),
            lambda value: value["review_payload"]["items"][0].__setitem__("final_answer", "tampered"),
            lambda value: value["budget"].__setitem__("reserved_total_tokens", 1_000_001),
        ):
            candidate = copy.deepcopy(self.package)
            mutate(candidate)
            with self.assertRaises(ValueError):
                validate_review_package(candidate)

    def test_fake_transport_parses_without_secret_persistence(self) -> None:
        review = {
            "review_payload_sha256": self.package["review_payload_sha256"],
            "verdict": "pass",
            "failed_item_ids": [],
            "critical_findings": [],
            "recommended_repairs": [],
            "item_reviews": [
                {"review_id": f"N{index:02d}", "verdict": "pass", "dimension_failures": [], "finding": "Pass."}
                for index in range(1, 17)
            ],
        }

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertNotIn(api_key, json.dumps(payload))
            return (
                {
                    "id": "resp_test",
                    "status": "completed",
                    "model": "test-model",
                    "output": [{"content": [{"type": "output_text", "text": json.dumps(review)}]}],
                    "usage": {"total_tokens": 100},
                },
                {"x-request-id": "req_test"},
                200,
            )

        result = review_natural_recovery_package(self.package, api_key="secret-test-key", transport=transport)
        self.assertTrue(result["passed"])
        self.assertNotIn("secret-test-key", json.dumps(result))

    def test_request_uses_strict_schema_and_store_false(self) -> None:
        payload = build_request_payload(self.package)
        self.assertFalse(payload["store"])
        self.assertTrue(payload["text"]["format"]["strict"])


if __name__ == "__main__":
    unittest.main()
