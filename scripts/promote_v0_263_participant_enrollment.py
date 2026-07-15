from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.262_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.263_project_status.json"
PRIVATE_STATE = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
PROTOCOL = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"
GATE = RUNTIME / "v0_263_completed_enrollment_gate.json"
BROWSER = RUNTIME / "v0_263_completed_enrollment_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_263_completed_enrollment_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_263_participant_enrollment_checkpoint.json"
MANIFEST = RUNTIME / "v0_263_enrollment_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    from psm_v0.external_trial_protocol import load_protocol
    from psm_v0.participant_enrollment import load_private_state, write_public_checkpoint

    source = read_json(SOURCE_STATUS)
    gate = read_json(GATE)
    browser = read_json(BROWSER)
    docker = read_json(DOCKER)
    protocol = load_protocol(PROTOCOL)
    state = load_private_state(PRIVATE_STATE, protocol)
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.263 completed enrollment gate is not passing.")
    if gate.get("decision") != "three_person_supervised_enrollment_complete":
        raise SystemExit("V0.263 completion decision is not promotable.")
    if browser.get("passed") is not True or browser.get("trial_active") is not True:
        raise SystemExit("V0.263 completed enrollment browser evidence is not passing.")
    if browser.get("participant_chat_messages_sent") is not False:
        raise SystemExit("Browser promotion evidence impersonated a participant.")
    if docker.get("passed") is not True or docker.get("tracked_private_secret_hits") != 0:
        raise SystemExit("V0.263 completed enrollment Docker boundary is not passing.")
    if state.get("trial_active") is not True or state.get("stopped") is not False:
        raise SystemExit("Live V0.263 trial state is not active and clean.")

    aggregate = gate["aggregate_evidence"]
    promotion_gate = {
        "decision": gate["decision"],
        "passed": True,
        "selected_participants": aggregate["selected_participants"],
        "completed_receipts": aggregate["completed_receipts"],
        "private_access_checks_passed": aggregate["private_access_checks_passed"],
        "content_free_session_events_at_promotion": aggregate["content_free_session_events"],
        "participants_with_session_events_at_promotion": aggregate["participants_with_observed_session_events"],
        "raw_prompts_persisted": aggregate["raw_prompts_persisted"],
        "participant_content_external_api_calls": aggregate["participant_content_external_api_calls"],
        "completion_gate_sha256": canonical_sha256(gate),
    }
    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.263"
    target["previous_formal_version"] = "psm_v0.262"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "three_person_supervised_trial_enrollment_completed"
    target["v0_263_enrollment_gate"] = promotion_gate
    target["next_stage"] = {
        "version": "PSM_V0.264",
        "objective": (
            "Run a bounded supervised pilot across all three enrolled pseudonymous participants. Require at least three low-risk general "
            "turns per participant, retain only content-free seven-day operational metadata, collect no direct identity or raw chat content, "
            "and stop without automatic resume on any prohibited, privacy, consent, supervision, or provider-boundary event."
        ),
        "blocked": True,
        "requires_user_input": True,
    }
    target.setdefault("primary_artifacts", {}).update({
        "v0_263_selection_contract": "benchmarks/v0_263_three_participant_enrollment_contract.json",
        "v0_263_completion_gate": "runtime/v0_263_completed_enrollment_gate.json",
        "v0_263_completed_browser": "runtime/v0_263_completed_enrollment_browser_regression/report.json",
        "v0_263_completed_docker": "runtime/v0_263_completed_enrollment_docker_boundary.json",
        "v0_263_checkpoint": "runtime/v0_263_participant_enrollment_checkpoint.json",
        "v0_263_promotion_manifest": "runtime/v0_263_enrollment_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.263_project_status.json",
    })
    write_json(TARGET_STATUS, target)
    manifest = {
        "schema_version": "psm_v0_263_enrollment_promotion_manifest_v1",
        "version": "PSM_V0.263",
        "promoted_at": "2026-07-15",
        "promoted": True,
        "decision": promotion_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "enrollment_gate": promotion_gate,
        "evidence": {
            "completion_gate": str(GATE.relative_to(PSM_ROOT)),
            "browser": str(BROWSER.relative_to(PSM_ROOT)),
            "docker_boundary": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": gate["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    write_public_checkpoint(CHECKPOINT, state)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.264")


if __name__ == "__main__":
    main()
