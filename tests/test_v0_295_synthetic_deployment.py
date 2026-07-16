from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class SyntheticDeploymentV295Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_295_synthetic_deployment_contract.json").read_text(
                encoding="utf-8"
            )
        )
        cls.index = (PSM_ROOT / "product_alpha_app" / "static" / "index.html").read_text(
            encoding="utf-8"
        )
        cls.server = (PSM_ROOT / "product_alpha_app" / "server.py").read_text(encoding="utf-8")
        cls.dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        cls.compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        cls.workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    def test_human_participant_workflow_is_explicitly_retired(self) -> None:
        boundary = self.contract["human_boundary"]
        self.assertEqual(boundary["human_participants"], 0)
        self.assertFalse(boundary["participant_recruitment_enabled"])
        self.assertFalse(boundary["adult_verification_enabled"])
        self.assertFalse(boundary["participant_consent_workflow_enabled"])
        self.assertFalse(boundary["real_user_satisfaction_claimed"])

    def test_active_chat_has_no_enrollment_entry_and_routes_are_gone(self) -> None:
        self.assertNotIn('id="enrollment-link"', self.index)
        self.assertNotIn('href="/trial-enrollment"', self.index)
        self.assertIn("RETIRED_TRIAL_API_PATHS", self.server)
        self.assertIn("RETIRED_TRIAL_STATIC_PATHS", self.server)
        self.assertIn('"human_trial_workflow_retired"', self.server)
        self.assertIn("status=410", self.server)

    def test_container_uses_content_free_health_and_excludes_invite_notice(self) -> None:
        self.assertIn("USER psm", self.dockerfile)
        self.assertIn("/api/health", self.dockerfile)
        self.assertNotIn("COPY --chown=psm:psm outputs/psm_v0/V0_262", self.dockerfile)
        self.assertIn('${PSM_DOCKER_BIND:-127.0.0.1}', self.compose)

    def test_ci_requires_no_secret_or_external_model_call(self) -> None:
        self.assertIn("make check", self.workflow)
        self.assertIn("docker build", self.workflow)
        self.assertIn("/api/health", self.workflow)
        self.assertIn("id -u", self.workflow)
        for forbidden in ("OPENAI_API_KEY", "secrets.", "api.openai.com"):
            self.assertNotIn(forbidden, self.workflow)

    def test_release_authority_remains_closed(self) -> None:
        boundary = self.contract["release_boundary"]
        self.assertTrue(boundary["synthetic_only"])
        self.assertFalse(boundary["human_validation_claimed"])
        self.assertFalse(boundary["public_service_allowed"])
        self.assertFalse(boundary["external_network_deployment_allowed"])
        self.assertFalse(boundary["external_release_authority"])


if __name__ == "__main__":
    unittest.main()
