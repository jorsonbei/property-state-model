from __future__ import annotations

import json
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psm_v0.external_trial_protocol import inspect_prompt, load_protocol
from psm_v0.participant_enrollment import (
    ACTION_ATTESTATIONS,
    apply_enrollment_action,
    initialize_enrollment,
    record_prompt_audit,
)
from psm_v0.participant_feedback import (
    FEEDBACK_ELIGIBLE_NOT_BEFORE,
    FeedbackError,
    delete_participant_feedback,
    feedback_token_for_event,
    initialize_feedback_state,
    load_feedback_state,
    public_feedback_progress,
    submit_feedback,
    validate_feedback_state,
    write_feedback_state,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"


class ParticipantFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load_protocol(PROTOCOL_PATH)
        cls.codes = ["feedback-code-p01", "feedback-code-p02", "feedback-code-p03"]
        cls.started = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)

    def eligible_enrollment(self, participant_id: str = "P01", event_id: str = "trial-feedback-1") -> dict:
        state = initialize_enrollment(
            participant_count=3,
            protocol=self.protocol,
            binding_secret=b"f" * 32,
            prepared_at=self.started,
            invitation_codes=list(self.codes),
        )
        minute = 1
        for current_id, code in zip(("P01", "P02", "P03"), self.codes, strict=True):
            for action in ("verify_adult", "display_notice", "acknowledge_notice", "consent", "enable_session"):
                state = apply_enrollment_action(
                    state,
                    participant_id=current_id,
                    invitation_code=code,
                    action=action,
                    attestation=ACTION_ATTESTATIONS[action],
                    protocol=self.protocol,
                    occurred_at=self.started + timedelta(minutes=minute),
                )
                minute += 1
        return record_prompt_audit(
            state,
            participant_id=participant_id,
            prompt="一个不含私人资料的普通问题",
            decision=inspect_prompt("为什么天空是蓝色？", self.protocol),
            latency_ms=12,
            token_count=8,
            occurred_at=datetime.fromisoformat(FEEDBACK_ELIGIBLE_NOT_BEFORE) + timedelta(minutes=1),
            event_id=event_id,
        )

    def test_feedback_token_is_bound_to_one_eligible_turn(self) -> None:
        enrollment = self.eligible_enrollment()
        token = feedback_token_for_event(enrollment, "trial-feedback-1")
        updated = submit_feedback(
            initialize_feedback_state(),
            enrollment_state=enrollment,
            participant_id="P01",
            feedback_token=token,
            helpfulness=5,
            clarity=4,
            state_alignment="yes",
            issue_category="none",
            submitted_at=self.started + timedelta(hours=2),
        )
        self.assertEqual(validate_feedback_state(updated), [])
        self.assertEqual(public_feedback_progress(updated)["participants"][0]["credited"], 1)
        serialized = json.dumps(updated, ensure_ascii=False)
        self.assertNotIn("一个不含私人资料", serialized)
        self.assertNotIn('"answer":', serialized)
        self.assertIn('"free_text_collected": false', serialized)
        with self.assertRaisesRegex(FeedbackError, "already been submitted"):
            submit_feedback(
                updated,
                enrollment_state=enrollment,
                participant_id="P01",
                feedback_token=token,
                helpfulness=5,
                clarity=4,
                state_alignment="yes",
                issue_category="none",
                submitted_at=self.started + timedelta(hours=3),
            )

    def test_invalid_fixed_fields_and_wrong_participant_fail_closed(self) -> None:
        enrollment = self.eligible_enrollment()
        token = feedback_token_for_event(enrollment, "trial-feedback-1")
        base = dict(
            feedback_state=initialize_feedback_state(),
            enrollment_state=enrollment,
            participant_id="P01",
            feedback_token=token,
            helpfulness=4,
            clarity=4,
            state_alignment="partial",
            issue_category="none",
        )
        for key, value in (("helpfulness", True), ("clarity", 6), ("state_alignment", "maybe"), ("issue_category", "other")):
            with self.subTest(key=key), self.assertRaises(FeedbackError):
                submit_feedback(**{**base, key: value})
        with self.assertRaisesRegex(FeedbackError, "not bound"):
            submit_feedback(**{**base, "participant_id": "P02"})

    def test_pre_v0_265_turn_cannot_receive_feedback(self) -> None:
        enrollment = self.eligible_enrollment()
        enrollment["audit_events"][0]["occurred_at"] = "2026-07-15T10:30:59+00:00"
        token = feedback_token_for_event(enrollment, "trial-feedback-1")
        with self.assertRaisesRegex(FeedbackError, "not bound"):
            submit_feedback(
                initialize_feedback_state(),
                enrollment_state=enrollment,
                participant_id="P01",
                feedback_token=token,
                helpfulness=5,
                clarity=5,
                state_alignment="yes",
                issue_category="none",
            )

    def test_retention_withdrawal_and_private_file_mode(self) -> None:
        enrollment = self.eligible_enrollment()
        token = feedback_token_for_event(enrollment, "trial-feedback-1")
        state = submit_feedback(
            initialize_feedback_state(),
            enrollment_state=enrollment,
            participant_id="P01",
            feedback_token=token,
            helpfulness=4,
            clarity=4,
            state_alignment="partial",
            issue_category="too_verbose",
            submitted_at=self.started + timedelta(hours=2),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "feedback.json"
            write_feedback_state(path, state)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(len(load_feedback_state(path)["feedback_events"]), 1)
            stale = json.loads(json.dumps(state))
            stale["feedback_events"][0]["submitted_at"] = "2020-01-01T00:00:00+00:00"
            write_feedback_state(path, stale)
            self.assertEqual(load_feedback_state(path)["feedback_events"], [])
            self.assertNotIn(token, path.read_text(encoding="utf-8"))
        withdrawn = delete_participant_feedback(state, "P01")
        self.assertEqual(withdrawn["feedback_events"], [])
        expired = submit_feedback(
            state,
            enrollment_state=self.eligible_enrollment(event_id="trial-feedback-2"),
            participant_id="P01",
            feedback_token=feedback_token_for_event(
                self.eligible_enrollment(event_id="trial-feedback-2"),
                "trial-feedback-2",
            ),
            helpfulness=5,
            clarity=5,
            state_alignment="yes",
            issue_category="none",
            submitted_at=self.started + timedelta(days=8),
        )
        self.assertEqual(len(expired["feedback_events"]), 1)


if __name__ == "__main__":
    unittest.main()
