#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
GATE = PSM_ROOT / "runtime" / "v0_272_long_context_state_gate.json"
REPORT = PSM_ROOT / "runtime" / "v0_272_long_context_state_report.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_272_long_context_docker_boundary.json"
HOST = "http://127.0.0.1:8765"
DOCKER = "http://127.0.0.1:8766"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(base: str, route: str) -> dict:
    with urllib.request.urlopen(base + route, timeout=10) as response:
        return json.loads(response.read().decode())


def post_chat(base: str, messages: list[dict[str, str]]) -> dict:
    request = urllib.request.Request(
        base + "/api/chat",
        data=json.dumps({"messages": messages, "scenario": "review"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def main() -> None:
    gate = read(GATE)
    report = read(REPORT)
    fact_messages = [
        {"role": "user", "content": "这个项目的代号定为松塔。"},
        {"role": "assistant", "content": "已记录项目代号为松塔。"},
        {"role": "user", "content": "界面先采用深色模式。"},
        {"role": "assistant", "content": "可以，先采用深色模式。"},
        {"role": "user", "content": "日志保留七天。"},
        {"role": "assistant", "content": "已记录日志保留七天。"},
        {"role": "user", "content": "回到最开始的项目设定：代号是什么？只给代号。"},
    ]
    host_status = get_json(HOST, "/api/status")
    docker_status = get_json(DOCKER, "/api/status")
    host_fact = post_chat(HOST, fact_messages)
    docker_fact = post_chat(DOCKER, fact_messages)
    docker_report = run([
        "docker",
        "compose",
        "exec",
        "-T",
        "psm-chat",
        "python",
        "-c",
        "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_272_long_context_state_report.json')); print(r['summary']['passed'])",
    ])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    checks = {
        "long_context_gate_passed": gate.get("passed") is True,
        "all_ten_cases_passed": report.get("summary", {}).get("passed") == 10,
        "host_and_docker_status_available": bool(host_status.get("version")) and bool(docker_status.get("version")),
        "host_and_docker_versions_match": host_status.get("version") == docker_status.get("version"),
        "long_user_fact_host": host_fact.get("chat", {}).get("assistant_message") == "松塔",
        "long_user_fact_docker": docker_fact.get("chat", {}).get("assistant_message") == "松塔",
        "long_context_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == "10",
        "external_user_release_closed_host": host_status.get("ready_for_external_user_trial") is False,
        "external_user_release_closed_docker": docker_status.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    result = {
        "schema_version": "psm_v0_272_long_context_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "human_feedback_collected": False,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "host": {"version": host_status.get("version"), "release_open": host_status.get("ready_for_external_user_trial")},
        "docker": {"version": docker_status.get("version"), "release_open": docker_status.get("ready_for_external_user_trial")},
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit("V0.272 host/Docker long-context boundary failed.")


if __name__ == "__main__":
    main()
