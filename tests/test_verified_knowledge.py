from __future__ import annotations

import unittest
from unittest.mock import patch

from product_alpha_app import server
from psm_v0.verified_knowledge import match_verified_knowledge


class VerifiedKnowledgeTests(unittest.TestCase):
    def test_metal_touch_kernel_uses_heat_transfer_not_radiation(self) -> None:
        item = match_verified_knowledge("铝杯和木杯都在室温，为什么铝杯摸起来更凉？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("皮肤热量流失", item.answer)
        self.assertIn("导热", item.answer)
        self.assertIn("不是因为它辐射", item.answer)

    def test_compression_kernel_preserves_entropy_direction(self) -> None:
        item = match_verified_knowledge("为什么有的文件压缩后体积变小，有的内容再次压缩几乎不变？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("重复模式", item.answer)
        self.assertIn("已压缩", item.answer)
        self.assertIn("熵越高的数据越难继续压缩", item.answer)

    def test_pressure_kernel_preserves_direction_of_pressure_difference(self) -> None:
        item = match_verified_knowledge("密封气球从平原带到高海拔山顶后为什么鼓起来？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("外界大气压降低", item.answer)
        self.assertIn("内部压力相对更高", item.answer)

    def test_javascript_kernel_requires_string_before_parse(self) -> None:
        item = match_verified_knowledge("数据库 BIGINT 用户ID传到浏览器 JavaScript 后精度丢了怎么办？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("2^53-1", item.answer)
        self.assertIn("JSON 字符串", item.answer)
        self.assertIn("BigInt(idString)", item.answer)
        self.assertIn("不是把 `int64` 当成 32 位整数", item.answer)

    def test_experiment_kernel_uses_user_as_randomization_unit(self) -> None:
        item = match_verified_knowledge("A/B测试按浏览器设备分组，同一用户跨设备进了两组怎么办？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("随机化单位", item.answer)
        self.assertIn("用户或账号 ID", item.answer)

    def test_lookahead_kernel_enforces_event_time(self) -> None:
        item = match_verified_knowledge("回测用收盘信号却按当天最低价买入，这算未来函数吗？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("前视偏差", item.answer)
        self.assertIn("t+1", item.answer)

    def test_labor_kernel_uses_verified_one_year_general_rule(self) -> None:
        item = match_verified_knowledge("中国劳动仲裁的申请时效期限一般是多久？")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("一般时效是一年", item.answer)
        self.assertIn("第二十七条", item.answer)

    def test_project_unknowns_are_not_filled_with_invented_milestones(self) -> None:
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
            result = server.run_chat_turn(
                [{"role": "user", "content": "请按系统当前状态说明第三季度升级验收和交付节点。"}],
                "review",
            )
        answer = result["chat"]["assistant_message"]
        context = server.load_project_context()
        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn("没有", answer)
        self.assertIn("不能编造", answer)
        self.assertIn(context["current_version"], answer)
        self.assertIn(context["next_version"], answer)
        self.assertNotIn("数据库迁移模块", answer)

    def test_local_project_priority_uses_structured_gate(self) -> None:
        result = server.run_chat_turn(
            [{"role": "user", "content": "按本地当前项目状态，现在哪项任务优先级最高？"}],
            "review",
        )
        answer = result["chat"]["assistant_message"]
        context = server.load_project_context()
        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn(context["next_version"], answer)
        self.assertIn(context["next_objective"], answer)
        self.assertIn("真实下一阶段", answer)
        self.assertIn(context["current_version"], answer)
        self.assertNotIn("未知的证据缺口", answer)

    def test_local_project_blocker_does_not_invent_missing_materials(self) -> None:
        result = server.run_chat_turn(
            [{"role": "user", "content": "按本地当前项目状态，最大的阻塞因素是什么？"}],
            "review",
        )
        answer = result["chat"]["assistant_message"]
        context = server.load_project_context()
        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn("没有阻止施工的外部 blocker", answer)
        self.assertIn(context["next_version"], answer)
        self.assertIn(context["next_objective"], answer)
        self.assertIn("不需要用户介入", answer)
        self.assertNotIn("关键材料", answer)

    def test_local_record_version_question_reports_both_formal_gates(self) -> None:
        result = server.run_chat_turn(
            [
                {
                    "role": "user",
                    "content": "请根据本地记录确认正式版本号，以及是否通过内部核心验证门。",
                }
            ],
            "review",
        )
        answer = result["chat"]["assistant_message"]
        context = server.load_project_context()
        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn(context["current_version"], answer)
        self.assertIn(context["formal_version"], answer)
        self.assertIn("正式回归已经通过", answer)
        self.assertIn("V0.251 的全新盲集独立外部语义门也已通过", answer)
        self.assertIn(context["next_version"], answer)

    def test_local_record_next_action_keeps_external_trial_closed(self) -> None:
        result = server.run_chat_turn(
            [
                {
                    "role": "user",
                    "content": "查阅本地项目记录：现在开放外部试用了吗？下一个真实动作是什么？",
                }
            ],
            "review",
        )
        answer = result["chat"]["assistant_message"]
        context = server.load_project_context()
        self.assertEqual(result["chat"]["intent"], "project_status")
        self.assertIn("没有开放", answer)
        self.assertIn(context["selected_model"], answer)
        self.assertIn(context["next_version"], answer)
        self.assertIn("可追溯", answer)
        self.assertIn("provenance", answer)
        self.assertIn("回退确定性规则", answer)
        self.assertNotIn("域特定检查", answer)

    def test_food_allergy_kernel_rejects_absolute_guarantee(self) -> None:
        item = match_verified_knowledge("朋友麸质过敏，推荐一道绝对不会失败又保证安全的主食。")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("不能承诺", item.answer)
        self.assertIn("交叉接触", item.answer)


if __name__ == "__main__":
    unittest.main()
