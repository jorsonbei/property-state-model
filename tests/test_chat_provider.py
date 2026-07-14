from __future__ import annotations

import unittest

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
            {"status", "answer", "provider", "model", "duration_ms", "error"},
        )

    def test_sanitizer_removes_reasoning_block_and_emoji(self) -> None:
        answer, leak = sanitize_model_answer("<think>内部推理</think>最终回答。🙂")
        self.assertTrue(leak)
        self.assertEqual(answer, "最终回答。")

    def test_sanitizer_drops_unclosed_reasoning_block(self) -> None:
        answer, leak = sanitize_model_answer("<think>被 token 上限截断的内部推理")
        self.assertTrue(leak)
        self.assertEqual(answer, "")


if __name__ == "__main__":
    unittest.main()
