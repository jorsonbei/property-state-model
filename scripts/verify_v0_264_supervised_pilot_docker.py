from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from verify_v0_263_completed_enrollment_docker import (
    docker_private_state_absent,
    run,
    tracked_secret_hits,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_264_supervised_pilot_docker_boundary.json"
PRIVATE_STATE = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
HOST_URL = "http://127.0.0.1:8765"
DOCKER_URL = "http://127.0.0.1:8766"


def request_json(base_url: str, path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def main() -> None:
    state = json.loads(PRIVATE_STATE.read_text(encoding="utf-8"))
    host_status_code, host_status = request_json(HOST_URL, "/api/status")
    host_enrollment_code, host_enrollment = request_json(HOST_URL, "/api/trial-enrollment")
    docker_status_code, docker_status = request_json(DOCKER_URL, "/api/status")
    docker_enrollment_code, _ = request_json(DOCKER_URL, "/api/trial-enrollment")
    docker_trial_code, docker_trial = request_json(
        DOCKER_URL,
        "/api/trial-chat",
        method="POST",
        payload={
            "participant_id": "P02",
            "invitation_code": "container-has-no-private-invite",
            "messages": [{"role": "user", "content": "容器邊界檢查"}],
        },
    )
    port_result = run(["docker", "compose", "port", "psm-chat", "8765"])
    if port_result.returncode != 0:
        raise SystemExit(port_result.stderr.strip() or "Docker port inspection failed.")
    progress = host_enrollment.get("pilot_progress") or {}
    credited = [item.get("credited_turns") for item in progress.get("participants") or []]
    secret_hits = tracked_secret_hits(state)
    checks = {
        "host_status_available": host_status_code == 200,
        "host_pilot_gate_passed": (
            host_enrollment_code == 200
            and host_enrollment.get("trial_active") is True
            and host_enrollment.get("stopped") is False
            and progress.get("completed_participants") == 3
            and progress.get("gate_passed") is True
            and credited == [3, 3, 3]
        ),
        "host_public_service_closed": host_status.get("ready_for_external_user_trial") is False,
        "private_values_absent_from_tracked_files": secret_hits == 0,
        "docker_status_available": docker_status_code == 200,
        "docker_private_state_absent": docker_private_state_absent(),
        "docker_enrollment_api_unavailable": docker_enrollment_code == 404,
        "docker_trial_chat_rejected": docker_trial_code == 409 and docker_trial.get("trial_active") is False,
        "docker_public_service_closed": docker_status.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port_result.stdout.strip() in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_264_supervised_pilot_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "tracked_private_secret_hits": secret_hits,
        "host": {
            "version": host_status.get("version"),
            "completed_participants": progress.get("completed_participants"),
            "credited_turns": credited,
            "pilot_gate_passed": progress.get("gate_passed"),
        },
        "docker": {
            "version": docker_status.get("version"),
            "private_state_present": False,
            "enrollment_api_status": docker_enrollment_code,
            "trial_chat_status": docker_trial_code,
            "public_service_allowed": False,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"V0.264 Docker boundary failed: {failed}")


if __name__ == "__main__":
    main()
