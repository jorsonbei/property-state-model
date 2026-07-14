from __future__ import annotations

import unittest

from psm_v0.internal_readiness_review import (
    choose_readiness_decision,
    internal_scope_boundary,
    validate_contract,
)


class InternalReadinessReviewTests(unittest.TestCase):
    def test_decision_is_blocked_when_required_artifact_is_unavailable(self) -> None:
        self.assertEqual(
            choose_readiness_decision(required_artifacts_available=False, required_checks={"core": True}),
            "blocked",
        )

    def test_decision_needs_work_when_a_required_gate_fails(self) -> None:
        self.assertEqual(
            choose_readiness_decision(required_artifacts_available=True, required_checks={"core": True, "browser": False}),
            "needs_more_work",
        )

    def test_internal_ready_never_opens_external_authority(self) -> None:
        self.assertEqual(
            choose_readiness_decision(required_artifacts_available=True, required_checks={"core": True, "browser": True}),
            "internal_trial_ready",
        )
        boundary = internal_scope_boundary()
        self.assertFalse(boundary["external_user_trial_allowed"])
        self.assertFalse(boundary["external_release_authority"])
        validate_contract(
            {
                "frozen": True,
                "allowed_decisions": ["internal_trial_ready", "needs_more_work", "blocked"],
                "required_boundaries": boundary,
            }
        )


if __name__ == "__main__":
    unittest.main()
