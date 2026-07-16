from __future__ import annotations

import unittest

from psm_v0.chat_prompt import build_conversation_state_capsule
from product_alpha_app.server import bounded_multiturn_edit_answer, deterministic_long_context_state_answer


class ConversationStateCapsuleTests(unittest.TestCase):
    def test_capsule_uses_user_statements_and_retains_remote_history(self) -> None:
        conversation = [
            {"role": "user", "content": "方案叫榆叶。"},
            {"role": "assistant", "content": "方案叫松针。"},
            {"role": "user", "content": "界面用浅色。"},
            {"role": "assistant", "content": "收到。"},
            {"role": "user", "content": "最终叫什么？"},
        ]
        capsule = build_conversation_state_capsule(conversation)
        self.assertTrue(capsule["user_authoritative"])
        self.assertEqual(capsule["active_user_statements"], 3)
        self.assertIn("方案叫榆叶。", capsule["user_statements"])
        self.assertNotIn("方案叫松针。", capsule["user_statements"])

    def test_expanded_topic_switch_discards_old_risk_segment(self) -> None:
        conversation = [
            {"role": "user", "content": "我胸痛。"},
            {"role": "assistant", "content": "请联系急救。"},
            {"role": "user", "content": "接下来不谈健康问题了，改聊咖啡。"},
            {"role": "assistant", "content": "好的。"},
            {"role": "user", "content": "哪种更苦？"},
        ]
        capsule = build_conversation_state_capsule(conversation)
        self.assertTrue(capsule["topic_switch_applied"])
        self.assertEqual(capsule["active_user_statements"], 2)
        self.assertNotIn("我胸痛。", capsule["user_statements"])
        self.assertIn("哪种更苦？", capsule["user_statements"])

    def test_latest_correction_order_is_preserved(self) -> None:
        conversation = [
            {"role": "user", "content": "文件叫 draft.zip。"},
            {"role": "assistant", "content": "收到。"},
            {"role": "user", "content": "改成 final.zip，旧名作废。"},
            {"role": "user", "content": "现在叫什么？"},
        ]
        capsule = build_conversation_state_capsule(conversation)
        self.assertEqual(
            capsule["user_statements"],
            ["文件叫 draft.zip。", "改成 final.zip，旧名作废。", "现在叫什么？"],
        )

    def test_natural_latest_day_and_unresolved_wording_resolve(self) -> None:
        correction = [
            {"role": "user", "content": "评审原本排在星期二。"},
            {"role": "assistant", "content": "收到。"},
            {"role": "user", "content": "改期到星期四，星期二取消。"},
            {"role": "assistant", "content": "已更新。"},
            {"role": "user", "content": "最终哪一天评审？"},
        ]
        self.assertEqual(deterministic_long_context_state_answer(correction[-1]["content"], correction), "星期四")

        unresolved = [
            {"role": "user", "content": "今天两件正事：修搜索页，再补部署说明。"},
            {"role": "assistant", "content": "收到。"},
            {"role": "user", "content": "搜索页已经修完。"},
            {"role": "assistant", "content": "已完成。"},
            {"role": "user", "content": "还剩哪一件？"},
        ]
        self.assertEqual(deterministic_long_context_state_answer(unresolved[-1]["content"], unresolved), "补部署说明")

    def test_natural_translation_replacement_inherits_constraint(self) -> None:
        conversation = [
            {"role": "user", "content": "把报告已经准备好译成英文，回答里不要加解释。"},
            {"role": "assistant", "content": "The report is ready."},
            {"role": "user", "content": "把 ready 换成 complete，照旧交付。"},
        ]
        self.assertEqual(
            bounded_multiturn_edit_answer(conversation[-1]["content"], conversation),
            "The report is complete.",
        )


if __name__ == "__main__":
    unittest.main()
