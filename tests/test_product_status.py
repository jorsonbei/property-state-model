from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from product_alpha_app.server import load_status_summary, load_trial_notice, status_version


class ProductStatusTests(unittest.TestCase):
    def test_status_version_is_numeric(self) -> None:
        self.assertEqual(status_version(Path("psm_v0.247_project_status.json")), 247)
        self.assertEqual(status_version(Path("not-a-status.json")), -1)

    def test_latest_status_is_exposed(self) -> None:
        status = load_status_summary()
        self.assertTrue(status["version"].startswith("PSM V0."))
        self.assertGreater(status["core_cases"], 0)
        self.assertFalse(status["ready_for_external_user_trial"])
        self.assertTrue(status["ready_for_stable_internal_chat"])
        self.assertEqual(status["internal_trial_decision"], "internal_trial_ready")
        self.assertEqual(status["selected_chat_model"], "qwen3.5:9b")
        self.assertEqual(status["chat_timeout_seconds"], 60)

    def test_v0_262_notice_is_explicitly_inactive(self) -> None:
        notice = load_trial_notice()
        self.assertEqual(notice["version"], "PSM V0.262")
        self.assertIn("3 至 5", notice["content"])
        self.assertFalse(notice["participant_enrollment_completed"])
        self.assertFalse(notice["trial_active"])
        self.assertFalse(notice["public_service_allowed"])


if __name__ == "__main__":
    unittest.main()
