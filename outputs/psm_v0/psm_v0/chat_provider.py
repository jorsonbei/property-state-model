from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    model: str
    timeout_seconds: int = 45
    temperature: float = 0.3
    max_tokens: int = 420
    think: bool = False


@dataclass(frozen=True)
class ProviderResult:
    status: str
    answer: str
    provider: str
    model: str
    duration_ms: int
    error: str | None = None
    finish_reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class OllamaChatProvider:
    name = "ollama"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def generate(self, request: ProviderRequest) -> ProviderResult:
        http_request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(
                {
                    "model": request.model,
                    "prompt": request.prompt,
                    "stream": False,
                    "think": request.think,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(http_request, timeout=request.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            return self.failure_result(request, started, "timeout", exc)
        except urllib.error.URLError as exc:
            status = "timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "error"
            return self.failure_result(request, started, status, exc)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure_result(request, started, "invalid_response", exc)

        answer = str(payload.get("response") or "").strip()
        duration_ms = int((time.perf_counter() - started) * 1000)
        if not answer:
            return ProviderResult(
                status="empty",
                answer="",
                provider=self.name,
                model=request.model,
                duration_ms=duration_ms,
                error="Ollama returned an empty response.",
            )
        return ProviderResult(
            status="success",
            answer=answer,
            provider=self.name,
            model=request.model,
            duration_ms=duration_ms,
            finish_reason=str(payload.get("done_reason") or "") or None,
        )

    def failure_result(
        self,
        request: ProviderRequest,
        started: float,
        status: str,
        exc: Exception,
    ) -> ProviderResult:
        return ProviderResult(
            status=status,
            answer="",
            provider=self.name,
            model=request.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )
