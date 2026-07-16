#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_270_multiturn_docker_boundary.json"
GATE = PSM_ROOT / "runtime" / "v0_270_multiturn_constraint_gate.json"
HOST_URL = "http://127.0.0.1:8765"
DOCKER_URL = "http://127.0.0.1:8766"


def request(base: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"} if data else {}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def probe(base: str, messages: list[dict]) -> tuple[int, dict]:
    return request(base, "/api/chat", {"messages": messages, "scenario": "review"})


def main() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    host_code, host = request(HOST_URL, "/api/status")
    docker_code, docker = request(DOCKER_URL, "/api/status")
    messages = [
        {"role": "user", "content": "给我三步复习计划，每步写时间。"},
        {"role": "assistant", "content": "1. 20分钟复习公式。\n2. 40分钟做题。\n3. 30分钟整理错题。"},
        {"role": "user", "content": "把第二步改成50分钟，仍然只保留三步。"},
    ]
    host_chat_code, host_chat = probe(HOST_URL, messages)
    docker_chat_code, docker_chat = probe(DOCKER_URL, messages)
    host_answer = host_chat.get("chat", {}).get("assistant_message", "")
    docker_answer = docker_chat.get("chat", {}).get("assistant_message", "")
    version_messages = [
        {"role": "user", "content": "项目当前版本是什么？"},
        {"role": "assistant", "content": "当前项目是 PSM V0.250。"},
        {"role": "user", "content": "不要沿用上一句，按本地结构化记录更正当前版本。"},
    ]
    host_version_code, host_version = probe(HOST_URL, version_messages)
    docker_version_code, docker_version = probe(DOCKER_URL, version_messages)
    docker_report = run(["docker", "compose", "exec", "-T", "psm-chat", "python", "-c", "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_270_multiturn_constraint_report.json')); print(r['summary']['passed'])"])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    checks = {
        "multiturn_gate_passed": gate.get("passed") is True,
        "host_and_docker_status_available": host_code == docker_code == 200,
        "three_step_revision_host": host_chat_code == 200 and "50分钟" in host_answer and "40分钟" not in host_answer and len([line for line in host_answer.splitlines() if line.strip()]) == 3,
        "three_step_revision_docker": docker_chat_code == 200 and docker_answer == host_answer,
        "direct_version_correction_host": host_version_code == 200 and host_version.get("chat", {}).get("assistant_message") == "当前项目版本是 PSM V0.270。",
        "direct_version_correction_docker": docker_version_code == 200 and docker_version.get("chat", {}).get("assistant_message") == host_version.get("chat", {}).get("assistant_message"),
        "multiturn_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == "12",
        "external_user_release_closed_host": host.get("ready_for_external_user_trial") is False,
        "external_user_release_closed_docker": docker.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_270_multiturn_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "human_feedback_collected": False,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "host": {"version": host.get("version"), "release_open": host.get("ready_for_external_user_trial")},
        "docker": {"version": docker.get("version"), "release_open": docker.get("ready_for_external_user_trial")},
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(f"V0.270 Docker boundary failed: {[key for key, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
