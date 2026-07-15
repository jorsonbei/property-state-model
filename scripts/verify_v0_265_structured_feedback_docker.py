from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import docker_private_state_absent, run


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_265_structured_feedback_docker_boundary.json"
HOST_URL = "http://127.0.0.1:8765"
DOCKER_URL = "http://127.0.0.1:8766"


def request_json(base_url: str, path: str) -> tuple[int, dict]:
    request = urllib.request.Request(base_url + path, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def main() -> None:
    host_status_code, host_status = request_json(HOST_URL, "/api/status")
    host_feedback_code, host_feedback = request_json(HOST_URL, "/api/trial-feedback")
    docker_status_code, docker_status = request_json(DOCKER_URL, "/api/status")
    docker_feedback_code, docker_feedback = request_json(DOCKER_URL, "/api/trial-feedback")
    port_result = run(["docker", "compose", "port", "psm-chat", "8765"])
    private_probe = run([
        "docker",
        "compose",
        "exec",
        "-T",
        "psm-chat",
        "python",
        "-c",
        (
            "from pathlib import Path; "
            "paths=[Path('/app/outputs/psm_v0/private_runtime/v0_263/enrollment_state.json'),"
            "Path('/app/outputs/psm_v0/private_runtime/v0_265/feedback_state.json')]; "
            "print(','.join(str(int(p.exists())) for p in paths))"
        ),
    ])
    progress = host_feedback.get("participants") or []
    checks = {
        "host_status_available": host_status_code == 200,
        "host_feedback_api_available": host_feedback_code == 200,
        "host_feedback_progress_empty": (
            host_feedback.get("completed_participants") == 0
            and host_feedback.get("total_feedback_events") == 0
            and [item.get("credited") for item in progress] == [0, 0, 0]
        ),
        "host_feedback_public_service_closed": (
            host_feedback.get("release_boundary", {}).get("public_service_allowed") is False
        ),
        "host_external_user_trial_closed": host_status.get("ready_for_external_user_trial") is False,
        "docker_status_available": docker_status_code == 200,
        "docker_enrollment_private_state_absent": docker_private_state_absent(),
        "docker_all_private_trial_state_absent": private_probe.returncode == 0
        and private_probe.stdout.strip() == "0,0",
        "docker_feedback_api_unavailable": docker_feedback_code == 404
        and bool(docker_feedback.get("error")),
        "docker_external_user_trial_closed": docker_status.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port_result.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_265_structured_feedback_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "host": {
            "version": host_status.get("version"),
            "feedback_events": host_feedback.get("total_feedback_events"),
            "credited_feedback": [item.get("credited") for item in progress],
            "public_service_allowed": False,
        },
        "docker": {
            "version": docker_status.get("version"),
            "private_enrollment_state_present": False,
            "private_feedback_state_present": False,
            "feedback_api_status": docker_feedback_code,
            "public_service_allowed": False,
            "bind": port_result.stdout.strip(),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"V0.265 Docker boundary failed: {failed}")


if __name__ == "__main__":
    main()
