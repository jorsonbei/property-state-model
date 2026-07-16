#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
SERVER = PSM_ROOT / "product_alpha_app" / "server.py"
LOCAL_GATE = PSM_ROOT / "runtime" / "v0_283_restart_recovery_gate.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_283_controlled_restart_boundary.json"
HOST_BASE = "http://127.0.0.1:8873"
DOCKER_BASE = "http://127.0.0.1:8766"


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_status(base_url: str, *, previous_instance: str | None = None) -> dict:
    deadline = time.monotonic() + 40
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status = request_json(f"{base_url}/api/status")
            instance = str(status.get("continuity_instance_id") or "")
            if instance and (previous_instance is None or instance != previous_instance):
                return status
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"status did not become ready for {base_url}: {last_error}")


def seed(base_url: str, session_id: str, instance_id: str) -> None:
    result = request_json(
        f"{base_url}/api/chat",
        {
            "scenario": "review",
            "session_id": session_id,
            "continuity_event": "active",
            "server_instance_id": instance_id,
            "messages": [
                {"id": 1, "role": "user", "content": "项目代号定为白砾。你好，你是谁？"}
            ],
        },
    )
    if result["chat"]["state_continuity"]["continuity_status"]["state"] != "active":
        raise RuntimeError("seed request was not active")


def query_after_restart(base_url: str, session_id: str, old_instance: str) -> dict:
    result = request_json(
        f"{base_url}/api/chat",
        {
            "scenario": "review",
            "session_id": session_id,
            "continuity_event": "active",
            "server_instance_id": old_instance,
            "messages": [
                {"id": 2, "role": "user", "content": "之前的项目代号是什么？"}
            ],
        },
    )
    status = result["chat"]["state_continuity"]["continuity_status"]
    answer = result["chat"]["assistant_message"]
    return {
        "state": status["state"],
        "recovery_required": status["recovery_required"],
        "recovery_action": status["recovery_action"],
        "archived_fact_fabricated": "白砾" in answer,
        "boundary_visible": "不能确认" in answer,
        "raw_conversation_persisted": status["raw_conversation_persisted"],
    }


def instance_digest(instance_id: str) -> str:
    return hashlib.sha256(instance_id.encode("utf-8")).hexdigest()[:16]


def start_host() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(SERVER), "--host", "127.0.0.1", "--port", "8873"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_host(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def exercise_host() -> dict:
    first = start_host()
    try:
        before = wait_status(HOST_BASE)
        old_instance = before["continuity_instance_id"]
        seed(HOST_BASE, "v283_host_restart_session", old_instance)
    finally:
        stop_host(first)
    second = start_host()
    try:
        after = wait_status(HOST_BASE, previous_instance=old_instance)
        result = query_after_restart(HOST_BASE, "v283_host_restart_session", old_instance)
    finally:
        stop_host(second)
    return {
        "old_instance_digest": instance_digest(old_instance),
        "new_instance_digest": instance_digest(after["continuity_instance_id"]),
        "instance_rotated": old_instance != after["continuity_instance_id"],
        **result,
    }


def exercise_docker() -> dict:
    before = wait_status(DOCKER_BASE)
    old_instance = before["continuity_instance_id"]
    seed(DOCKER_BASE, "v283_docker_restart_session", old_instance)
    subprocess.run(
        ["docker", "compose", "restart", "psm-chat"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    after = wait_status(DOCKER_BASE, previous_instance=old_instance)
    result = query_after_restart(DOCKER_BASE, "v283_docker_restart_session", old_instance)
    return {
        "old_instance_digest": instance_digest(old_instance),
        "new_instance_digest": instance_digest(after["continuity_instance_id"]),
        "instance_rotated": old_instance != after["continuity_instance_id"],
        **result,
    }


def main() -> None:
    local_gate = json.loads(LOCAL_GATE.read_text(encoding="utf-8"))
    if local_gate.get("passed") is not True:
        raise SystemExit("V0.283 local gate is not passed")
    host = exercise_host()
    docker = exercise_docker()
    checks = {
        "host_instance_rotated": host["instance_rotated"],
        "docker_instance_rotated": docker["instance_rotated"],
        "host_restart_detected": host["state"] == "restarted",
        "docker_restart_detected": docker["state"] == "restarted",
        "host_recovery_boundary_visible": host["boundary_visible"] and host["recovery_required"],
        "docker_recovery_boundary_visible": docker["boundary_visible"] and docker["recovery_required"],
        "zero_archived_fact_fabrication": not host["archived_fact_fabricated"] and not docker["archived_fact_fabricated"],
        "zero_raw_conversation_persistence": not host["raw_conversation_persisted"] and not docker["raw_conversation_persisted"],
    }
    report = {
        "schema_version": "psm_v0_283_controlled_restart_boundary_v1",
        "version": "PSM_V0.283-candidate",
        "passed": all(checks.values()),
        "synthetic_only": True,
        "host": host,
        "docker": docker,
        "checks": checks,
        "external_release_authority": False,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"boundary: {OUTPUT.relative_to(ROOT)}")
    print(f"passed: {report['passed']}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
