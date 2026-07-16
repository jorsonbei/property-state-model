from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from product_alpha_app import server


class ContentFreeTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        server.CHAT_CANCEL_EVENTS.clear()
        server.reset_chat_telemetry()

    def tearDown(self) -> None:
        server.CHAT_CANCEL_EVENTS.clear()
        server.reset_chat_telemetry()

    def test_health_snapshot_contains_only_content_free_aggregates(self) -> None:
        snapshot = server.chat_health_snapshot()
        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertEqual(snapshot["status"], "healthy")
        self.assertFalse(snapshot["identifiers_retained"])
        self.assertFalse(snapshot["content_retained"])
        self.assertFalse(snapshot["disk_persistence"])
        for forbidden in (
            "prompt",
            "answer",
            "messages",
            "session_id",
            "request_id",
            "participant_id",
            "invitation_code",
            "model_output",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_lifecycle_counters_and_latency_buckets_are_exact(self) -> None:
        request_id = "chat_telemetry_1234567890abcdef"
        event = server.register_chat_request(request_id)
        self.assertEqual(server.chat_health_snapshot()["status"], "busy")
        active_cancel = server.cancel_chat_request(request_id)
        server.record_chat_outcome(request_id, "cancelled")
        server.unregister_chat_request(request_id, event)
        inactive_cancel = server.cancel_chat_request(request_id)
        with self.assertRaises(server.ChatRequestError):
            server.cancel_chat_request("invalid")

        snapshot = server.chat_health_snapshot()
        self.assertTrue(active_cancel["active"])
        self.assertFalse(inactive_cancel["active"])
        self.assertEqual(snapshot["status"], "healthy")
        self.assertEqual(snapshot["active_requests"], 0)
        self.assertEqual(snapshot["counters"]["accepted"], 1)
        self.assertEqual(snapshot["counters"]["cancel_requests"], 2)
        self.assertEqual(snapshot["counters"]["cancel_active"], 1)
        self.assertEqual(snapshot["counters"]["cancel_inactive"], 1)
        self.assertEqual(snapshot["counters"]["cancelled"], 1)
        self.assertEqual(snapshot["counters"]["invalid_rejected"], 1)
        self.assertEqual(
            sum(bucket["count"] for bucket in snapshot["latency_buckets_ms"]["cancelled"]),
            1,
        )

    def test_completed_and_failed_outcomes_use_fixed_buckets_without_raw_samples(self) -> None:
        for outcome, index in (("completed", 1), ("failed", 2)):
            request_id = f"chat_outcome_{index}_1234567890abcdef"
            event = server.register_chat_request(request_id)
            server.record_chat_outcome(request_id, outcome)
            server.unregister_chat_request(request_id, event)
        snapshot = server.chat_health_snapshot()
        self.assertEqual(snapshot["counters"]["completed"], 1)
        self.assertEqual(snapshot["counters"]["failed"], 1)
        self.assertFalse(snapshot["raw_latency_samples_retained"])
        self.assertEqual(
            sum(bucket["count"] for bucket in snapshot["latency_buckets_ms"]["completed"]),
            1,
        )
        self.assertEqual(
            sum(bucket["count"] for bucket in snapshot["latency_buckets_ms"]["failed"]),
            1,
        )

    def test_health_state_tracks_busy_and_saturated_without_ids(self) -> None:
        first = server.register_chat_request("chat_health_1_1234567890abcdef")
        self.assertEqual(server.chat_health_snapshot()["status"], "busy")
        with patch.object(server, "CHAT_CONCURRENCY_LIMIT", 1):
            saturated = server.chat_health_snapshot()
        self.assertEqual(saturated["status"], "saturated")
        self.assertEqual(saturated["active_requests"], 1)
        server.unregister_chat_request("chat_health_1_1234567890abcdef", first)

    def test_reset_clears_all_process_memory_telemetry(self) -> None:
        event = server.register_chat_request("chat_reset_1234567890abcdef")
        server.record_chat_outcome("chat_reset_1234567890abcdef", "completed")
        server.unregister_chat_request("chat_reset_1234567890abcdef", event)
        server.reset_chat_telemetry()
        snapshot = server.chat_health_snapshot()
        self.assertTrue(all(value == 0 for value in snapshot["counters"].values()))
        self.assertTrue(
            all(
                bucket["count"] == 0
                for buckets in snapshot["latency_buckets_ms"].values()
                for bucket in buckets
            )
        )


if __name__ == "__main__":
    unittest.main()
