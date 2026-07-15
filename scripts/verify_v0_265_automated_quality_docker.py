#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_265_automated_quality_docker_boundary.json"
GATE = PSM_ROOT / "runtime" / "v0_265_automated_quality_gate.json"
HOST_URL = "http://127.0.0.1:8765"
DOCKER_URL = "http://127.0.0.1:8766"


def request(base: str, path: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(base + path, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {}


def main() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    host_code, host = request(HOST_URL, "/api/status")
    docker_code, docker = request(DOCKER_URL, "/api/status")
    host_feedback_code, _ = request(HOST_URL, "/api/trial-feedback")
    docker_feedback_code, _ = request(DOCKER_URL, "/api/trial-feedback")
    inspect = run(["docker", "compose", "exec", "-T", "psm-chat", "python", "-c", "from pathlib import Path; roots=[Path('/app/outputs/psm_v0/psm_v0/participant_feedback.py'),Path('/app/outputs/psm_v0/private_runtime/v0_265')]; print('absent' if not any(p.exists() for p in roots) else 'present')"])
    port = run(["docker", "compose", "port", "psm-chat", "8765"])
    checks = {
        "automated_gate_passed": gate.get("passed") is True,
        "host_status_available": host_code == 200,
        "docker_status_available": docker_code == 200,
        "human_feedback_endpoint_absent_host": host_feedback_code == 404,
        "human_feedback_endpoint_absent_docker": docker_feedback_code == 404,
        "human_feedback_module_and_state_absent_docker": inspect.returncode == 0 and inspect.stdout.strip() == "absent",
        "external_user_release_closed_host": host.get("ready_for_external_user_trial") is False,
        "external_user_release_closed_docker": docker.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port.returncode == 0 and port.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_265_automated_quality_docker_boundary_v1",
        "passed": all(checks.values()), "checks": checks,
        "human_feedback_collected": False, "human_validation_claimed": False,
        "host": {"version": host.get("version"), "feedback_endpoint_status": host_feedback_code},
        "docker": {"version": docker.get("version"), "feedback_endpoint_status": docker_feedback_code, "public_service_allowed": False},
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(f"V0.265 Docker boundary failed: {[key for key, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
