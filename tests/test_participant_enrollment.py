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
    build_enrollment_checkpoint,
    EnrollmentError,
    apply_enrollment_action,
    initialize_enrollment,
    load_private_state,
    operator_invitation_cards,
    public_enrollment_status,
    record_prompt_audit,
    stop_enrollment,
    validate_trial_access,
    write_private_state,
    write_public_checkpoint,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"


class ParticipantEnrollmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load_protocol(PROTOCOL_PATH)
        cls.codes = ["invite-code-p01-safe", "invite-code-p02-safe", "invite-code-p03-safe"]
        cls.prepared_at = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)

    def new_state(self) -> dict:
        return initialize_enrollment(
            participant_count=3,
            protocol=self.protocol,
            binding_secret=b"b" * 32,
            prepared_at=self.prepared_at,
            invitation_codes=list(self.codes),
        )

    def apply(self, state: dict, participant_id: str, action: str, offset: int) -> dict:
        index = int(participant_id[-2:]) - 1
        return apply_enrollment_action(
            state,
            participant_id=participant_id,
            invitation_code=self.codes[index],
            action=action,
            attestation=ACTION_ATTESTATIONS[action],
            protocol=self.protocol,
            occurred_at=self.prepared_at + timedelta(minutes=offset),
        )

    def complete_participant(self, state: dict, participant_id: str, start: int) -> dict:
        for offset, action in enumerate(
            ("verify_adult", "display_notice", "acknowledge_notice", "consent", "enable_session"),
            start=start,
        ):
            state = self.apply(state, participant_id, action, offset)
        return state

    def test_three_unique_private_invitations_have_no_identity_fields(self) -> None:
        state = self.new_state()
        self.assertEqual(state["participant_count"], 3)
        self.assertEqual([item["participant_id"] for item in state["participants"]], ["P01", "P02", "P03"])
        self.assertEqual(len({item["invitation_sha256"] for item in state["participants"]}), 3)
        self.assertEqual(len({item["invitee_binding_hmac_sha256"] for item in state["participants"]}), 3)
        serialized = json.dumps(state)
        for key in ("full_name", "email", "phone", "identity_document", "date_of_birth"):
            self.assertNotIn(key, serialized)
        self.assertFalse(state["trial_active"])

    def test_public_status_redacts_codes_hashes_and_audit_secret(self) -> None:
        state = self.new_state()
        public = public_enrollment_status(state)
        serialized = json.dumps(public)
        self.assertNotIn("invitation_code", serialized)
        self.assertNotIn("invitation_sha256", serialized)
        self.assertNotIn("invitee_binding_hmac_sha256", serialized)
        self.assertNotIn("audit_secret", serialized)
        self.assertEqual(public["counts"]["invited"], 3)
        cards = operator_invitation_cards(state)
        self.assertTrue(cards["private_local_operator_view"])
        self.assertEqual(cards["participants"][0]["invitation_code"], self.codes[0])

    def test_public_checkpoint_tracks_human_gate_without_private_material(self) -> None:
        state = self.new_state()
        checkpoint = build_enrollment_checkpoint(state)
        self.assertTrue(checkpoint["requires_user_input"])
        self.assertEqual(checkpoint["adult_verified"], 0)
        self.assertFalse(checkpoint["trial_active"])
        for index, participant_id in enumerate(("P01", "P02", "P03")):
            state = self.complete_participant(state, participant_id, 1 + index * 10)
        checkpoint = build_enrollment_checkpoint(state)
        self.assertFalse(checkpoint["requires_user_input"])
        self.assertEqual(checkpoint["session_enabled"], 3)
        self.assertTrue(checkpoint["trial_active"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            write_public_checkpoint(path, state)
            serialized = path.read_text(encoding="utf-8")
        for value in (
            self.codes[0],
            state["participants"][0]["invitation_sha256"],
            state["audit_secret_hex"],
        ):
            self.assertNotIn(value, serialized)

    def test_wrong_code_missing_attestation_and_out_of_order_actions_fail(self) -> None:
        state = self.new_state()
        with self.assertRaises(EnrollmentError):
            apply_enrollment_action(
                state,
                participant_id="P01",
                invitation_code="wrong-invitation-code",
                action="verify_adult",
                attestation=ACTION_ATTESTATIONS["verify_adult"],
                protocol=self.protocol,
            )
        with self.assertRaises(EnrollmentError):
            apply_enrollment_action(
                state,
                participant_id="P01",
                invitation_code=self.codes[0],
                action="verify_adult",
                attestation="self_asserted_adult",
                protocol=self.protocol,
            )
        with self.assertRaises(EnrollmentError):
            self.apply(state, "P01", "consent", 1)

    def test_all_three_must_complete_strict_sequence_before_trial_access(self) -> None:
        state = self.new_state()
        state = self.complete_participant(state, "P01", 1)
        state = self.complete_participant(state, "P02", 10)
        self.assertFalse(state["trial_active"])
        self.assertIn("cohort gate", validate_trial_access(
            state,
            participant_id="P01",
            invitation_code=self.codes[0],
            protocol=self.protocol,
        )[0])
        state = self.complete_participant(state, "P03", 20)
        self.assertTrue(state["trial_active"])
        self.assertTrue(state["trial_start_gate"]["passed"])
        self.assertEqual(validate_trial_access(
            state,
            participant_id="P02",
            invitation_code=self.codes[1],
            protocol=self.protocol,
        ), [])

    def test_revocation_stops_trial_without_automatic_resume(self) -> None:
        state = self.new_state()
        for index, participant_id in enumerate(("P01", "P02", "P03")):
            state = self.complete_participant(state, participant_id, 1 + index * 10)
        state = self.apply(state, "P02", "revoke", 40)
        self.assertTrue(state["stopped"])
        self.assertFalse(state["trial_active"])
        self.assertIn("trial is stopped", validate_trial_access(
            state,
            participant_id="P01",
            invitation_code=self.codes[0],
            protocol=self.protocol,
        ))

    def test_revocation_deletes_participant_audit_events(self) -> None:
        state = self.new_state()
        state = record_prompt_audit(
            state,
            participant_id="P02",
            prompt="低风险一般问题",
            decision=inspect_prompt("低风险一般问题", self.protocol),
            latency_ms=10,
            token_count=4,
            occurred_at=self.prepared_at,
            event_id="trial-withdrawal-delete",
        )
        state = self.apply(state, "P02", "revoke", 1)
        self.assertEqual(state["audit_events"], [])
        self.assertTrue(state["stopped"])

    def test_protocol_stop_is_fail_closed_and_cannot_auto_resume(self) -> None:
        state = stop_enrollment(
            self.new_state(),
            reason="prohibited_or_unknown_data_detected",
            protocol=self.protocol,
        )
        self.assertTrue(state["stopped"])
        self.assertFalse(state["trial_active"])
        self.assertEqual(state["stop_reasons"], ["prohibited_or_unknown_data_detected"])
        with self.assertRaises(EnrollmentError):
            self.apply(state, "P01", "verify_adult", 1)

    def test_private_state_is_written_with_owner_only_permissions(self) -> None:
        state = self.new_state()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "enrollment.json"
            write_private_state(path, state, self.protocol)
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)
            self.assertEqual(load_private_state(path, self.protocol), state)

    def test_content_free_audit_retains_no_prompt_or_answer(self) -> None:
        state = self.new_state()
        prompt = "为什么天空看起来是蓝色？"
        decision = inspect_prompt(prompt, self.protocol)
        state = record_prompt_audit(
            state,
            participant_id="P01",
            prompt=prompt,
            decision=decision,
            latency_ms=120,
            token_count=30,
            occurred_at=self.prepared_at,
            event_id="trial-test-1",
        )
        event = state["audit_events"][0]
        serialized = json.dumps(event, ensure_ascii=False)
        self.assertNotIn(prompt, serialized)
        self.assertNotIn("answer", serialized)
        self.assertFalse(event["raw_prompt_persisted"])
        self.assertFalse(event["participant_content_sent_to_external_api"])


if __name__ == "__main__":
    unittest.main()
