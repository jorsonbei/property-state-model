from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from psm_v0.external_trial_protocol import (
    CONSENT_SCHEMA,
    active_participant_ids,
    build_content_free_audit_event,
    inspect_prompt,
    load_protocol,
    purge_expired_events,
    reserve_api_budget,
    stop_gate,
    trial_start_gate,
    validate_audit_event,
    validate_consent_receipt,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"


def receipt(index: int, *, adult: bool = True, acknowledged: bool = True, revoked_at: str | None = None) -> dict:
    return {
        "schema_version": CONSENT_SCHEMA,
        "participant_id": f"P{index:02d}",
        "invitation_sha256": f"{index:064x}",
        "invitee_binding_hmac_sha256": f"{index + 100:064x}",
        "adult_confirmed": adult,
        "adult_verified_by_operator": adult,
        "adult_verification_method": "operator_verified_pre_vetted_adult_invitee",
        "adult_verified_at": "2026-07-15T00:56:00Z",
        "notice_version": "psm_v0_262_trial_notice_v1",
        "notice_displayed_at": "2026-07-15T00:57:00Z",
        "notice_acknowledged": acknowledged,
        "notice_acknowledged_at": "2026-07-15T00:58:00Z",
        "consented_at": "2026-07-15T01:00:00Z",
        "session_enabled_at": "2026-07-15T01:01:00Z",
        "operator_supervision_attested": True,
        "revoked_at": revoked_at,
    }


class ExternalTrialProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = load_protocol(PROTOCOL_PATH)

    def test_frozen_protocol_matches_approved_conservative_scope(self) -> None:
        self.assertEqual(validate_protocol(self.protocol), [])
        self.assertEqual(self.protocol["trial_scope"]["participant_minimum"], 3)
        self.assertEqual(self.protocol["trial_scope"]["participant_maximum"], 5)
        self.assertEqual(self.protocol["retention"]["operational_metadata_days"], 7)
        self.assertEqual(self.protocol["api_budget"]["calendar_month_limit"], 20.0)

    def test_trial_requires_three_to_five_valid_adult_consents(self) -> None:
        valid = [receipt(index) for index in range(1, 4)]
        self.assertTrue(trial_start_gate(valid, self.protocol)["passed"])
        self.assertFalse(trial_start_gate(valid[:2], self.protocol)["passed"])
        self.assertFalse(trial_start_gate([receipt(index) for index in range(1, 7)], self.protocol)["passed"])
        self.assertEqual(active_participant_ids(valid, self.protocol), {"P01", "P02", "P03"})

    def test_minor_missing_notice_and_revoked_consent_fail_closed(self) -> None:
        self.assertTrue(validate_consent_receipt(receipt(1, adult=False), self.protocol))
        self.assertTrue(validate_consent_receipt(receipt(1, acknowledged=False), self.protocol))
        self.assertTrue(validate_consent_receipt(receipt(1, revoked_at="2026-07-15T02:00:00Z"), self.protocol))

    def test_notice_consent_and_session_sequence_is_strict(self) -> None:
        invalid = receipt(1)
        invalid["notice_displayed_at"] = "2026-07-15T01:02:00Z"
        self.assertTrue(validate_consent_receipt(invalid, self.protocol))
        self.assertTrue(validate_consent_receipt({**receipt(1), "adult_verified_by_operator": False}, self.protocol))
        self.assertTrue(validate_consent_receipt({**receipt(1), "invitee_binding_hmac_sha256": "invalid"}, self.protocol))

    def test_low_risk_prompt_is_allowed(self) -> None:
        decision = inspect_prompt("请解释为什么金属摸起来比木头凉。", self.protocol)
        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["categories"], ["low_risk_general"])

    def test_sensitive_and_professional_prompts_are_rejected(self) -> None:
        prompts = [
            "联系我 test@example.com",
            "password: this-is-private",
            "请根据我的病历诊断并给药量",
            "律师帮我处理我的案件",
            "告诉我现在买入哪只股票",
            "分析这份未公开的私人文件",
            "我今年16岁，这是我的资料",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertFalse(inspect_prompt(prompt, self.protocol)["allowed"])

    def test_audit_event_retains_hmac_but_no_content(self) -> None:
        prompt = "解释一个低风险物理现象"
        decision = inspect_prompt(prompt, self.protocol)
        event = build_content_free_audit_event(
            event_id="E001",
            participant_id="P01",
            prompt=prompt,
            decision=decision,
            occurred_at="2026-07-15T01:05:00Z",
            audit_secret=b"local-test-secret",
            latency_ms=120,
            token_count=80,
        )
        self.assertEqual(validate_audit_event(event), [])
        self.assertNotIn(prompt, json.dumps(event, ensure_ascii=False))
        self.assertFalse(event["raw_prompt_persisted"])
        self.assertFalse(event["participant_content_sent_to_external_api"])

    def test_seven_day_retention_purges_old_metadata(self) -> None:
        decision = {"allowed": True, "categories": ["low_risk_general"]}
        events = [
            build_content_free_audit_event(
                event_id="old", participant_id="P01", prompt="old", decision=decision,
                occurred_at="2026-07-07T23:59:59Z", audit_secret=b"s", latency_ms=1, token_count=1,
            ),
            build_content_free_audit_event(
                event_id="new", participant_id="P01", prompt="new", decision=decision,
                occurred_at="2026-07-14T00:00:01Z", audit_secret=b"s", latency_ms=1, token_count=1,
            ),
        ]
        retained, tombstones = purge_expired_events(
            events, now=datetime(2026, 7, 15, tzinfo=timezone.utc)
        )
        self.assertEqual([item["event_id"] for item in retained], ["new"])
        self.assertEqual(tombstones[0]["event_id"], "old")
        self.assertFalse(tombstones[0]["content_retained"])

    def test_budget_reservation_allows_exact_limit_and_rejects_overage(self) -> None:
        reservations = []
        allowed, first, _ = reserve_api_budget(
            reservations,
            reservation_id="R1",
            occurred_at="2026-07-15T00:00:00Z",
            purpose="synthetic_protocol_review",
            reserved_cost_usd=Decimal("18.00"),
            contains_participant_content=False,
            protocol=self.protocol,
        )
        self.assertTrue(allowed)
        assert first is not None
        reservations.append(first)
        allowed, second, _ = reserve_api_budget(
            reservations,
            reservation_id="R2",
            occurred_at="2026-07-15T01:00:00Z",
            purpose="synthetic_safety_evaluation",
            reserved_cost_usd=Decimal("2.00"),
            contains_participant_content=False,
            protocol=self.protocol,
        )
        self.assertTrue(allowed)
        assert second is not None
        reservations.append(second)
        allowed, _, reason = reserve_api_budget(
            reservations,
            reservation_id="R3",
            occurred_at="2026-07-15T02:00:00Z",
            purpose="synthetic_protocol_review",
            reserved_cost_usd=Decimal("0.01"),
            contains_participant_content=False,
            protocol=self.protocol,
        )
        self.assertFalse(allowed)
        self.assertIn("exceeded", reason or "")

    def test_participant_content_external_api_reservation_is_rejected(self) -> None:
        allowed, _, reason = reserve_api_budget(
            [], reservation_id="R1", occurred_at="2026-07-15T00:00:00Z",
            purpose="synthetic_protocol_review", reserved_cost_usd=Decimal("1.00"),
            contains_participant_content=True, protocol=self.protocol,
        )
        self.assertFalse(allowed)
        self.assertIn("participant content", reason or "")

    def test_any_boundary_failure_requires_stop_without_auto_resume(self) -> None:
        result = stop_gate(
            consent_errors=["revoked"],
            prompt_decision={"allowed": False},
            budget_allowed=False,
            incident_open=True,
            deletion_failed=True,
        )
        self.assertTrue(result["stop_required"])
        self.assertEqual(len(result["reasons"]), 5)
        self.assertFalse(result["automatic_resume_allowed"])


if __name__ == "__main__":
    unittest.main()
