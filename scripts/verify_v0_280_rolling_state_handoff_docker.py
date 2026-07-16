#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
GATE = PSM_ROOT / "runtime" / "v0_280_rolling_state_handoff_gate.json"
REPORT = PSM_ROOT / "runtime" / "v0_280_rolling_state_handoff_report.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_280_rolling_state_handoff_docker_boundary.json"
HOST = "http://127.0.0.1:8765"
DOCKER = "http://127.0.0.1:8766"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(base: str, route: str) -> dict:
    with urllib.request.urlopen(base + route, timeout=10) as response:
        return json.loads(response.read().decode())


def get_text(base: str, route: str) -> str:
    with urllib.request.urlopen(base + route, timeout=10) as response:
        return response.read().decode()


def post_chat(base: str, session_id: str, messages: list[dict]) -> dict:
    request = urllib.request.Request(
        base + "/api/chat",
        data=json.dumps({"messages": messages, "scenario": "review", "session_id": session_id}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=70) as response:
        return json.loads(response.read().decode())


def rolling_window() -> list[dict]:
    messages = [
        {
            "id": message_id,
            "role": "assistant" if message_id % 2 == 0 else "user",
            "content": "已记录。" if message_id % 2 == 0 else f"窗口过程记录 {message_id}：无新增决定。",
        }
        for message_id in range(2, 121)
    ]
    messages.append({"id": 121, "role": "user", "content": "最早确定的项目代号是什么？只回答代号。"})
    return messages


def verify_base(base: str, session_id: str) -> tuple[dict, dict]:
    first = post_chat(
        base,
        session_id,
        [{"id": 1, "role": "user", "content": "项目代号定为白砾。你好，你是谁？"}],
    )
    second = post_chat(base, session_id, rolling_window())
    return first, second


def main() -> None:
    gate = read(GATE)
    report = read(REPORT)
    host_status = get_json(HOST, "/api/status")
    docker_status = get_json(DOCKER, "/api/status")
    host_first, host_second = verify_base(HOST, "host_session_0123456789abcdef")
    docker_first, docker_second = verify_base(DOCKER, "docker_session_0123456789abcdef")
    host_continuity = host_second["chat"]["state_continuity"]
    docker_continuity = docker_second["chat"]["state_continuity"]
    host_capsule = host_second["chat"]["generation"].get("state_capsule") or {}
    docker_capsule = docker_second["chat"]["generation"].get("state_capsule") or {}
    docker_report = run([
        "docker", "compose", "exec", "-T", "psm-chat", "python", "-c",
        "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_280_rolling_state_handoff_report.json')); print(r['summary']['passed'])",
    ])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    host_frontend = get_text(HOST, "/app.js")
    docker_frontend = get_text(DOCKER, "/app.js")
    checks = {
        "rolling_gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "all_four_cases_passed": report.get("summary", {}).get("passed") == 4,
        "host_and_docker_versions_are_v0_279": host_status.get("version") == docker_status.get("version") == "PSM V0.279",
        "first_requests_completed": bool(host_first.get("chat", {}).get("assistant_message")) and bool(docker_first.get("chat", {}).get("assistant_message")),
        "archived_fact_recovered_on_host": host_second["chat"]["assistant_message"] == "白砾",
        "archived_fact_recovered_in_docker": docker_second["chat"]["assistant_message"] == "白砾",
        "host_window_bounded_to_120": host_continuity.get("history_messages") == 120,
        "docker_window_bounded_to_120": docker_continuity.get("history_messages") == 120,
        "host_rolling_state_applied": host_continuity.get("rolling_state_applied") is True,
        "docker_rolling_state_applied": docker_continuity.get("rolling_state_applied") is True,
        "ephemeral_memory_only": (
            host_continuity.get("rolling_state", {}).get("ephemeral_memory_only") is True
            and docker_continuity.get("rolling_state", {}).get("ephemeral_memory_only") is True
            and host_continuity.get("rolling_state", {}).get("disk_persistence") is False
            and docker_continuity.get("rolling_state", {}).get("disk_persistence") is False
        ),
        "public_capsules_hide_raw_user_state": "user_statements" not in host_capsule and "user_statements" not in docker_capsule,
        "frontend_sends_session_and_sequence": all(
            token in frontend
            for frontend in (host_frontend, docker_frontend)
            for token in ("session_id: state.sessionId", "({ id, role, content })", "state.sessionId = createSessionId()")
        ),
        "rolling_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == "4",
        "external_user_release_closed": (
            host_status.get("ready_for_external_user_trial") is False
            and docker_status.get("ready_for_external_user_trial") is False
        ),
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    result = {
        "schema_version": "psm_v0_280_rolling_state_handoff_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "human_feedback_collected": False,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "host": {
            "version": host_status.get("version"),
            "history_messages": host_continuity.get("history_messages"),
            "effective_context_messages": host_continuity.get("effective_context_messages"),
        },
        "docker": {
            "version": docker_status.get("version"),
            "history_messages": docker_continuity.get("history_messages"),
            "effective_context_messages": docker_continuity.get("effective_context_messages"),
        },
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit("V0.280 host/Docker rolling-state boundary failed.")


if __name__ == "__main__":
    main()
