#!/usr/bin/env python3
from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_269_task_stability_docker_boundary.json"
GATE = PSM_ROOT / "runtime" / "v0_269_task_stability_gate.json"
HOST_URL = "http://127.0.0.1:8765"
DOCKER_URL = "http://127.0.0.1:8766"


def request(base: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"} if data else {}, method="POST" if data else "GET")
    last_error: Exception | None = None
    for attempt in range(10):
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, {}
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.RemoteDisconnected) as exc:
            last_error = exc
            if attempt < 9:
                time.sleep(0.5)
    assert last_error is not None
    raise last_error


def probe(base: str, prompt: str) -> tuple[int, dict]:
    return request(base, "/api/chat", {"messages": [{"role": "user", "content": prompt}], "scenario": "review"})


def main() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    host_code, host = request(HOST_URL, "/api/status")
    docker_code, docker = request(DOCKER_URL, "/api/status")
    prompt = "这不是医疗诊断，只做词汇翻译：把“胸痛”翻译成英文。"
    host_chat_code, host_chat = probe(HOST_URL, prompt)
    docker_chat_code, docker_chat = probe(DOCKER_URL, prompt)
    host_answer = host_chat.get("chat", {}).get("assistant_message", "")
    docker_answer = docker_chat.get("chat", {}).get("assistant_message", "")
    docker_report = run(["docker", "compose", "exec", "-T", "psm-chat", "python", "-c", "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_269_task_stability_report.json')); print(r['summary']['passed_runs'], r['summary']['p95_ms'])"])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    metrics = gate.get("metrics") or {}
    checks = {
        "task_stability_gate_passed": gate.get("passed") is True,
        "host_and_docker_status_available": host_code == docker_code == 200,
        "deterministic_kernel_host": host_chat_code == 200 and "chest pain" in host_answer,
        "deterministic_kernel_docker": docker_chat_code == 200 and docker_answer == host_answer,
        "stability_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == f"{metrics.get('passed_runs')} {metrics.get('p95_ms')}",
        "external_user_release_closed_host": host.get("ready_for_external_user_trial") is False,
        "external_user_release_closed_docker": docker.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_269_task_stability_docker_boundary_v1",
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
        raise SystemExit(f"V0.269 Docker boundary failed: {[key for key, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
