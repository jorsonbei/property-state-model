from __future__ import annotations

import unittest

from product_alpha_app import server


class RollingStateHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        server.ROLLING_STATE_SESSIONS.clear()
        server.ROLLING_STATE_TOMBSTONES.clear()

    def test_archived_user_fact_survives_the_120_message_window(self) -> None:
        messages = [
            {"role": "user", "content": f"过程记录 {index}。"}
            if index % 2 == 0
            else {"role": "assistant", "content": "已记录。"}
            for index in range(120)
        ]
        messages[-1] = {"role": "user", "content": "最早确定的项目代号是什么？只回答代号。"}
        result = server.run_chat_turn(
            messages,
            "review",
            rolling_user_statements=["项目代号定为白砾。"],
        )
        self.assertEqual(result["chat"]["assistant_message"], "白砾")
        continuity = result["chat"]["state_continuity"]
        self.assertEqual(continuity["history_messages"], 120)
        self.assertTrue(continuity["rolling_state_applied"])
        self.assertEqual(continuity["rolling_user_statements"], 1)

    def test_session_state_is_incremental_bounded_and_ephemeral(self) -> None:
        session_id = "session_0123456789abcdef"
        first, metadata = server.update_rolling_session_state(
            session_id,
            [{"id": 1, "role": "user", "content": "项目代号定为白砾。"}],
            now=100.0,
        )
        self.assertEqual(first, ["项目代号定为白砾。"])
        second, metadata = server.update_rolling_session_state(
            session_id,
            [
                {"id": 1, "role": "user", "content": "项目代号定为白砾。"},
                {"id": 2, "role": "assistant", "content": "已记录。"},
                {"id": 3, "role": "user", "content": "输出文件名改为 final-long.zip，旧名作废。"},
            ],
            now=101.0,
        )
        self.assertEqual(second.count("项目代号定为白砾。"), 1)
        self.assertIn("输出文件名改为 final-long.zip，旧名作废。", second)
        self.assertTrue(metadata["ephemeral_memory_only"])
        self.assertFalse(metadata["disk_persistence"])
        self.assertLessEqual(metadata["retained_user_statements"], 20)

    def test_topic_switch_removes_archived_old_topic_state(self) -> None:
        session_id = "session_abcdef0123456789"
        server.update_rolling_session_state(
            session_id,
            [{"id": 1, "role": "user", "content": "我出现呼吸困难和胸口压迫感。"}],
            now=100.0,
        )
        statements, metadata = server.update_rolling_session_state(
            session_id,
            [
                {"id": 2, "role": "assistant", "content": "请立即联系当地急救。"},
                {"id": 3, "role": "user", "content": "接下来不谈健康问题了，改聊咖啡和茶的味道。"},
            ],
            now=101.0,
        )
        self.assertNotIn("我出现呼吸困难和胸口压迫感。", statements)
        self.assertTrue(metadata["topic_switch_applied"])

    def test_invalid_session_id_disables_memory(self) -> None:
        statements, metadata = server.update_rolling_session_state(
            "bad",
            [{"id": 1, "role": "user", "content": "不应保存"}],
        )
        self.assertEqual(statements, [])
        self.assertFalse(metadata["enabled"])
        self.assertEqual(server.ROLLING_STATE_SESSIONS, {})


if __name__ == "__main__":
    unittest.main()
