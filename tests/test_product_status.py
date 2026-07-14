from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from product_alpha_app.server import load_status_summary, status_version


class ProductStatusTests(unittest.TestCase):
    def test_status_version_is_numeric(self) -> None:
        self.assertEqual(status_version(Path("psm_v0.247_project_status.json")), 247)
        self.assertEqual(status_version(Path("not-a-status.json")), -1)

    def test_latest_status_is_exposed(self) -> None:
        status = load_status_summary()
        self.assertTrue(status["version"].startswith("PSM V0."))
        self.assertGreater(status["core_cases"], 0)
        self.assertFalse(status["ready_for_external_user_trial"])
        self.assertEqual(status["selected_chat_model"], "qwen3.5:9b")
        self.assertEqual(status["chat_timeout_seconds"], 60)


if __name__ == "__main__":
    unittest.main()
