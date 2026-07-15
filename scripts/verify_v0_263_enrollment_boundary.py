from __future__ import annotations

import json
import stat
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_263_enrollment_docker_boundary.json"
PRIVATE_STATE = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_263_participant_enrollment_checkpoint.json"
HOST_URL = "http://127.0.0.1:8765"
DOCKER_URL = "http://127.0.0.1:8766"


def request_json(base_url: str, path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def request_text(base_url: str, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(base_url + path, timeout=15) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def docker_private_state_absent() -> bool:
    completed = run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "psm-chat",
            "python",
            "-c",
            (
                "from pathlib import Path;"
                "print('absent' if not Path('/app/outputs/psm_v0/private_runtime').exists() else 'present')"
            ),
        ]
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or "Docker private-state inspection failed.")
    return completed.stdout.strip() == "absent"


def published_port() -> str:
    completed = run(["docker", "compose", "port", "psm-chat", "8765"])
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or "Docker port inspection failed.")
    return completed.stdout.strip()


def tracked_secret_hits(private_state: dict) -> int:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit("Unable to enumerate Git-tracked files.")
    secrets = []
    for participant in private_state.get("participants") or []:
        secrets.extend(
            str(participant.get(key) or "").encode("utf-8")
            for key in ("invitation_code", "invitation_sha256", "invitee_binding_hmac_sha256")
        )
    secrets.append(str(private_state.get("audit_secret_hex") or "").encode("utf-8"))
    files = [ROOT / raw.decode("utf-8") for raw in completed.stdout.split(b"\0") if raw]
    hits = 0
    for path in files:
        content = path.read_bytes()
        hits += sum(bool(secret) and secret in content for secret in secrets)
    return hits


def main() -> None:
    private_state = json.loads(PRIVATE_STATE.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    host_status_code, host_status = request_json(HOST_URL, "/api/status")
    host_enrollment_code, host_enrollment = request_json(HOST_URL, "/api/trial-enrollment")
    host_cards_code, host_cards = request_json(HOST_URL, "/api/trial-enrollment/operator-cards")
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
            "messages": [{"role": "user", "content": "容器边界检查"}],
        },
    )
    docker_page_code, docker_page = request_text(DOCKER_URL, "/trial-enrollment")
    public_checkpoint_text = json.dumps(checkpoint, ensure_ascii=False)
    public_host_text = json.dumps(host_enrollment, ensure_ascii=False)
    private_mode = stat.S_IMODE(PRIVATE_STATE.stat().st_mode)
    private_dir_mode = stat.S_IMODE(PRIVATE_STATE.parent.stat().st_mode)
    port = published_port()
    secret_hits = tracked_secret_hits(private_state)
    checks = {
        "host_status_available": host_status_code == 200,
        "host_selected_exactly_three": host_status.get("v0_263_selected_participant_count") == 3,
        "host_three_private_invitations_ready": host_status.get("v0_263_pseudonymous_invitations_generated") == 3,
        "host_enrollment_interface_ready": host_status.get("v0_263_enrollment_interface_ready") is True,
        "host_human_counts_all_zero": (
            host_enrollment_code == 200
            and host_enrollment.get("counts")
            == {
                "invited": 3,
                "adult_verified": 0,
                "notice_displayed": 0,
                "notice_acknowledged": 0,
                "consented": 0,
                "session_enabled": 0,
                "revoked": 0,
            }
        ),
        "host_trial_inactive": (
            host_enrollment.get("trial_active") is False
            and host_status.get("ready_for_supervised_invite_only_trial") is False
            and host_status.get("ready_for_external_user_trial") is False
        ),
        "host_operator_cards_private_count_three": (
            host_cards_code == 200 and len(host_cards.get("participants") or []) == 3
        ),
        "public_host_status_redacted": (
            "invitation_code" not in public_host_text
            and "audit_secret" not in public_host_text
            and "invitee_binding_hmac" not in public_host_text
        ),
        "public_checkpoint_redacted": (
            "invitation_code\"" not in public_checkpoint_text
            and "audit_secret" not in public_checkpoint_text
            and "invitee_binding_hmac" not in public_checkpoint_text
        ),
        "private_file_owner_only": private_mode == 0o600,
        "private_directory_owner_only": private_dir_mode == 0o700,
        "private_runtime_gitignored": run(["git", "check-ignore", str(PRIVATE_STATE.relative_to(ROOT))]).returncode == 0,
        "private_secrets_absent_from_tracked_files": secret_hits == 0,
        "docker_status_available": docker_status_code == 200,
        "docker_retains_public_three_person_checkpoint": (
            docker_status.get("v0_263_selected_participant_count") == 3
            and docker_status.get("v0_263_pseudonymous_invitations_generated") == 3
        ),
        "docker_private_state_absent": docker_private_state_absent(),
        "docker_enrollment_api_unavailable": docker_enrollment_code == 404,
        "docker_operator_cards_unavailable": docker_cards_code in {403, 404},
        "docker_trial_chat_rejected": docker_trial_code == 409 and docker_trial.get("trial_active") is False,
        "docker_interface_reports_unavailable": docker_status.get("v0_263_enrollment_interface_ready") is False,
        "docker_trial_inactive": (
            docker_status.get("ready_for_supervised_invite_only_trial") is False
            and docker_status.get("ready_for_external_user_trial") is False
        ),
        "docker_page_contains_no_invitation": (
            docker_page_code == 200
            and "invitation_code" not in docker_page
        ),
        "docker_localhost_only": port in {"127.0.0.1:8766", "[::1]:8766"},
        "target_not_promoted": checkpoint.get("target_promoted") is False,
        "human_action_still_required": checkpoint.get("requires_user_input") is True,
    }
    report = {
        "schema_version": "psm_v0_263_enrollment_docker_boundary_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "published_port": port,
        "tracked_private_secret_hits": secret_hits,
        "host": {
            "selected_participant_count": host_status.get("v0_263_selected_participant_count"),
            "invitations_generated": host_status.get("v0_263_pseudonymous_invitations_generated"),
            "enrollment_interface_ready": host_status.get("v0_263_enrollment_interface_ready"),
            "trial_active": host_enrollment.get("trial_active"),
            "counts": host_enrollment.get("counts"),
        },
        "docker": {
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
        raise SystemExit(f"V0.263 enrollment Docker boundary failed: {failed}")


if __name__ == "__main__":
    main()
