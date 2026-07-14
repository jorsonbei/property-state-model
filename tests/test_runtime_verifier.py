from __future__ import annotations

import unittest
import json
from pathlib import Path

from psm_v0.runtime_verifier import verify_runtime


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class RuntimeVerifierTests(unittest.TestCase):
    def test_public_runtime_snapshot_and_core_routes_pass(self) -> None:
        report = verify_runtime(PSM_ROOT)
        snapshot = json.loads(
            (PSM_ROOT / "runtime" / "current_runtime_snapshot.json").read_text(encoding="utf-8")
        )

        self.assertGreater(report["python_sources_parsed"], 0)
        self.assertEqual(report["current_version"], snapshot["project_status"]["current_version"])
        self.assertTrue(report["regression_passed"])
        self.assertTrue(report["high_risk_external_judge_retained"])


if __name__ == "__main__":
    unittest.main()
