#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
GATE = PSM_ROOT / "runtime" / "v0_274_open_context_generalization_gate.json"
REPORT = PSM_ROOT / "runtime" / "v0_274_open_context_generalization_report.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_274_open_context_docker_boundary.json"
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
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def main() -> None:
    gate = read(GATE)
    report = read(REPORT)
    messages = [
        {"role": "user", "content": "出门前要买燕麦、牛奶。"},
        {"role": "assistant", "content": "购物项是燕麦和牛奶。"},
        {"role": "user", "content": "牛奶刚买好了。"},
        {"role": "assistant", "content": "牛奶已完成。"},
        {"role": "user", "content": "回家顺便取快递。"},
        {"role": "assistant", "content": "收到。"},
        {"role": "user", "content": "晚饭不做汤。"},
        {"role": "assistant", "content": "明白。"},
        {"role": "user", "content": "购物袋放门边。"},
        {"role": "assistant", "content": "好的。"},
        {"role": "user", "content": "购物方面还漏了什么？"},
    ]
    host_status = get_json(HOST, "/api/status")
    docker_status = get_json(DOCKER, "/api/status")
    host_answer = post_chat(HOST, messages)
    docker_answer = post_chat(DOCKER, messages)
    docker_report = run([
        "docker", "compose", "exec", "-T", "psm-chat", "python", "-c",
        "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_274_open_context_generalization_report.json')); print(r['summary']['passed'])",
    ])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    checks = {
        "open_context_gate_passed": gate.get("passed") is True,
        "all_ten_cases_passed": report.get("summary", {}).get("passed") == 10,
        "host_and_docker_status_available": bool(host_status.get("version")) and bool(docker_status.get("version")),
        "host_and_docker_versions_match": host_status.get("version") == docker_status.get("version"),
        "unresolved_work_host": host_answer.get("chat", {}).get("assistant_message") == "燕麦",
        "unresolved_work_docker": docker_answer.get("chat", {}).get("assistant_message") == "燕麦",
        "host_state_capsule_present": host_answer.get("chat", {}).get("generation", {}).get("state_capsule", {}).get("user_authoritative") is True,
        "docker_state_capsule_present": docker_answer.get("chat", {}).get("generation", {}).get("state_capsule", {}).get("user_authoritative") is True,
        "open_context_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == "10",
        "external_user_release_closed_host": host_status.get("ready_for_external_user_trial") is False,
        "external_user_release_closed_docker": docker_status.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    result = {
        "schema_version": "psm_v0_274_open_context_docker_boundary_v1",
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
        raise SystemExit("V0.274 host/Docker open-context boundary failed.")


if __name__ == "__main__":
    main()
