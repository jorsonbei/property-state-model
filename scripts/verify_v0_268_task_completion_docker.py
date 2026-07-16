#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_268_task_completion_docker_boundary.json"
GATE = PSM_ROOT / "runtime" / "v0_268_task_completion_gate.json"
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


def probe(base: str, prompt: str) -> tuple[int, dict]:
    return request(base, "/api/chat", {"messages": [{"role": "user", "content": prompt}], "scenario": "review"})


def main() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    host_code, host = request(HOST_URL, "/api/status")
    docker_code, docker = request(DOCKER_URL, "/api/status")
    prompt = "一句话总结：内部实验支持假设，但样本很小，尚无独立复现，因此只能作为初步证据。"
    host_summary_code, host_summary = probe(HOST_URL, prompt)
    docker_summary_code, docker_summary = probe(DOCKER_URL, prompt)
    host_answer = host_summary.get("chat", {}).get("assistant_message", "")
    docker_answer = docker_summary.get("chat", {}).get("assistant_message", "")
    docker_report = run(["docker", "compose", "exec", "-T", "psm-chat", "python", "-c", "import json; r=json.load(open('/app/outputs/psm_v0/runtime/v0_268_task_completion_report.json')); print(r['summary']['passed'])"])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    checks = {
        "task_completion_gate_passed": gate.get("passed") is True,
        "host_and_docker_status_available": host_code == docker_code == 200,
        "epistemic_summary_host": host_summary_code == 200 and "内部实验支持" in host_answer and "初步证据" in host_answer and "结论成立" not in host_answer,
        "epistemic_summary_docker": docker_summary_code == 200 and "内部实验支持" in docker_answer and "初步证据" in docker_answer and "结论成立" not in docker_answer,
        "task_report_in_docker": docker_report.returncode == 0 and docker_report.stdout.strip() == "21",
        "external_user_release_closed_host": host.get("ready_for_external_user_trial") is False,
        "external_user_release_closed_docker": docker.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_268_task_completion_docker_boundary_v1",
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
        raise SystemExit(f"V0.268 Docker boundary failed: {[key for key, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
