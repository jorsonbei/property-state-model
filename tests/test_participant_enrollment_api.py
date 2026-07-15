from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from product_alpha_app import server
from psm_v0.external_trial_protocol import load_protocol
from psm_v0.participant_enrollment import (
    ACTION_ATTESTATIONS,
    apply_enrollment_action,
    initialize_enrollment,
    load_private_state,
    write_private_state,
)
from psm_v0.participant_feedback import load_feedback_state


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"


class ParticipantEnrollmentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = load_protocol(PROTOCOL_PATH)
        self.codes = ["api-invite-p01-safe", "api-invite-p02-safe", "api-invite-p03-safe"]
        self.started = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "private" / "enrollment.json"
        self.checkpoint_path = Path(self.directory.name) / "runtime" / "checkpoint.json"
        self.feedback_path = Path(self.directory.name) / "private" / "feedback.json"
        self.original_path = server.ENROLLMENT_STATE_PATH
        self.original_checkpoint_path = server.ENROLLMENT_CHECKPOINT_PATH
        self.original_feedback_path = server.FEEDBACK_STATE_PATH
        server.ENROLLMENT_STATE_PATH = self.path
        server.ENROLLMENT_CHECKPOINT_PATH = self.checkpoint_path
        server.FEEDBACK_STATE_PATH = self.feedback_path
        state = initialize_enrollment(
            participant_count=3,
            protocol=self.protocol,
            binding_secret=b"a" * 32,
            prepared_at=self.started,
            invitation_codes=list(self.codes),
        )
        write_private_state(self.path, state, self.protocol)

    def tearDown(self) -> None:
        server.ENROLLMENT_STATE_PATH = self.original_path
        server.ENROLLMENT_CHECKPOINT_PATH = self.original_checkpoint_path
        server.FEEDBACK_STATE_PATH = self.original_feedback_path
        self.directory.cleanup()

    def complete_state(self) -> None:
        state = load_private_state(self.path, self.protocol)
        minute = 1
        for participant_id, code in zip(("P01", "P02", "P03"), self.codes, strict=True):
            for action in ("verify_adult", "display_notice", "acknowledge_notice", "consent", "enable_session"):
                state = apply_enrollment_action(
                    state,
                    participant_id=participant_id,
                    invitation_code=code,
                    action=action,
                    attestation=ACTION_ATTESTATIONS[action],
                    protocol=self.protocol,
                    occurred_at=self.started + timedelta(minutes=minute),
                )
                minute += 1
        write_private_state(self.path, state, self.protocol)

    def test_public_api_status_is_redacted_and_inactive(self) -> None:
        status = server.load_enrollment_api_status()
        serialized = json.dumps(status)
        self.assertEqual(status["participant_count"], 3)
        self.assertFalse(status["trial_active"])
        self.assertFalse(status["participant_content_external_api_allowed"])
        self.assertFalse(status["raw_prompt_server_persistence"])
        self.assertNotIn("invitation_code", serialized)
        self.assertNotIn("audit_secret", serialized)

    def test_enrollment_action_requires_closed_payload_and_correct_sequence(self) -> None:
        with self.assertRaisesRegex(ValueError, "fields are not closed"):
            server.handle_enrollment_action(
                {
                    "participant_id": "P01",
                    "invitation_code": self.codes[0],
                    "action": "verify_adult",
                    "attestation": ACTION_ATTESTATIONS["verify_adult"],
                    "name": "must-not-be-accepted",
                }
            )
        result = server.handle_enrollment_action(
            {
                "participant_id": "P01",
                "invitation_code": self.codes[0],
                "action": "verify_adult",
                "attestation": ACTION_ATTESTATIONS["verify_adult"],
            }
        )
        self.assertEqual(result["participants"][0]["current_step"], "display_notice")
        self.assertFalse(result["trial_active"])

    def test_trial_chat_rejects_before_model_when_three_person_gate_is_incomplete(self) -> None:
        payload = {
            "participant_id": "P01",
            "invitation_code": self.codes[0],
            "messages": [{"role": "user", "content": "为什么天空是蓝色？"}],
        }
        with patch.object(server, "run_chat_turn") as generate:
            with self.assertRaisesRegex(ValueError, "cohort gate"):
                server.run_trial_chat_turn(payload)
        generate.assert_not_called()

    def test_active_trial_returns_slim_response_and_content_free_audit(self) -> None:
        self.complete_state()
        prompt = "为什么天空是蓝色？"
        payload = {
            "participant_id": "P01",
            "invitation_code": self.codes[0],
            "messages": [{"role": "user", "content": prompt}],
            "scenario": "review",
        }
        generated = {
            "chat": {
                "assistant_message": "阳光散射时，短波长的蓝光更容易进入视线。",
                "generation": {"provider": "deterministic"},
            },
            "packet": {"must_not_reach_participant": True},
            "sigma_plus_delivery": {"must_not_reach_participant": True},
        }
        with patch.object(server, "run_chat_turn", return_value=generated):
            result = server.run_trial_chat_turn(payload)
        self.assertEqual(set(result), {"schema_version", "chat", "trial_session"})
        self.assertNotIn("packet", result)
        self.assertNotIn("sigma_plus_delivery", result)
        self.assertFalse(result["trial_session"]["raw_prompt_persisted"])
        self.assertFalse(result["trial_session"]["participant_content_sent_to_external_api"])
        self.assertTrue(result["trial_session"]["structured_feedback_required"])
        self.assertFalse(result["trial_session"]["free_text_feedback_allowed"])
        self.assertEqual(len(result["trial_session"]["feedback_token"]), 64)
        private_text = self.path.read_text(encoding="utf-8")
        self.assertNotIn(prompt, private_text)
        self.assertNotIn(generated["chat"]["assistant_message"], private_text)
        state = load_private_state(self.path, self.protocol)
        self.assertEqual(len(state["audit_events"]), 1)

    def test_structured_feedback_is_closed_content_free_and_single_use(self) -> None:
        self.complete_state()
        generated = {
            "chat": {
                "assistant_message": "蓝光在大气中更容易发生散射。",
                "generation": {"provider": "deterministic"},
            }
        }
        chat_payload = {
            "participant_id": "P01",
            "invitation_code": self.codes[0],
            "messages": [{"role": "user", "content": "为什么天空是蓝色？"}],
        }
        with patch.object(server, "run_chat_turn", return_value=generated):
            chat = server.run_trial_chat_turn(chat_payload)
        feedback_payload = {
            "participant_id": "P01",
            "invitation_code": self.codes[0],
            "feedback_token": chat["trial_session"]["feedback_token"],
            "helpfulness": 5,
            "clarity": 4,
            "state_alignment": "yes",
            "issue_category": "none",
        }
        result = server.handle_trial_feedback(feedback_payload)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["free_text_collected"])
        self.assertEqual(result["progress"]["participants"][0]["credited"], 1)
        persisted = self.feedback_path.read_text(encoding="utf-8")
        self.assertNotIn("为什么天空是蓝色", persisted)
        self.assertNotIn("蓝光在大气", persisted)
        self.assertEqual(len(load_feedback_state(self.feedback_path)["feedback_events"]), 1)
        with self.assertRaisesRegex(ValueError, "already been submitted"):
            server.handle_trial_feedback(feedback_payload)
        with self.assertRaisesRegex(ValueError, "fields are not closed"):
            server.handle_trial_feedback({**feedback_payload, "free_text": "must be rejected"})
        with self.assertRaisesRegex(ValueError, "must be integers"):
            server.handle_trial_feedback({**feedback_payload, "feedback_token": "0" * 64, "helpfulness": True})

    def test_sensitive_prompt_is_rejected_and_never_reaches_model(self) -> None:
        self.complete_state()
        prompt = "我叫王小明，邮箱是 test@example.com"
        payload = {
            "participant_id": "P02",
            "invitation_code": self.codes[1],
            "messages": [{"role": "user", "content": prompt}],
        }
        with patch.object(server, "run_chat_turn") as generate:
            with self.assertRaisesRegex(ValueError, "direct_identifiers"):
                server.run_trial_chat_turn(payload)
        generate.assert_not_called()
        self.assertNotIn(prompt, self.path.read_text(encoding="utf-8"))
        state = load_private_state(self.path, self.protocol)
        self.assertTrue(state["stopped"])
        self.assertFalse(state["trial_active"])
        self.assertIn("prohibited_or_unknown_data_detected", state["stop_reasons"])

    def test_sensitive_prior_message_is_the_content_free_audited_event(self) -> None:
        self.complete_state()
        sensitive = "我叫王小明，护照号是 A12345678"
        payload = {
            "participant_id": "P03",
            "invitation_code": self.codes[2],
            "messages": [
                {"role": "user", "content": sensitive},
                {"role": "assistant", "content": "请不要提供个人资料。"},
                {"role": "user", "content": "换一个一般问题。"},
            ],
        }
        with patch.object(server, "run_chat_turn") as generate:
            with self.assertRaisesRegex(ValueError, "direct_identifiers"):
                server.run_trial_chat_turn(payload)
        generate.assert_not_called()
        state = load_private_state(self.path, self.protocol)
        self.assertEqual(len(state["audit_events"]), 1)
        private_text = self.path.read_text(encoding="utf-8")
        self.assertNotIn(sensitive, private_text)
        self.assertTrue(state["stopped"])

    def test_unapproved_generation_provider_stops_before_delivery(self) -> None:
        self.complete_state()
        generated = {
            "chat": {
                "assistant_message": "此回答不得交付。",
                "generation": {"provider": "unexpected-external-provider"},
            }
        }
        payload = {
            "participant_id": "P01",
            "invitation_code": self.codes[0],
            "messages": [{"role": "user", "content": "为什么天空是蓝色？"}],
        }
        with patch.object(server, "run_chat_turn", return_value=generated):
            with self.assertRaisesRegex(ValueError, "unapproved generation provider"):
                server.run_trial_chat_turn(payload)
        state = load_private_state(self.path, self.protocol)
        self.assertTrue(state["stopped"])
        self.assertFalse(state["trial_active"])
        self.assertIn(
            "participant_content_would_be_sent_to_external_api",
            state["stop_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
