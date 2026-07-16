#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_292_server_cancel_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_292_server_cancel_runtime_report.json"
GATE = PSM_ROOT / "runtime" / "v0_292_server_cancel_runtime_gate.json"
RUNTIMES = (
    {"runtime_id": "host", "base_url": "http://127.0.0.1:8765"},
    {"runtime_id": "docker", "base_url": "http://127.0.0.1:8766"},
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request_json(base_url: str, path: str, payload: dict | None = None, timeout: int = 90) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def chat_payload(runtime_id: str, request_id: str, prompt: str) -> dict:
    return {
        "request_id": request_id,
        "scenario": "review",
        "session_id": f"v292_{runtime_id}_{uuid.uuid4().hex}",
        "continuity_event": "active",
        "messages": [{"id": 1, "role": "user", "content": prompt}],
    }


def cancel_once(base_url: str, runtime_id: str, index: int, sentinel: str) -> dict:
    request_id = f"chat_v292_{runtime_id}_{index}_{uuid.uuid4().hex}"
    payload = chat_payload(
        runtime_id,
        request_id,
        f"请详细设计一个全新的本地知识管理项目，包括名称、架构和三个阶段。校验符 {sentinel}",
    )
    result: dict = {}

    def run_chat() -> None:
        started = time.perf_counter()
        status, body = request_json(base_url, "/api/chat", payload)
        result.update(
            chat_status=status,
            chat_body=body,
            chat_total_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    thread = threading.Thread(target=run_chat)
    thread.start()
    time.sleep(2)
    cancel_started = time.perf_counter()
    cancel_status, cancel_body = request_json(
        base_url,
        "/api/chat-cancel",
        {"request_id": request_id},
    )
    cancel_ack_ms = round((time.perf_counter() - cancel_started) * 1000, 2)
    thread.join(5)
    stop_ms = round((time.perf_counter() - cancel_started) * 1000, 2)
    checks = {
        "cancel_ack_200": cancel_status == 200,
        "active_request_acknowledged": cancel_body.get("accepted") is True and cancel_body.get("active") is True,
        "chat_thread_stopped": not thread.is_alive(),
        "chat_returned_499": result.get("chat_status") == 499,
        "cancel_error_exact": result.get("chat_body") == {"error": "chat_cancelled", "request_id": request_id},
        "partial_answer_not_released": "answer" not in result.get("chat_body", {}),
    }
    return {
        "case_id": f"{runtime_id}-cancel-{index}",
        "request_id": request_id,
        "cancel_ack_ms": cancel_ack_ms,
        "server_stop_ms": stop_ms,
        "cancel_status": cancel_status,
        "cancel_body": cancel_body,
        "chat_status": result.get("chat_status"),
        "chat_body": result.get("chat_body"),
        "chat_total_ms": result.get("chat_total_ms"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def retry_after_cancel(base_url: str, runtime_id: str) -> dict:
    request_id = f"chat_v292_retry_{runtime_id}_{uuid.uuid4().hex}"
    started = time.perf_counter()
    status, body = request_json(
        base_url,
        "/api/chat",
        chat_payload(runtime_id, request_id, "请给一个新的本地知识项目起代号，并说明理由。"),
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    generation = body.get("chat", {}).get("generation", {})
    answer = str(body.get("chat", {}).get("assistant_message") or "")
    checks = {
        "status_200": status == 200,
        "answer_nonempty": bool(answer.strip()),
        "ollama_success": generation.get("provider") == "ollama" and generation.get("status") == "success",
        "fallback_not_used": generation.get("attempted_provider") is None,
        "sigma_plus_passed": body.get("sigma_plus_delivery", {}).get("passed") is True,
    }
    return {
        "status": status,
        "duration_ms": duration_ms,
        "provider": generation.get("provider"),
        "generation_status": generation.get("status"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def sentinel_hits(sentinel: str) -> list[str]:
    hits = []
    for path in PSM_ROOT.rglob("*"):
        if not path.is_file() or path == REPORT:
            continue
        try:
            if sentinel in path.read_text(encoding="utf-8"):
                hits.append(str(path.relative_to(PSM_ROOT)))
        except (UnicodeDecodeError, OSError):
            continue
    return hits


def main() -> None:
    contract = read(CONTRACT)
    stop_limit = contract["acceptance"]["cancel_to_server_stop_limit_ms"]
    sentinel = f"V292-NO-DISK-{uuid.uuid4().hex}"
    runtimes = []
    for runtime in RUNTIMES:
        status_code, status = request_json(runtime["base_url"], "/api/status")
        cancel_rows = [
            cancel_once(runtime["base_url"], runtime["runtime_id"], index + 1, sentinel)
            for index in range(3)
        ]
        retry = retry_after_cancel(runtime["base_url"], runtime["runtime_id"])
        checks = {
            "status_available": status_code == 200,
            "source_version_valid": status.get("version") in {"PSM V0.291", "PSM V0.292"},
            "all_cancellations_pass": all(row["passed"] for row in cancel_rows),
            "all_server_stops_within_limit": all(row["server_stop_ms"] <= stop_limit for row in cancel_rows),
            "retry_after_cancel_passes": retry["passed"],
            "external_release_closed": status.get("ready_for_external_user_trial") is False,
        }
        runtimes.append({
            **runtime,
            "version": status.get("version"),
            "cancel_rows": cancel_rows,
            "cancel_max_ms": max(row["server_stop_ms"] for row in cancel_rows),
            "retry": retry,
            "checks": checks,
            "passed": all(checks.values()),
        })
    disk_hits = sentinel_hits(sentinel)
    checks = {
        "contract_frozen": contract.get("frozen_before_implementation") is True,
        "host_passed": runtimes[0]["passed"],
        "docker_passed": runtimes[1]["passed"],
        "six_of_six_cancelled": sum(row["passed"] for runtime in runtimes for row in runtime["cancel_rows"]) == 6,
        "cancelled_content_not_persisted": not disk_hits,
        "raw_chunks_not_user_visible": contract["delivery_contract"]["raw_model_chunks_user_visible"] is False,
        "network_token_streaming_not_claimed": contract["delivery_contract"]["network_token_streaming_claimed"] is False,
        "external_release_closed": contract["release_boundary"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_292_server_cancel_runtime_report_v1",
        "version": "PSM_V0.292-candidate",
        "contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "runtimes": runtimes,
        "disk_sentinel_hits": disk_hits,
        "checks": checks,
        "passed": all(checks.values()),
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "network_token_streaming_claimed": False,
        "external_release_authority": False,
    }
    gate = {
        "schema_version": "psm_v0_292_server_cancel_runtime_gate_v1",
        "decision": "server_cancel_runtime_gate_passed" if report["passed"] else "server_cancel_runtime_gate_failed",
        "passed": report["passed"],
        "checks": checks,
        "host_cancel_max_ms": runtimes[0]["cancel_max_ms"],
        "docker_cancel_max_ms": runtimes[1]["cancel_max_ms"],
        "stop_limit_ms": stop_limit,
        "external_release_authority": False,
    }
    write(REPORT, report)
    write(GATE, gate)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
