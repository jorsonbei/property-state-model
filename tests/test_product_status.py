from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_alpha_app import server
from product_alpha_app.server import load_status_summary, load_trial_notice, status_version


class ProductStatusTests(unittest.TestCase):
    def test_status_version_is_numeric(self) -> None:
        self.assertEqual(status_version(Path("psm_v0.247_project_status.json")), 247)
        self.assertEqual(status_version(Path("not-a-status.json")), -1)

    def test_latest_status_is_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            server,
            "ENROLLMENT_STATE_PATH",
            Path(directory) / "missing-enrollment.json",
        ):
            status = load_status_summary()
        self.assertTrue(status["version"].startswith("PSM V0."))
        self.assertGreater(status["core_cases"], 0)
        self.assertFalse(status["ready_for_external_user_trial"])
        self.assertTrue(status["ready_for_stable_internal_chat"])
        self.assertEqual(status["internal_trial_decision"], "internal_trial_ready")
        self.assertEqual(status["selected_chat_model"], "qwen3.5:9b")
        self.assertEqual(status["chat_timeout_seconds"], 60)
        self.assertEqual(status["chat_concurrency_limit"], 4)
        self.assertFalse(status["chat_queue_enabled"])
        self.assertFalse(status["human_participant_workflow_enabled"])
        self.assertTrue(status["synthetic_validation_only"])
        self.assertFalse(status["ready_for_invite_only_external_trial_protocol"])
        self.assertFalse(status["external_trial_participant_enrollment_completed"])
        self.assertEqual(status["external_trial_participant_minimum"], 0)
        self.assertEqual(status["external_trial_participant_maximum"], 0)
        self.assertEqual(status["external_trial_monthly_api_budget_usd"], 0.0)
        self.assertEqual(status["v0_263_selected_participant_count"], 3)
        self.assertEqual(status["v0_263_pseudonymous_invitations_generated"], 3)
        self.assertFalse(status["v0_263_enrollment_interface_ready"])
        self.assertFalse(status["ready_for_supervised_invite_only_trial"])

    def test_v0_262_notice_is_inactive_without_private_enrollment(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            server,
            "ENROLLMENT_STATE_PATH",
            Path(directory) / "missing-enrollment.json",
        ):
            notice = load_trial_notice()
        self.assertEqual(notice["version"], "PSM V0.262")
        self.assertIn("3 至 5", notice["content"])
        self.assertFalse(notice["participant_enrollment_completed"])
        self.assertFalse(notice["trial_active"])
        self.assertFalse(notice["public_service_allowed"])


if __name__ == "__main__":
    unittest.main()
