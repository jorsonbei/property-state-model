from __future__ import annotations

import unittest
from unittest.mock import patch

from product_alpha_app import server
from psm_v0.chat_prompt import sanitize_model_answer
from psm_v0.chat_provider import ProviderResult


class ChatProviderTests(unittest.TestCase):
    def test_provider_result_has_stable_transport_fields(self) -> None:
        result = ProviderResult(
            status="success",
            answer="直接回答",
            provider="ollama",
            model="example:1b",
            duration_ms=123,
        ).to_dict()
        self.assertEqual(
            set(result),
            {"status", "answer", "provider", "model", "duration_ms", "error", "finish_reason"},
        )
        self.assertIsNone(result["finish_reason"])

    def test_sanitizer_removes_reasoning_block_and_emoji(self) -> None:
        answer, leak = sanitize_model_answer("<think>内部推理</think>最终回答。🙂")
        self.assertTrue(leak)
        self.assertEqual(answer, "最终回答。")

    def test_sanitizer_drops_unclosed_reasoning_block(self) -> None:
        answer, leak = sanitize_model_answer("<think>被 token 上限截断的内部推理")
        self.assertTrue(leak)
        self.assertEqual(answer, "")

    def test_generation_retries_once_when_ollama_hits_token_limit(self) -> None:
        first = ProviderResult(
            status="success",
            answer="未完成",
            provider="ollama",
            model="example:1b",
            duration_ms=10,
            finish_reason="length",
        )
        second = ProviderResult(
            status="success",
            answer="完整回答。",
            provider="ollama",
            model="example:1b",
            duration_ms=20,
            finish_reason="stop",
        )
        result = server.run_demo_case("请解释一个普通概念。", "review")
        with patch.object(server, "selected_chat_model", return_value="example:1b"), patch.object(
            server, "selected_chat_max_tokens", return_value=300
        ), patch.object(server.OllamaChatProvider, "generate", side_effect=[first, second]) as generate:
            generation = server.try_ollama_chat_generation(
                "请解释一个普通概念。",
                [{"role": "user", "content": "请解释一个普通概念。"}],
                result,
            )
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(generate.call_args_list[0].args[0].max_tokens, 300)
        self.assertEqual(generate.call_args_list[1].args[0].max_tokens, 600)
        self.assertEqual(generation["answer"], "完整回答。")
        self.assertTrue(generation["truncation_retry"])
        self.assertEqual(generation["duration_ms"], 30)


if __name__ == "__main__":
    unittest.main()
