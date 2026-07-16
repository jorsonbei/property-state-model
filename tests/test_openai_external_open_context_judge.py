from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from psm_v0.openai_external_open_context_judge import (
    APPROVED_AUTHORIZATION,
    build_markdown_report,
    build_request_payload,
    review_open_context_package,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
PACKAGE_PATH = PSM_ROOT / "runtime" / "v0_275_external_open_context_review_package.json"


def prepared_package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def authorized_package() -> dict:
    value = prepared_package()
    value["authorization"] = APPROVED_AUTHORIZATION
    value["budget"].update({
        "maximum_api_calls": 1,
        "reserved_usd": 4.0,
        "reserved_total_month_usd": 32.0,
        "monthly_limit_usd": 32.0,
    })
    return value


class OpenAIExternalOpenContextJudgeTests(unittest.TestCase):
    def test_checked_in_package_is_prepared_hash_locked_and_private_free(self) -> None:
        value = prepared_package()
        validate_review_package(value, require_authorization=False)
        self.assertEqual(value["budget"]["maximum_api_calls"], 0)
        self.assertEqual(len(value["review_payload"]["items"]), 10)
        self.assertEqual(len({item["family"] for item in value["review_payload"]["items"]}), 5)
        self.assertTrue(all(len(item["conversation"]) >= 11 for item in value["review_payload"]["items"]))

    def test_prepared_package_cannot_build_external_request(self) -> None:
        with self.assertRaises(ValueError):
            build_request_payload(prepared_package())

    def test_authorized_shape_parses_with_fake_transport(self) -> None:
        value = authorized_package()
        validate_review_package(value, require_authorization=True)
        ids = [item["review_id"] for item in value["review_payload"]["items"]]
        review = {
            "review_payload_sha256": value["review_payload_sha256"],
            "verdict": "pass",
            "failed_item_ids": [],
            "critical_findings": [],
            "recommended_repairs": [],
            "item_reviews": [
                {"review_id": item_id, "verdict": "pass", "dimension_failures": [], "finding": "pass"}
                for item_id in ids
            ],
        }

        def transport(payload: dict, api_key: str, endpoint: str, timeout: float):
            self.assertEqual(api_key, "test-only")
            return ({
                "id": "resp_test",
                "model": "gpt-test",
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(review)}]}],
                "usage": {"total_tokens": 10},
            }, {"x-request-id": "req_test"}, 200)

        result = review_open_context_package(value, api_key="test-only", transport=transport)
        self.assertTrue(result["passed"])
        self.assertFalse(result["api_key_persisted_in_artifact"])
        self.assertFalse(result["release_boundary"]["public_service_allowed"])

    def test_privacy_hash_and_budget_mutations_fail_closed(self) -> None:
        value = prepared_package()
        value["privacy"]["contains_user_documents"] = True
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = prepared_package()
        value["review_payload"]["items"][0]["final_answer"] += " changed"
        with self.assertRaises(ValueError):
            validate_review_package(value)
        value = authorized_package()
        value["budget"]["monthly_limit_usd"] = 36.0
        with self.assertRaises(ValueError):
            validate_review_package(value, require_authorization=True)

    def test_external_failure_and_local_repairs_are_distinct_states(self) -> None:
        judge_path = PSM_ROOT / "runtime" / "v0_275_openai_external_open_context_judge.json"
        repair_path = PSM_ROOT / "runtime" / "v0_275_external_open_context_repair_report.json"
        gate_path = PSM_ROOT / "runtime" / "v0_275_external_open_context_repair_gate.json"
        if not judge_path.exists() or not repair_path.exists() or not gate_path.exists():
            self.skipTest("V0.275 external result and local repair artifacts are not built yet.")
        judge = json.loads(judge_path.read_text(encoding="utf-8"))
        repair = json.loads(repair_path.read_text(encoding="utf-8"))
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        self.assertFalse(judge["passed"])
        self.assertEqual(judge["review"]["failed_item_ids"], ["O01", "O02", "O10"])
        markdown = build_markdown_report(judge)
        self.assertIn(judge["review"]["review_payload_sha256"], markdown)
        self.assertTrue(repair["passed"])
        self.assertEqual(repair["failed_items_repaired_locally"], ["O01", "O02", "O10"])
        self.assertFalse(repair["external_rejudge_completed"])
        self.assertTrue(gate["passed"])
        self.assertFalse(gate["external_rejudge_completed"])


if __name__ == "__main__":
    unittest.main()
