from __future__ import annotations

import unittest

from product_alpha_app import server


class RestartRecoveryV283Tests(unittest.TestCase):
    def setUp(self) -> None:
        server.ROLLING_STATE_SESSIONS.clear()
        server.ROLLING_STATE_TOMBSTONES.clear()

    def seed(self, session_id: str = "restart_session_abcdef01") -> None:
        server.update_rolling_session_state(
            session_id,
            [{"id": 1, "role": "user", "content": "项目代号定为白砾。"}],
            now=100.0,
            client_server_instance_id=server.SERVER_INSTANCE_ID,
        )

    def test_active_reset_reload_expired_and_restarted_are_distinguishable(self) -> None:
        session_id = "restart_session_abcdef01"
        self.seed(session_id)
        cases = (
            ("active", 101.0, server.SERVER_INSTANCE_ID, session_id, "active"),
            ("reset", 102.0, server.SERVER_INSTANCE_ID, "reset_session_abcdef012", "reset"),
            ("reload", 103.0, server.SERVER_INSTANCE_ID, "reload_session_abcdef01", "reload"),
            ("active", 1902.0, server.SERVER_INSTANCE_ID, session_id, "expired"),
            ("active", 104.0, "previous-server-instance", "restart_session_abcdef02", "restarted"),
        )
        observed = []
        for event, now, instance, target_session, expected in cases:
            _, metadata = server.update_rolling_session_state(
                target_session,
                [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
                now=now,
                client_event=event,
                client_server_instance_id=instance,
            )
            status = metadata["continuity_status"]
            observed.append(status["state"])
            self.assertEqual(status["state"], expected)
            self.assertFalse(status["raw_conversation_persisted"])
        self.assertEqual(set(observed), {"active", "reset", "reload", "expired", "restarted"})

    def test_memory_loss_question_fails_cleanly_without_fabricating_fact(self) -> None:
        for state in ("reset", "reload", "expired", "restarted"):
            metadata = {
                "continuity_status": server.continuity_status(state, memory_available=False),
                "ephemeral_memory_only": True,
                "disk_persistence": False,
            }
            result = server.run_chat_turn(
                [{"id": 1, "role": "user", "content": "之前的项目代号是什么？"}],
                "review",
                rolling_state_metadata=metadata,
            )
            answer = result["chat"]["assistant_message"]
            self.assertNotIn("白砾", answer)
            self.assertIn("不能确认", answer)
            self.assertIn("重新告诉我", answer)

    def test_memory_loss_signal_clears_existing_same_session_state(self) -> None:
        for event in ("reset", "reload"):
            with self.subTest(event=event):
                self.setUp()
                session_id = f"same_session_{event}_abcdef"
                self.seed(session_id)
                statements, metadata = server.update_rolling_session_state(
                    session_id,
                    [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
                    now=101.0,
                    client_event=event,
                    client_server_instance_id=server.SERVER_INSTANCE_ID,
                )
                self.assertNotIn("项目代号定为白砾。", statements)
                self.assertTrue(metadata["continuity_status"]["memory_cleared"])

    def test_expiry_tombstones_are_hash_only_and_bounded(self) -> None:
        session_id = "expiry_session_abcdef012"
        other_session_id = "expiry_session_abcdef013"
        self.seed(session_id)
        self.seed(other_session_id)
        server.update_rolling_session_state(
            session_id,
            [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
            now=1901.0,
            client_server_instance_id=server.SERVER_INSTANCE_ID,
        )
        self.assertNotIn(session_id, server.ROLLING_STATE_TOMBSTONES)
        self.assertNotIn(other_session_id, server.ROLLING_STATE_TOMBSTONES)
        self.assertNotIn(server.rolling_session_digest(session_id), server.ROLLING_STATE_TOMBSTONES)
        self.assertIn(server.rolling_session_digest(other_session_id), server.ROLLING_STATE_TOMBSTONES)
        self.assertLessEqual(len(server.ROLLING_STATE_TOMBSTONES), server.ROLLING_STATE_MAX_TOMBSTONES)

    def test_status_exposes_only_ephemeral_continuity_instance(self) -> None:
        status = server.load_status_summary()
        self.assertEqual(status["continuity_protocol"], "psm_v0_283_restart_recovery_v1")
        self.assertEqual(status["continuity_instance_id"], server.SERVER_INSTANCE_ID)
        self.assertFalse(status["persistent_conversation_memory_enabled"])

    def test_natural_prior_references_do_not_match_new_task_controls(self) -> None:
        positives = (
            "那个项目代号来着？",
            "我們定的檔名叫什麼？",
            "原定的会议是几点？",
            "剩下哪件没做？",
            "What was the project codename?",
            "Remind me of the filename we settled on.",
        )
        negatives = (
            "请给这个新项目起个代号。",
            "新文件应该叫什么？",
            "安排一个新的会议时间。",
            "列出今天的新待办。",
        )
        self.assertTrue(all(server.asks_unavailable_prior_state(text) for text in positives))
        self.assertTrue(all(not server.asks_unavailable_prior_state(text) for text in negatives))


if __name__ == "__main__":
    unittest.main()
