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
CONTRACT = PSM_ROOT / "benchmarks" / "v0_294_content_free_telemetry_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_294_content_free_telemetry_report.json"
GATE = PSM_ROOT / "runtime" / "v0_294_content_free_telemetry_gate.json"
RUNTIMES = (
    {"runtime_id": "host", "base_url": "http://127.0.0.1:8765"},
    {"runtime_id": "docker", "base_url": "http://127.0.0.1:8766"},
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request_json(base_url: str, path: str, payload: dict | None = None, timeout: int = 90) -> tuple[int, dict, dict]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8")), dict(exc.headers)


def chat_payload(runtime_id: str, request_id: str | None, prompt: str) -> dict:
    value = {
        "scenario": "review",
        "session_id": f"v294_{runtime_id}_{uuid.uuid4().hex}",
        "continuity_event": "active",
        "messages": [{"id": 1, "role": "user", "content": prompt}],
    }
    if request_id is not None:
        value["request_id"] = request_id
    return value


def latency_total(health: dict, series: str) -> int:
    return sum(bucket["count"] for bucket in health["latency_buckets_ms"][series])


def exercise(base_url: str, runtime_id: str, sentinel: str, contract: dict) -> dict:
    health_status, before, health_headers = request_json(base_url, "/api/health")
    status_code, status, _ = request_json(base_url, "/api/status")
    request_id = f"chat_v294_{runtime_id}_{uuid.uuid4().hex}"
    result: dict = {}

    def run_chat() -> None:
        chat_status, body, _ = request_json(
            base_url,
            "/api/chat",
            chat_payload(
                runtime_id,
                request_id,
                f"请详细规划一个新的本地资料项目，包含名称、架构、阶段和风险。{sentinel}",
            ),
        )
        result.update(status=chat_status, body=body)

    thread = threading.Thread(target=run_chat)
    thread.start()
    time.sleep(1)
    duplicate_status, duplicate_body, _ = request_json(
        base_url,
        "/api/chat",
        chat_payload(runtime_id, request_id, "这个重复请求不应执行。"),
    )
    cancel_status, cancel_body, _ = request_json(
        base_url,
        "/api/chat-cancel",
        {"request_id": request_id},
    )
    thread.join(5)
    repeat_status, repeat_body, _ = request_json(
        base_url,
        "/api/chat-cancel",
        {"request_id": request_id},
    )
    invalid_status, invalid_body, _ = request_json(
        base_url,
        "/api/chat-cancel",
        {"request_id": "invalid"},
    )
    complete_status, complete_body, _ = request_json(
        base_url,
        "/api/chat",
        chat_payload(runtime_id, None, "你好，你是谁？"),
    )
    _, after, _ = request_json(base_url, "/api/health")

    expected_delta = {
        "accepted": 2,
        "capacity_rejected": 0,
        "duplicate_rejected": 1,
        "invalid_rejected": 1,
        "cancel_requests": 2,
        "cancel_active": 1,
        "cancel_inactive": 1,
        "cancelled": 1,
        "completed": 1,
        "failed": 0,
    }
    observed_delta = {
        name: after["counters"][name] - before["counters"][name]
        for name in contract["counters"]
    }
    serialized = json.dumps(after, ensure_ascii=False, sort_keys=True)
    checks = {
        "health_200_no_store": health_status == 200 and health_headers.get("Cache-Control") == "no-store",
        "source_version_valid": status_code == 200 and status.get("version") in {"PSM V0.293", "PSM V0.294"},
        "duplicate_409": duplicate_status == 409 and duplicate_body.get("error") == "duplicate_request_id",
        "active_cancel_accepted": cancel_status == 200 and cancel_body.get("active") is True,
        "cancelled_chat_499": not thread.is_alive() and result.get("status") == 499 and result.get("body", {}).get("error") == "chat_cancelled",
        "repeat_cancel_inactive": repeat_status == 200 and repeat_body.get("active") is False,
        "invalid_rejected_400": invalid_status == 400 and invalid_body.get("error") == "invalid_request_id",
        "completed_identity_200": complete_status == 200 and bool(complete_body.get("chat", {}).get("assistant_message")),
        "counter_delta_exact": observed_delta == expected_delta,
        "active_returns_to_zero": after.get("active_requests") == 0 and after.get("status") == "healthy",
        "completed_bucket_delta_exact": latency_total(after, "completed") - latency_total(before, "completed") == 1,
        "cancelled_bucket_delta_exact": latency_total(after, "cancelled") - latency_total(before, "cancelled") == 1,
        "failed_bucket_delta_zero": latency_total(after, "failed") - latency_total(before, "failed") == 0,
        "forbidden_fields_absent": all(field not in serialized for field in contract["privacy"]["forbidden_fields"]),
        "content_and_identifiers_not_retained": after.get("content_retained") is False and after.get("identifiers_retained") is False,
        "disk_persistence_false": after.get("disk_persistence") is False,
        "external_release_closed": status.get("ready_for_external_user_trial") is False,
    }
    return {
        "runtime_id": runtime_id,
        "base_url": base_url,
        "version": status.get("version"),
        "before": before,
        "after": after,
        "expected_counter_delta": expected_delta,
        "observed_counter_delta": observed_delta,
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
    sentinel = f"V294-NO-DISK-{uuid.uuid4().hex}"
    runtimes = [
        exercise(runtime["base_url"], runtime["runtime_id"], sentinel, contract)
        for runtime in RUNTIMES
    ]
    disk_hits = sentinel_hits(sentinel)
    checks = {
        "contract_frozen": contract.get("frozen_before_implementation") is True,
        "host_passed": runtimes[0]["passed"],
        "docker_passed": runtimes[1]["passed"],
        "both_counter_deltas_exact": all(runtime["observed_counter_delta"] == runtime["expected_counter_delta"] for runtime in runtimes),
        "disk_sentinel_hits_zero": not disk_hits,
        "external_release_closed": contract["release_boundary"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_294_content_free_telemetry_report_v1",
        "version": "PSM_V0.294-candidate",
        "contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "runtimes": runtimes,
        "disk_sentinel_hits": disk_hits,
        "checks": checks,
        "passed": all(checks.values()),
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    gate = {
        "schema_version": "psm_v0_294_content_free_telemetry_gate_v1",
        "decision": "content_free_telemetry_gate_passed" if report["passed"] else "content_free_telemetry_gate_failed",
        "passed": report["passed"],
        "checks": checks,
        "host_counter_delta": runtimes[0]["observed_counter_delta"],
        "docker_counter_delta": runtimes[1]["observed_counter_delta"],
        "external_release_authority": False,
    }
    write(REPORT, report)
    write(GATE, gate)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
