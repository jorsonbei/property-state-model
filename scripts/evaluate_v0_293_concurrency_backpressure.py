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
CONTRACT = PSM_ROOT / "benchmarks" / "v0_293_concurrency_backpressure_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_293_concurrency_backpressure_report.json"
GATE = PSM_ROOT / "runtime" / "v0_293_concurrency_backpressure_gate.json"
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


def payload(runtime_id: str, request_id: str | None, prompt: str) -> dict:
    value = {
        "scenario": "review",
        "session_id": f"v293_{runtime_id}_{uuid.uuid4().hex}",
        "continuity_event": "active",
        "messages": [{"id": 1, "role": "user", "content": prompt}],
    }
    if request_id is not None:
        value["request_id"] = request_id
    return value


def run_wave(base_url: str, runtime_id: str, wave: int, contract: dict, sentinel: str) -> dict:
    active_count = contract["admission"]["max_active_chat_requests"]
    request_ids = [f"chat_v293_{runtime_id}_{wave}_{index}_{uuid.uuid4().hex}" for index in range(active_count)]
    chat_results: list[dict] = [{} for _ in request_ids]
    start_barrier = threading.Barrier(active_count + 1)

    def run_chat(index: int) -> None:
        start_barrier.wait()
        started = time.perf_counter()
        status, body = request_json(
            base_url,
            "/api/chat",
            payload(
                runtime_id,
                request_ids[index],
                f"请详细设计一个新的本地资料系统，给出名称、架构、阶段和风险。{sentinel}",
            ),
        )
        chat_results[index] = {
            "status": status,
            "body": body,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    chat_threads = [threading.Thread(target=run_chat, args=(index,)) for index in range(active_count)]
    for thread in chat_threads:
        thread.start()
    start_barrier.wait()
    time.sleep(1)

    duplicate_started = time.perf_counter()
    duplicate_status, duplicate_body = request_json(
        base_url,
        "/api/chat",
        payload(runtime_id, request_ids[0], "重复请求不应进入执行。"),
    )
    duplicate_ms = round((time.perf_counter() - duplicate_started) * 1000, 2)

    capacity_started = time.perf_counter()
    capacity_status, capacity_body = request_json(
        base_url,
        "/api/chat",
        payload(runtime_id, None, "无客户端 ID 的第五个请求也必须受容量门控制。"),
    )
    capacity_ms = round((time.perf_counter() - capacity_started) * 1000, 2)

    cancel_started = time.perf_counter()
    cancel_results: list[dict] = [{} for _ in request_ids]

    def cancel(index: int) -> None:
        status, body = request_json(
            base_url,
            "/api/chat-cancel",
            {"request_id": request_ids[index]},
        )
        cancel_results[index] = {"status": status, "body": body}

    cancel_threads = [threading.Thread(target=cancel, args=(index,)) for index in range(active_count)]
    for thread in cancel_threads:
        thread.start()
    for thread in cancel_threads:
        thread.join(3)
    for thread in chat_threads:
        thread.join(5)
    stop_ms = round((time.perf_counter() - cancel_started) * 1000, 2)

    repeated_cancels = [
        request_json(base_url, "/api/chat-cancel", {"request_id": request_id})
        for request_id in request_ids
    ]
    recovery_status, recovery_body = request_json(
        base_url,
        "/api/chat",
        payload(runtime_id, None, "你好，你是谁？"),
    )
    checks = {
        "duplicate_rejected_409": duplicate_status == 409 and duplicate_body.get("error") == "duplicate_request_id",
        "duplicate_fast": duplicate_ms <= contract["admission"]["capacity_response_limit_ms"],
        "capacity_rejected_503": capacity_status == 503 and capacity_body.get("error") == "chat_capacity_reached",
        "capacity_retry_hint_exact": capacity_body.get("retry_after_seconds") == contract["admission"]["capacity_retry_after_seconds"],
        "capacity_fast": capacity_ms <= contract["admission"]["capacity_response_limit_ms"],
        "all_active_cancels_acknowledged": all(
            item.get("status") == 200 and item.get("body", {}).get("active") is True
            for item in cancel_results
        ),
        "all_workers_stopped": all(not thread.is_alive() for thread in chat_threads),
        "all_chat_responses_cancelled": all(
            item.get("status") == 499 and item.get("body", {}).get("error") == "chat_cancelled" and "answer" not in item.get("body", {})
            for item in chat_results
        ),
        "cancel_storm_within_limit": stop_ms <= contract["cancel_storm"]["cancel_to_worker_stop_limit_ms"],
        "repeat_cancel_idempotent": all(
            status == 200 and body.get("accepted") is True and body.get("active") is False
            for status, body in repeated_cancels
        ),
        "capacity_recovers": recovery_status == 200 and bool(recovery_body.get("chat", {}).get("assistant_message")),
    }
    return {
        "wave": wave,
        "request_ids": request_ids,
        "duplicate_probe": {"status": duplicate_status, "body": duplicate_body, "duration_ms": duplicate_ms},
        "capacity_probe": {"status": capacity_status, "body": capacity_body, "duration_ms": capacity_ms},
        "cancel_results": cancel_results,
        "chat_results": chat_results,
        "cancel_storm_stop_ms": stop_ms,
        "recovery_status": recovery_status,
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
    sentinel = f"V293-NO-DISK-{uuid.uuid4().hex}"
    runtimes = []
    for runtime in RUNTIMES:
        status_code, status = request_json(runtime["base_url"], "/api/status")
        waves = [
            run_wave(runtime["base_url"], runtime["runtime_id"], wave + 1, contract, sentinel)
            for wave in range(contract["runtime"]["waves_per_runtime"])
        ]
        checks = {
            "status_available": status_code == 200,
            "source_version_valid": status.get("version") in {"PSM V0.292", "PSM V0.293"},
            "concurrency_limit_exposed": status.get("chat_concurrency_limit") == contract["admission"]["max_active_chat_requests"],
            "queue_disabled": status.get("chat_queue_enabled") is False,
            "all_waves_pass": all(wave["passed"] for wave in waves),
            "external_release_closed": status.get("ready_for_external_user_trial") is False,
        }
        runtimes.append({
            **runtime,
            "version": status.get("version"),
            "waves": waves,
            "max_capacity_response_ms": max(wave["capacity_probe"]["duration_ms"] for wave in waves),
            "max_cancel_storm_stop_ms": max(wave["cancel_storm_stop_ms"] for wave in waves),
            "checks": checks,
            "passed": all(checks.values()),
        })
    disk_hits = sentinel_hits(sentinel)
    checks = {
        "contract_frozen": contract.get("frozen_before_implementation") is True,
        "host_passed": runtimes[0]["passed"],
        "docker_passed": runtimes[1]["passed"],
        "four_waves_passed": sum(wave["passed"] for runtime in runtimes for wave in runtime["waves"]) == 4,
        "sixteen_active_requests_cancelled": sum(
            item.get("status") == 499
            for runtime in runtimes
            for wave in runtime["waves"]
            for item in wave["chat_results"]
        ) == 16,
        "capacity_probe_content_not_persisted": not disk_hits,
        "external_release_closed": contract["release_boundary"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_293_concurrency_backpressure_report_v1",
        "version": "PSM_V0.293-candidate",
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
        "schema_version": "psm_v0_293_concurrency_backpressure_gate_v1",
        "decision": "concurrency_backpressure_gate_passed" if report["passed"] else "concurrency_backpressure_gate_failed",
        "passed": report["passed"],
        "checks": checks,
        "host_capacity_max_ms": runtimes[0]["max_capacity_response_ms"],
        "docker_capacity_max_ms": runtimes[1]["max_capacity_response_ms"],
        "host_cancel_storm_max_ms": runtimes[0]["max_cancel_storm_stop_ms"],
        "docker_cancel_storm_max_ms": runtimes[1]["max_cancel_storm_stop_ms"],
        "external_release_authority": False,
    }
    write(REPORT, report)
    write(GATE, gate)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
