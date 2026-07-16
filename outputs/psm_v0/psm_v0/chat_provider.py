from __future__ import annotations

import http.client
import json
import socket
import threading
import time
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit


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
        self.parsed_base_url = urlsplit(self.base_url)

    def generate(
        self,
        request: ProviderRequest,
        *,
        cancel_event: threading.Event | None = None,
    ) -> ProviderResult:
        body = json.dumps(
            {
                "model": request.model,
                "prompt": request.prompt,
                "stream": True,
                "think": request.think,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
        started = time.perf_counter()
        chunks: list[str] = []
        final_payload: dict = {}
        stream_finished = threading.Event()
        connection = self.open_connection(request.timeout_seconds)
        try:
            if cancel_event is not None and cancel_event.is_set():
                return self.cancelled_result(request, started)
            path = f"{self.parsed_base_url.path.rstrip('/')}/api/generate"
            connection.request(
                "POST",
                path,
                body=body,
                headers={"Content-Type": "application/json"},
            )
            if cancel_event is not None:
                threading.Thread(
                    target=self.close_connection_when_cancelled,
                    args=(connection, cancel_event, stream_finished),
                    daemon=True,
                ).start()
            with connection.getresponse() as response:
                if response.status >= 400:
                    error_body = response.read().decode("utf-8", errors="replace")[:500]
                    raise http.client.HTTPException(
                        f"Ollama returned HTTP {response.status}: {error_body}"
                    )
                for raw_line in response:
                    if cancel_event is not None and cancel_event.is_set():
                        return self.cancelled_result(request, started)
                    if not raw_line.strip():
                        continue
                    payload = json.loads(raw_line.decode("utf-8"))
                    chunks.append(str(payload.get("response") or ""))
                    final_payload = payload
                    if payload.get("done") is True:
                        break
                if cancel_event is not None and cancel_event.is_set():
                    return self.cancelled_result(request, started)
        except (TimeoutError, socket.timeout) as exc:
            if cancel_event is not None and cancel_event.is_set():
                return self.cancelled_result(request, started)
            return self.failure_result(request, started, "timeout", exc)
        except (http.client.HTTPException, ConnectionError) as exc:
            if cancel_event is not None and cancel_event.is_set():
                return self.cancelled_result(request, started)
            return self.failure_result(request, started, "error", exc)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure_result(request, started, "invalid_response", exc)
        except (OSError, ValueError) as exc:
            if cancel_event is not None and cancel_event.is_set():
                return self.cancelled_result(request, started)
            return self.failure_result(request, started, "error", exc)
        finally:
            stream_finished.set()
            connection.close()

        answer = "".join(chunks).strip()
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
            finish_reason=str(final_payload.get("done_reason") or "") or None,
        )

    def cancelled_result(self, request: ProviderRequest, started: float) -> ProviderResult:
        return ProviderResult(
            status="cancelled",
            answer="",
            provider=self.name,
            model=request.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            finish_reason="cancelled",
        )

    def open_connection(
        self,
        timeout_seconds: int,
    ) -> http.client.HTTPConnection:
        if self.parsed_base_url.scheme not in {"http", "https"}:
            raise ValueError("Ollama base URL must use http or https.")
        connection_type = (
            http.client.HTTPSConnection
            if self.parsed_base_url.scheme == "https"
            else http.client.HTTPConnection
        )
        return connection_type(
            self.parsed_base_url.hostname,
            self.parsed_base_url.port,
            timeout=timeout_seconds,
        )

    @staticmethod
    def close_connection_when_cancelled(
        connection: http.client.HTTPConnection,
        cancel_event: threading.Event,
        stream_finished: threading.Event,
    ) -> None:
        while not stream_finished.wait(0.025):
            if cancel_event.is_set():
                try:
                    transport_socket = connection.sock
                    if transport_socket is None:
                        return
                    transport_socket.shutdown(socket.SHUT_RDWR)
                    transport_socket.close()
                except (AttributeError, OSError, ValueError):
                    pass
                try:
                    connection.close()
                except (OSError, ValueError):
                    pass
                return

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
