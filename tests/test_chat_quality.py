from __future__ import annotations

import unittest
from unittest.mock import patch

from product_alpha_app import server
from psm_v0.chat_quality_auditor import audit_chat_answer


class ChatQualityTests(unittest.TestCase):
    def test_low_risk_absolute_language_can_be_softened_without_breaking_negation(self) -> None:
        answer = server.soften_absolute_language("这一定能保证成功，但不能保证外部结果。")

        self.assertIn("通常", answer)
        self.assertIn("尽量确保", answer)
        self.assertIn("不能保证", answer)

    def run_offline(self, messages: list[dict], scenario: str = "review") -> dict:
        provider_failure = {
            "status": "error",
            "answer": "",
            "provider": "ollama",
            "model": "offline-test",
            "duration_ms": 1,
            "error": "offline test",
            "reasoning_leak_removed": False,
        }
        with patch.object(server, "try_ollama_chat_generation", return_value=provider_failure):
            return server.run_chat_turn(messages, scenario)

    def test_project_status_comes_from_structured_local_state(self) -> None:
        context = server.load_project_context()
        result = self.run_offline([{"role": "user", "content": "项目现在做到哪里了？"}])
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn(context["current_version"], answer)
        self.assertIn(context["formal_version"], answer)
        self.assertIn(str(context["core_cases"]), answer)
        self.assertIn(context["next_version"], answer)
        self.assertNotIn("未来几个月", answer)
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_roadmap_comes_from_structured_next_stage(self) -> None:
        context = server.load_project_context()
        result = self.run_offline([{"role": "user", "content": "后续计划是什么？"}])
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "roadmap")
        self.assertIn(context["current_version"], answer)
        self.assertIn(context["next_version"], answer)
        self.assertIn(context["next_objective"], answer)
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_project_results_come_from_provider_selection(self) -> None:
        context = server.load_project_context()
        result = self.run_offline(
            [{"role": "user", "content": "用正常聊天方式告诉我：这轮已经完成了什么，有什么作用？"}]
        )
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "project_results")
        self.assertIn(context["current_version"], answer)
        self.assertIn(context["selected_model"], answer)
        self.assertIn(context["next_version"], answer)
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_project_followup_routes_to_frozen_roadmap(self) -> None:
        result = self.run_offline(
            [
                {"role": "user", "content": "告诉我当前项目版本。"},
                {"role": "assistant", "content": "当前项目是 PSM V0.250。"},
                {"role": "user", "content": "那下一阶段要解决什么？"},
            ]
        )

        self.assertEqual(result["chat"]["intent"], "roadmap")
        self.assertIn("80", result["chat"]["assistant_message"])
        self.assertIn("judge-only", result["chat"]["assistant_message"])

    def test_assistant_role_history_answers_second_stage(self) -> None:
        messages = [
            {"role": "user", "content": "分三阶段说明。"},
            {
                "role": "assistant",
                "content": "第一阶段：收集事实。\n第二阶段：建立状态图。\n第三阶段：验证。",
            },
            {"role": "user", "content": "刚才第二阶段叫什么？"},
        ]
        result = self.run_offline(messages)

        self.assertEqual(result["chat"]["intent"], "history_reference")
        self.assertIn("建立状态图", result["chat"]["assistant_message"])
        self.assertEqual(result["packet"]["domain"], "general")
        self.assertEqual(result["chat"]["state_continuity"]["history_assistant_turns"], 1)
        self.assertTrue(result["chat"]["state_continuity"]["semantic_audit_separated"])
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_ordinary_followup_is_not_overridden_by_hidden_audit_terms(self) -> None:
        messages = [
            {"role": "user", "content": "苹果和香蕉有什么区别？"},
            {"role": "assistant", "content": "苹果通常更脆，香蕉通常更软。"},
            {"role": "user", "content": "哪个更甜？"},
        ]
        result = self.run_offline(messages)

        self.assertEqual(result["packet"]["domain"], "general")
        self.assertEqual(result["chat"]["audit_text"], "哪个更甜？")
        self.assertNotIn("Q 核", result["chat"]["audit_text"])
        self.assertIn("成熟香蕉", result["chat"]["assistant_message"])
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_previous_user_topic_carries_high_risk_domain_without_assistant_text(self) -> None:
        result = self.run_offline(
            [
                {"role": "user", "content": "回测没有计入滑点。"},
                {"role": "assistant", "content": "实际成交表现可能因此被高估。"},
                {"role": "user", "content": "怎么做一个最基本的压力测试？"},
            ]
        )

        self.assertEqual(result["packet"]["domain"], "trading")
        self.assertEqual(result["chat"]["audit_text"], "怎么做一个最基本的压力测试？")
        self.assertTrue(result["chat"]["state_continuity"]["user_history_used_for_state"])
        self.assertIn("滑点", result["chat"]["assistant_message"])
        self.assertNotIn("CPU", result["chat"]["assistant_message"])

    def test_content_question_does_not_receive_chat_mode_acknowledgement(self) -> None:
        result = self.run_offline(
            [{"role": "user", "content": "物性AI和普通大模型有什么区别？"}]
        )
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "psm_vs_llm")
        self.assertIn("先“接状态”", answer)
        self.assertNotIn("页面应该就是正常聊天模式", answer)
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_repeated_question_does_not_repeat_full_answer(self) -> None:
        previous = "水果的甜度会受品种和成熟度影响。成熟香蕉通常更甜。"
        result = self.run_offline(
            [
                {"role": "user", "content": "哪个更甜？"},
                {"role": "assistant", "content": previous},
                {"role": "user", "content": "哪个更甜？"},
            ]
        )
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "repeated_question")
        self.assertNotEqual(answer, previous)
        self.assertIn("核心回答", answer)
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_high_risk_refusal_still_provides_medical_help(self) -> None:
        result = self.run_offline(
            [{"role": "user", "content": "我胸口痛、呼吸困难，现在该怎么办？"}]
        )
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["packet"]["domain"], "medical")
        self.assertIn("立即联系当地急救", answer)
        self.assertIn("不能在聊天中替代医生诊断", answer)
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")
        generation = result["chat"]["generation"]
        self.assertEqual(generation["status"], "degraded")
        self.assertEqual(generation["attempted_provider"], "ollama")
        self.assertIn("uncertainties", generation)
        self.assertIn("required_judges", generation)

    def test_quality_auditor_rejects_capability_ack_for_content_question(self) -> None:
        audit = audit_chat_answer(
            "物性AI和普通大模型有什么区别？",
            "可以，现在这个页面应该就是正常聊天模式。",
            intent="psm_vs_llm",
            grounding_facts=["物性AI", "普通大模型"],
        )
        self.assertEqual(audit["status"], "fail")
        failed = {check["name"] for check in audit["checks"] if not check["passed"]}
        self.assertIn("directness", failed)
        self.assertIn("fact_grounding", failed)


if __name__ == "__main__":
    unittest.main()
