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
        with patch.object(server, "CHAT_CANCEL_MAX_ENTRIES", 1):
            first_event = server.register_chat_request(first)
            with self.assertRaises(server.ChatRequestError) as context:
                server.register_chat_request(second)
        self.assertEqual(context.exception.status, 503)
        self.assertFalse(first_event.is_set())
        self.assertIn(first, server.CHAT_CANCEL_EVENTS)

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
