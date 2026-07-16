from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from product_alpha_app import server


class ServerCancelRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        server.CHAT_CANCEL_EVENTS.clear()

    def tearDown(self) -> None:
        server.CHAT_CANCEL_EVENTS.clear()

    def test_active_request_can_be_cancelled_without_storing_prompt_content(self) -> None:
        request_id = "chat_test_1234567890abcdef"
        event = server.register_chat_request(request_id)
        entry = server.CHAT_CANCEL_EVENTS[request_id]
        self.assertEqual(set(entry), {"event", "created_at"})
        self.assertIs(entry["event"], event)
        self.assertNotIn("prompt", entry)

        result = server.cancel_chat_request(request_id)
        self.assertEqual(result, {"request_id": request_id, "accepted": True, "active": True})
        self.assertTrue(event.is_set())
        with self.assertRaises(server.ChatCancelled):
            server.raise_if_chat_cancelled(event, request_id)

        server.unregister_chat_request(request_id, event)
        self.assertEqual(server.CHAT_CANCEL_EVENTS, {})

    def test_registry_rejects_capacity_overflow_instead_of_evicting_active_request(self) -> None:
        first = "chat_capacity_1234567890abc"
        second = "chat_capacity_1234567890def"
        with patch.object(server, "CHAT_CANCEL_MAX_ENTRIES", 1), patch.object(
            server, "CHAT_CONCURRENCY_LIMIT", 2
        ):
            first_event = server.register_chat_request(first)
            with self.assertRaises(server.ChatRequestError) as context:
                server.register_chat_request(second)
        self.assertEqual(context.exception.status, 503)
        self.assertFalse(first_event.is_set())
        self.assertIn(first, server.CHAT_CANCEL_EVENTS)

    def test_operational_capacity_has_structured_error_and_retains_all_active_requests(self) -> None:
        request_ids = [f"chat_limit_{index}_1234567890abcdef" for index in range(3)]
        with patch.object(server, "CHAT_CONCURRENCY_LIMIT", 2):
            events = [server.register_chat_request(request_id) for request_id in request_ids[:2]]
            with self.assertRaises(server.ChatRequestError) as context:
                server.register_chat_request(request_ids[2])
        self.assertEqual(context.exception.status, 503)
        self.assertEqual(context.exception.code, "chat_capacity_reached")
        self.assertEqual(context.exception.retry_after_seconds, 1)
        self.assertEqual(set(server.CHAT_CANCEL_EVENTS), set(request_ids[:2]))
        self.assertTrue(all(not event.is_set() for event in events))

    def test_duplicate_id_fails_before_capacity_without_disturbing_original(self) -> None:
        request_id = "chat_duplicate_1234567890abcdef"
        with patch.object(server, "CHAT_CONCURRENCY_LIMIT", 1):
            event = server.register_chat_request(request_id)
            with self.assertRaises(server.ChatRequestError) as context:
                server.register_chat_request(request_id)
        self.assertEqual(context.exception.status, 409)
        self.assertEqual(context.exception.code, "duplicate_request_id")
        self.assertFalse(event.is_set())

    def test_server_generated_request_id_is_bounded_and_content_free(self) -> None:
        request_id = server.server_chat_request_id()
        self.assertRegex(request_id, server.CHAT_REQUEST_PATTERN)
        self.assertLessEqual(len(request_id), 80)
        self.assertNotIn("prompt", request_id)

    def test_expired_registry_entry_is_cancelled_and_pruned(self) -> None:
        request_id = "chat_expired_1234567890abc"
        event = server.register_chat_request(request_id)
        server.CHAT_CANCEL_EVENTS[request_id]["created_at"] = (
            time.monotonic() - server.CHAT_CANCEL_TTL_SECONDS - 1
        )
        server.prune_chat_cancel_events(time.monotonic())
        self.assertTrue(event.is_set())
        self.assertNotIn(request_id, server.CHAT_CANCEL_EVENTS)

    def test_invalid_request_id_fails_closed(self) -> None:
        for request_id in ("", "too-short", "private data with spaces", "x" * 81):
            with self.assertRaises(server.ChatRequestError) as context:
                server.register_chat_request(request_id)
            self.assertEqual(context.exception.status, 400)
            self.assertEqual(context.exception.code, "invalid_request_id")

    def test_cancelled_event_is_not_treated_as_a_normal_result(self) -> None:
        event = threading.Event()
        event.set()
        with self.assertRaises(server.ChatCancelled):
            server.run_chat_turn(
                [{"role": "user", "content": "你好，你是谁？"}],
                "review",
                cancel_event=event,
            )


if __name__ == "__main__":
    unittest.main()
