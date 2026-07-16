#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_278_incremental_long_horizon_stress_contract.json"
GATE = PSM_ROOT / "runtime" / "v0_278_incremental_long_horizon_stress_gate.json"
REPORT = PSM_ROOT / "runtime" / "v0_278_incremental_long_horizon_stress_report.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_278_incremental_long_horizon_stress_docker_boundary.json"
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
    contract = read(CONTRACT)
    gate = read(GATE)
    report = read(REPORT)
    messages = contract["cases"][1]["messages"]
    host_status = get_json(HOST, "/api/status")
    docker_status = get_json(DOCKER, "/api/status")
    host_answer = post_chat(HOST, messages)
    docker_answer = post_chat(DOCKER, messages)
    host_capsule = host_answer.get("chat", {}).get("generation", {}).get("state_capsule", {})
    docker_capsule = docker_answer.get("chat", {}).get("generation", {}).get("state_capsule", {})
    docker_report = run([
        "docker", "compose", "exec", "-T", "psm-chat", "python", "-c",
        "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_278_incremental_long_horizon_stress_report.json')); print(r['summary']['passed'])",
    ])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    host_frontend = get_text(HOST, "/app.js")
    docker_frontend = get_text(DOCKER, "/app.js")
    checks = {
        "stress_gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "all_ten_cases_passed": report.get("summary", {}).get("passed") == 10,
        "host_and_docker_versions_are_v0_277": host_status.get("version") == docker_status.get("version") == "PSM V0.277",
        "remote_fact_host": host_answer.get("chat", {}).get("assistant_message") == "银杏厅",
        "remote_fact_docker": docker_answer.get("chat", {}).get("assistant_message") == "银杏厅",
        "host_retains_119_messages": host_answer.get("chat", {}).get("state_continuity", {}).get("history_messages") == 119,
        "docker_retains_119_messages": docker_answer.get("chat", {}).get("state_continuity", {}).get("history_messages") == 119,
        "host_compression_applied": host_capsule.get("compression_applied") is True and host_capsule.get("source_user_statements", 0) > 20,
        "docker_compression_applied": docker_capsule.get("compression_applied") is True and docker_capsule.get("source_user_statements", 0) > 20,
        "public_capsules_hide_raw_user_state": "user_statements" not in host_capsule and "user_statements" not in docker_capsule,
        "frontend_retains_120_messages": (
            "state.messages.length > 120" in host_frontend
            and "state.messages.slice(-120)" in host_frontend
            and "state.messages.length > 120" in docker_frontend
            and "state.messages.slice(-120)" in docker_frontend
        ),
        "stress_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == "10",
        "external_user_release_closed": (
            host_status.get("ready_for_external_user_trial") is False
            and docker_status.get("ready_for_external_user_trial") is False
        ),
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    result = {
        "schema_version": "psm_v0_278_incremental_long_horizon_stress_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "human_feedback_collected": False,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "host": {
            "version": host_status.get("version"),
            "history_messages": host_answer.get("chat", {}).get("state_continuity", {}).get("history_messages"),
        },
        "docker": {
            "version": docker_status.get("version"),
            "history_messages": docker_answer.get("chat", {}).get("state_continuity", {}).get("history_messages"),
        },
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit("V0.278 host/Docker stress boundary failed.")


if __name__ == "__main__":
    main()
