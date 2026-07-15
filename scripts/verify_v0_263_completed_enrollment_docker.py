from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_263_completed_enrollment_docker_boundary.json"
PRIVATE_STATE = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_263_participant_enrollment_checkpoint.json"
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


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)


def docker_private_state_absent() -> bool:
    completed = run([
        "docker", "compose", "exec", "-T", "psm-chat", "python", "-c",
        "from pathlib import Path;print('absent' if not Path('/app/outputs/psm_v0/private_runtime').exists() else 'present')",
    ])
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or "Docker private-state inspection failed.")
    return completed.stdout.strip() == "absent"


def tracked_secret_hits(private_state: dict) -> int:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, timeout=30, check=False
    )
    if completed.returncode != 0:
        raise SystemExit("Unable to enumerate Git-tracked files.")
    secrets = [str(private_state.get("audit_secret_hex") or "").encode()]
    for participant in private_state.get("participants") or []:
        secrets.extend(
            str(participant.get(key) or "").encode()
            for key in ("invitation_code", "invitation_sha256", "invitee_binding_hmac_sha256")
        )
    files = [ROOT / raw.decode() for raw in completed.stdout.split(b"\0") if raw]
    return sum(secret in path.read_bytes() for path in files for secret in secrets if secret)


def main() -> None:
    private_state = json.loads(PRIVATE_STATE.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    host_status_code, host_status = request_json(HOST_URL, "/api/status")
    host_enrollment_code, host_enrollment = request_json(HOST_URL, "/api/trial-enrollment")
    docker_status_code, docker_status = request_json(DOCKER_URL, "/api/status")
    docker_enrollment_code, _ = request_json(DOCKER_URL, "/api/trial-enrollment")
    docker_cards_code, _ = request_json(DOCKER_URL, "/api/trial-enrollment/operator-cards")
    docker_trial_code, docker_trial = request_json(
        DOCKER_URL,
        "/api/trial-chat",
        method="POST",
        payload={
            "participant_id": "P01",
            "invitation_code": "container-has-no-private-invite",
            "messages": [{"role": "user", "content": "容器邊界檢查"}],
        },
    )
    port_result = run(["docker", "compose", "port", "psm-chat", "8765"])
    if port_result.returncode != 0:
        raise SystemExit(port_result.stderr.strip() or "Docker port inspection failed.")
    port = port_result.stdout.strip()
    secret_hits = tracked_secret_hits(private_state)
    public_checkpoint_text = json.dumps(checkpoint, ensure_ascii=False)
    expected_counts = {
        "invited": 3,
        "adult_verified": 3,
        "notice_displayed": 3,
        "notice_acknowledged": 3,
        "consented": 3,
        "session_enabled": 3,
        "revoked": 0,
    }
    checks = {
        "host_status_available": host_status_code == 200,
        "host_completed_three_person_gate": (
            host_enrollment_code == 200
            and host_enrollment.get("counts") == expected_counts
            and host_enrollment.get("trial_active") is True
            and host_enrollment.get("stopped") is False
            and host_status.get("ready_for_supervised_invite_only_trial") is True
        ),
        "host_public_service_still_closed": host_status.get("ready_for_external_user_trial") is False,
        "public_checkpoint_redacted": all(
            marker not in public_checkpoint_text
            for marker in (
                'invitation_code"', "invitation_sha256", "invitee_binding_hmac", "audit_secret"
            )
        ),
        "private_runtime_gitignored": run([
            "git", "check-ignore", str(PRIVATE_STATE.relative_to(ROOT))
        ]).returncode == 0,
        "private_values_absent_from_tracked_files": secret_hits == 0,
        "docker_status_available": docker_status_code == 200,
        "docker_private_state_absent": docker_private_state_absent(),
        "docker_enrollment_api_unavailable": docker_enrollment_code == 404,
        "docker_operator_cards_unavailable": docker_cards_code in {403, 404},
        "docker_trial_chat_rejected": docker_trial_code == 409 and docker_trial.get("trial_active") is False,
        "docker_supervised_trial_inactive": docker_status.get("ready_for_supervised_invite_only_trial") is False,
        "docker_public_service_closed": docker_status.get("ready_for_external_user_trial") is False,
        "docker_localhost_only": port in {"127.0.0.1:8766", "[::1]:8766"},
    }
    report = {
        "schema_version": "psm_v0_263_completed_enrollment_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "published_port": port,
        "tracked_private_secret_hits": secret_hits,
        "host": {
            "version": host_status.get("version"),
            "counts": host_enrollment.get("counts"),
            "trial_active": host_enrollment.get("trial_active"),
        },
        "docker": {
            "version": docker_status.get("version"),
            "private_state_present": False,
            "enrollment_api_status": docker_enrollment_code,
            "operator_cards_status": docker_cards_code,
            "trial_chat_status": docker_trial_code,
            "trial_active": docker_status.get("ready_for_supervised_invite_only_trial"),
        },
        "release_boundary": checkpoint.get("release_boundary"),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"V0.263 completed Docker boundary failed: {failed}")


if __name__ == "__main__":
    main()
