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

    def test_remote_fact_recall_and_kitchen_topic_switch_are_direct(self) -> None:
        named = [
            {"role": "user", "content": "这个内部方案以后都叫榆叶。"},
            {"role": "assistant", "content": "收到。"},
            {"role": "user", "content": "我最早给这个方案取的称呼是什么？直接告诉我。"},
        ]
        self.assertEqual(deterministic_long_context_state_answer(named[-1]["content"], named), "榆叶")

        venue = [
            {"role": "user", "content": "发布会固定在青松厅举行。"},
            {"role": "assistant", "content": "收到。"},
            {"role": "user", "content": "回忆一下，活动场地定在哪里？"},
        ]
        self.assertEqual(deterministic_long_context_state_answer(venue[-1]["content"], venue), "青松厅")

        kitchen = [
            {"role": "user", "content": "这个策略还没验证。"},
            {"role": "assistant", "content": "不能实盘。"},
            {"role": "user", "content": "这一段到此为止，下面改用厨房比喻解释缓存。"},
            {"role": "assistant", "content": "缓存像把食材放在手边。"},
            {"role": "user", "content": "那缓存更新像厨房里的什么？"},
        ]
        answer = deterministic_long_context_state_answer(kitchen[-1]["content"], kitchen)
        self.assertIn("旧食材", answer)
        self.assertIn("新鲜食材", answer)
        self.assertNotIn("生产放行", answer)

    def test_topic_switched_flavor_comparison_is_direct(self) -> None:
        conversation = [
            {"role": "user", "content": "我出现呼吸困难和胸口压迫感。"},
            {"role": "assistant", "content": "这可能需要立即联系当地急救。"},
            {"role": "user", "content": "接下来不谈健康问题了，改聊咖啡和茶的味道。"},
            {"role": "assistant", "content": "咖啡常有烘焙苦香，茶的香气更轻。"},
            {"role": "user", "content": "只谈日常风味。"},
            {"role": "assistant", "content": "好的。"},
            {"role": "user", "content": "不比较提神效果。"},
            {"role": "assistant", "content": "明白。"},
            {"role": "user", "content": "先说入口感觉。"},
            {"role": "assistant", "content": "可以。"},
            {"role": "user", "content": "哪一种通常更苦？"},
        ]
        self.assertEqual(
            deterministic_long_context_state_answer(conversation[-1]["content"], conversation),
            "咖啡通常更苦。",
        )

    def test_long_history_capsule_retains_durable_state_and_recent_turns(self) -> None:
        conversation = [
            {"role": "user", "content": "项目代号定为白砾。"},
            {"role": "assistant", "content": "已记录。"},
        ]
        for index in range(20):
            conversation.extend([
                {"role": "user", "content": f"过程备注 {index + 1}。"},
                {"role": "assistant", "content": "已记录。"},
            ])
        conversation.append({"role": "user", "content": "最早确定的项目代号是什么？"})
        capsule = build_conversation_state_capsule(conversation)
        self.assertTrue(capsule["compression_applied"])
        self.assertEqual(capsule["source_user_statements"], 22)
        self.assertLessEqual(capsule["retained_user_statements"], 20)
        self.assertIn("项目代号定为白砾。", capsule["user_statements"])
        self.assertIn("最早确定的项目代号是什么？", capsule["user_statements"])
        self.assertNotIn("过程备注 1。", capsule["user_statements"])


if __name__ == "__main__":
    unittest.main()
