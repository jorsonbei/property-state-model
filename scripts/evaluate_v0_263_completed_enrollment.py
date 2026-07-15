from __future__ import annotations

import json
import stat
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
PRIVATE_STATE = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
PROTOCOL = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_263_participant_enrollment_checkpoint.json"
OUT = PSM_ROOT / "runtime" / "v0_263_completed_enrollment_gate.json"
HOST_STATUS_URL = "http://127.0.0.1:8765/api/trial-enrollment"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tracked_secret_hits(state: dict) -> int:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit("Unable to enumerate Git-tracked files.")
    secrets = [str(state.get("audit_secret_hex") or "").encode()]
    for participant in state.get("participants") or []:
        secrets.extend(
            str(participant.get(key) or "").encode()
            for key in (
                "invitation_code",
                "invitation_sha256",
                "invitee_binding_hmac_sha256",
            )
        )
    files = [ROOT / raw.decode() for raw in completed.stdout.split(b"\0") if raw]
    return sum(secret in path.read_bytes() for path in files for secret in secrets if secret)


def ordered_receipt(participant: dict) -> bool:
    fields = (
        "adult_verified_at",
        "notice_displayed_at",
        "notice_acknowledged_at",
        "consented_at",
        "session_enabled_at",
    )
    values = [participant.get(field) for field in fields]
    if any(not value for value in values):
        return False
    timestamps = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in values]
    return timestamps == sorted(timestamps) and len(set(timestamps)) == len(timestamps)


def live_public_status() -> dict:
    with urllib.request.urlopen(HOST_STATUS_URL, timeout=10) as response:
        if response.status != 200:
            raise SystemExit(f"Host enrollment API returned {response.status}.")
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    from psm_v0.external_trial_protocol import load_protocol, validate_audit_event
    from psm_v0.participant_enrollment import validate_private_state, validate_trial_access

    state = read_json(PRIVATE_STATE)
    protocol = load_protocol(PROTOCOL)
    checkpoint = read_json(CHECKPOINT)
    public = live_public_status()
    participants = state.get("participants") or []
    events = state.get("audit_events") or []
    participant_by_id = {item.get("participant_id"): item for item in participants}
    event_participants = {event.get("participant_id") for event in events}
    public_text = json.dumps({"checkpoint": checkpoint, "api": public}, ensure_ascii=False)
    private_values = [state.get("audit_secret_hex")]
    for participant in participants:
        private_values.extend(
            participant.get(key)
            for key in ("invitation_code", "invitation_sha256", "invitee_binding_hmac_sha256")
        )
    access_passes = sum(
        not validate_trial_access(
            state,
            participant_id=participant["participant_id"],
            invitation_code=participant["invitation_code"],
            protocol=protocol,
        )
        for participant in participants
    )
    session_events_after_enablement = all(
        event.get("participant_id") in participant_by_id
        and datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
        >= datetime.fromisoformat(
            participant_by_id[event["participant_id"]]["session_enabled_at"].replace("Z", "+00:00")
        )
        for event in events
    )
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
        "private_schema_valid": not validate_private_state(state, protocol),
        "exact_three_pseudonymous_participants": (
            state.get("participant_count") == 3
            and [item.get("participant_id") for item in participants] == ["P01", "P02", "P03"]
        ),
        "three_strictly_ordered_consent_receipts": all(ordered_receipt(item) for item in participants),
        "three_operator_supervision_attestations": all(
            item.get("operator_supervision_attested") is True for item in participants
        ),
        "cohort_gate_passed": (
            state.get("trial_active") is True
            and state.get("stopped") is False
            and (state.get("trial_start_gate") or {}).get("passed") is True
            and (state.get("trial_start_gate") or {}).get("active_participants") == 3
        ),
        "all_three_private_access_checks_pass": access_passes == 3,
        "public_api_matches_private_aggregate": (
            public.get("counts") == expected_counts
            and public.get("trial_active") is True
            and public.get("stopped") is False
        ),
        "public_checkpoint_matches_private_aggregate": (
            checkpoint.get("adult_verified") == 3
            and checkpoint.get("notice_acknowledged") == 3
            and checkpoint.get("explicitly_consented") == 3
            and checkpoint.get("session_enabled") == 3
            and checkpoint.get("trial_active") is True
        ),
        "public_surfaces_contain_no_private_values": all(
            not value or str(value) not in public_text for value in private_values
        ),
        "private_file_owner_only": stat.S_IMODE(PRIVATE_STATE.stat().st_mode) == 0o600,
        "private_directory_owner_only": stat.S_IMODE(PRIVATE_STATE.parent.stat().st_mode) == 0o700,
        "private_runtime_gitignored": subprocess.run(
            ["git", "check-ignore", str(PRIVATE_STATE.relative_to(ROOT))],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode == 0,
        "private_values_absent_from_tracked_files": tracked_secret_hits(state) == 0,
        "first_supervised_low_risk_session_observed": len(events) >= 1,
        "session_events_follow_enablement": session_events_after_enablement,
        "audit_events_schema_valid": all(not validate_audit_event(event) for event in events),
        "audit_events_content_free": all(
            event.get("raw_prompt_persisted") is False
            and event.get("participant_content_sent_to_external_api") is False
            and "prompt" not in event
            and "answer" not in event
            for event in events
        ),
        "observed_events_are_allowed_low_risk": all(
            event.get("allowed") is True and event.get("categories") == ["low_risk_general"]
            for event in events
        ),
        "release_authority_remains_closed": all(
            public.get("release_boundary", {}).get(key) is False
            for key in (
                "public_service_allowed",
                "privacy_compliance_claimed",
                "training_on_trial_data_allowed",
                "rule_replacement_allowed",
                "external_release_authority",
            )
        ),
    }
    report = {
        "schema_version": "psm_v0_263_completed_enrollment_gate_v1",
        "version": "PSM_V0.263",
        "passed": all(checks.values()),
        "decision": "three_person_supervised_enrollment_complete",
        "checks": checks,
        "aggregate_evidence": {
            "selected_participants": len(participants),
            "completed_receipts": sum(ordered_receipt(item) for item in participants),
            "private_access_checks_passed": access_passes,
            "content_free_session_events": len(events),
            "participants_with_observed_session_events": len(event_participants),
            "allowed_events": sum(event.get("allowed") is True for event in events),
            "rejected_events": sum(event.get("allowed") is False for event in events),
            "raw_prompts_persisted": sum(event.get("raw_prompt_persisted") is True for event in events),
            "participant_content_external_api_calls": sum(
                event.get("participant_content_sent_to_external_api") is True for event in events
            ),
        },
        "identity_boundary": {
            "direct_identity_collected_in_project": False,
            "identity_or_adulthood_independently_verified_by_software": False,
            "operator_attestations_recorded": 3,
            "private_invitation_values_published": False,
        },
        "release_boundary": public.get("release_boundary"),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"V0.263 completed enrollment gate failed: {failed}")


if __name__ == "__main__":
    main()
