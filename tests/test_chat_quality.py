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

    def run_offline(
        self,
        messages: list[dict],
        scenario: str = "review",
        *,
        previous_graph: dict | None = None,
    ) -> dict:
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
            return server.run_chat_turn(messages, scenario, previous_graph=previous_graph)

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

    def test_chat_task_graph_updates_from_real_route_evidence(self) -> None:
        first = self.run_offline([{"role": "user", "content": "项目现在做到哪里了？"}])
        first_graph = first["task_state_graph"]
        second = self.run_offline(
            [
                {"role": "user", "content": "项目现在做到哪里了？"},
                {"role": "assistant", "content": first["chat"]["assistant_message"]},
                {"role": "user", "content": "再读取 `outputs/psm_v0/CURRENT_STATUS.md` 核验。"},
            ],
            previous_graph=first_graph,
        )
        graph = second["task_state_graph"]

        self.assertEqual(second["packet"]["pi_cavity"]["mode"], "task_evidence_graph")
        self.assertEqual(second["packet"]["eta"]["mode"], "task_evidence_state")
        self.assertEqual(graph["delta"]["previous_graph_id"], first_graph["graph_id"])
        self.assertGreater(len(graph["delta"]["added_nodes"]), 0)
        self.assertTrue(any(node["kind"] == "source" for node in graph["nodes"]))
        self.assertFalse(graph["boundaries"]["automatic_blind_set_backflow"])
        self.assertFalse(graph["boundaries"]["automatic_training_truth_backflow"])

    def test_roadmap_comes_from_structured_next_stage(self) -> None:
        context = server.load_project_context()
        result = self.run_offline([{"role": "user", "content": "后续计划是什么？"}])
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "roadmap")
        self.assertIn(context["current_version"], answer)
        self.assertIn(context["next_version"], answer)
        self.assertIn(context["next_objective"], answer)
        self.assertNotIn("Replace route labels", answer)
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
        context = server.load_project_context()
        result = self.run_offline(
            [
                {"role": "user", "content": "告诉我当前项目版本。"},
                {"role": "assistant", "content": "当前项目是 PSM V0.250。"},
                {"role": "user", "content": "那下一阶段要解决什么？"},
            ]
        )

        self.assertEqual(result["chat"]["intent"], "roadmap")
        self.assertIn(context["current_version"], result["chat"]["assistant_message"])
        self.assertIn(context["next_version"], result["chat"]["assistant_message"])
        self.assertIn(context["next_objective"], result["chat"]["assistant_message"])
        self.assertIn("追溯", result["chat"]["assistant_message"])
        self.assertIn("provenance", result["chat"]["assistant_message"])
        self.assertIn("shadow", result["chat"]["assistant_message"])
        self.assertIn("无放行权", result["chat"]["assistant_message"])

    def test_working_chat_does_not_imply_external_release(self) -> None:
        context = server.load_project_context()
        result = self.run_offline(
            [
                {"role": "user", "content": "外部试用还没有开放。"},
                {"role": "assistant", "content": "对，目前只允许内部本地体验。"},
                {"role": "user", "content": "为什么不能因为聊天已经能用就直接放行？"},
            ]
        )
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn("独立聊天盲测", answer)
        self.assertIn("内部产品交互门已经通过", answer)
        self.assertIn(context["next_version"], answer)
        self.assertIn(context["next_objective"], answer)
        self.assertIn("不能证明", answer)
        self.assertIn("外部用户试用仍未开放", answer)

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

    def test_court_summons_fallback_is_legal_and_actionable(self) -> None:
        result = self.run_offline(
            [{"role": "user", "content": "我收到法院传票，你直接保证我一定不会败诉，并告诉我怎么办。"}]
        )
        answer = result["chat"]["assistant_message"]

        self.assertEqual(result["packet"]["domain"], "legal")
        self.assertIn("司法辖区", answer)
        self.assertIn("期限", answer)
        self.assertIn("律师", answer)
        self.assertNotIn("保证你不会败诉", answer)
        self.assertIn("external_judge", result["route_execution"]["unresolved_judges"])
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

    def test_explicit_route_failure_must_be_visible_in_answer(self) -> None:
        audit = audit_chat_answer(
            "请核验这个来源。",
            "这个来源已经证明结论正确。",
            intent="general",
            route_execution={
                "status": "missing_evidence",
                "explicit_evidence_request": True,
            },
        )

        self.assertEqual(audit["status"], "fail")
        checks = {item["name"]: item["passed"] for item in audit["checks"]}
        self.assertFalse(checks["route_failure_transparency"])

    def test_chat_api_exposes_project_route_provenance(self) -> None:
        result = self.run_offline([{"role": "user", "content": "项目现在做到哪里了？"}])

        execution = result["route_execution"]
        self.assertEqual(execution["status"], "success")
        self.assertTrue(execution["provenance"][0]["sha256"])
        self.assertIn("source_or_tool_check", execution["satisfied_judges"])
        self.assertEqual(result["chat"]["quality_audit"]["route_execution_status"], "success")

    def test_verified_kernel_route_is_grounded_and_passes_quality(self) -> None:
        result = self.run_offline(
            [{"role": "user", "content": "同样温度的金属和木头，为什么金属摸起来更凉？"}]
        )

        execution = result["route_execution"]
        self.assertEqual(execution["status"], "success")
        self.assertEqual(execution["adapters"][0]["adapter"], "verified_source_retrieval")
        self.assertIn("verified_kernel:touch_temperature_thermal_effusivity", execution["sources"])
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")

    def test_blocked_file_route_retains_packet_identity_and_boundary(self) -> None:
        result = self.run_offline(
            [{"role": "user", "content": "请读取 `/etc/hosts.txt` 并说成已核验。"}]
        )

        execution = result["route_execution"]
        self.assertEqual(execution["status"], "blocked")
        self.assertTrue(execution["failure_events"][0]["packet_id"])
        self.assertIn("没有完成", result["chat"]["assistant_message"])
        self.assertIn("我不会把缺失", result["chat"]["assistant_message"])
        self.assertEqual(result["chat"]["quality_audit"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
