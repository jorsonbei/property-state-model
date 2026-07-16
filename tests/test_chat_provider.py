from __future__ import annotations

import json
import threading
import unittest
from unittest.mock import patch

from product_alpha_app import server
from psm_v0.chat_prompt import sanitize_model_answer
from psm_v0.chat_provider import OllamaChatProvider, ProviderRequest, ProviderResult


class FakeStreamResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines

    def __enter__(self) -> FakeStreamResponse:
        return self

    def __exit__(self, *args) -> None:
        return None

    def __iter__(self):
        return iter(self.lines)


class CancellingStreamResponse(FakeStreamResponse):
    def __init__(self, lines: list[bytes], cancel_event: threading.Event) -> None:
        super().__init__(lines)
        self.cancel_event = cancel_event

    def __iter__(self):
        yield self.lines[0]
        self.cancel_event.set()
        yield self.lines[1]


class FakeConnection:
    def __init__(self, response: FakeStreamResponse) -> None:
        self.response = response
        self.sock = None
        self.request_call: tuple | None = None

    def request(self, method, path, *, body, headers) -> None:
        self.request_call = (method, path, body, headers)

    def getresponse(self) -> FakeStreamResponse:
        self.response.status = 200
        return self.response

    def close(self) -> None:
        return None


class ChatProviderTests(unittest.TestCase):
    def test_ollama_internal_stream_joins_chunks_without_releasing_partial_data(self) -> None:
        response = FakeStreamResponse([
            b'{"response":"first ","done":false}\n',
            b'{"response":"answer","done":true,"done_reason":"stop"}\n',
        ])
        connection = FakeConnection(response)
        provider = OllamaChatProvider("http://ollama.test")
        with patch.object(provider, "open_connection", return_value=connection):
            result = provider.generate(
                ProviderRequest(prompt="test", model="model:1b")
            )
        sent = json.loads(connection.request_call[2].decode("utf-8"))
        self.assertTrue(sent["stream"])
        self.assertEqual(connection.request_call[:2], ("POST", "/api/generate"))
        self.assertEqual(result.status, "success")
        self.assertEqual(result.answer, "first answer")
        self.assertEqual(result.finish_reason, "stop")

    def test_ollama_cancel_discards_all_buffered_chunks(self) -> None:
        cancel_event = threading.Event()
        response = CancellingStreamResponse([
            b'{"response":"must never be released","done":false}\n',
            b'{"response":"ignored","done":false}\n',
        ], cancel_event)
        connection = FakeConnection(response)
        provider = OllamaChatProvider("http://ollama.test")
        with patch.object(provider, "open_connection", return_value=connection):
            result = provider.generate(
                ProviderRequest(prompt="test", model="model:1b"),
                cancel_event=cancel_event,
            )
        self.assertEqual(result.status, "cancelled")
        self.assertEqual(result.answer, "")
        self.assertEqual(result.finish_reason, "cancelled")

    def test_provider_request_disables_hidden_thinking_by_default(self) -> None:
        request = ProviderRequest(prompt="问题", model="example:1b")
        self.assertFalse(request.think)

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
        ), patch.object(
            server, "selected_chat_timeout_seconds", return_value=60
        ), patch.object(server.OllamaChatProvider, "generate", side_effect=[first, second]) as generate:
            generation = server.try_ollama_chat_generation(
                "请解释一个普通概念。",
                [{"role": "user", "content": "请解释一个普通概念。"}],
                result,
            )
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(generate.call_args_list[0].args[0].max_tokens, 300)
        self.assertEqual(generate.call_args_list[1].args[0].max_tokens, 600)
        self.assertEqual(generate.call_args_list[0].args[0].timeout_seconds, 60)
        self.assertEqual(generate.call_args_list[1].args[0].timeout_seconds, 60)
        self.assertEqual(generation["answer"], "完整回答。")
        self.assertTrue(generation["truncation_retry"])
        self.assertEqual(generation["duration_ms"], 30)

    def test_cancelled_model_generation_never_becomes_fallback_answer(self) -> None:
        result = server.run_demo_case("请拟一个新项目名称。", "review")
        cancelled = ProviderResult(
            status="cancelled",
            answer="",
            provider="ollama",
            model="example:1b",
            duration_ms=5,
            finish_reason="cancelled",
        )
        with patch.object(server.OllamaChatProvider, "generate", return_value=cancelled):
            with self.assertRaises(server.ChatCancelled):
                server.build_chat_generation(
                    "请拟一个新项目名称。",
                    [{"role": "user", "content": "请拟一个新项目名称。"}],
                    result,
                    "general",
                    {},
                )


if __name__ == "__main__":
    unittest.main()
