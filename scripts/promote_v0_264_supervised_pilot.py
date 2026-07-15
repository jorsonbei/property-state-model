from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.263_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.264_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_264_supervised_pilot_contract.json"
GATE = RUNTIME / "v0_264_supervised_pilot_gate.json"
BROWSER = RUNTIME / "v0_264_supervised_pilot_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_264_supervised_pilot_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_264_supervised_pilot_checkpoint.json"
MANIFEST = RUNTIME / "v0_264_supervised_pilot_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    source = read_json(SOURCE_STATUS)
    contract = read_json(CONTRACT)
    gate = read_json(GATE)
    browser = read_json(BROWSER)
    docker = read_json(DOCKER)
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.264 supervised pilot gate is not passing.")
    if gate.get("decision") != "three_person_supervised_pilot_complete":
        raise SystemExit("V0.264 pilot decision is not promotable.")
    if browser.get("passed") is not True or browser.get("participant_chat_messages_sent") is not False:
        raise SystemExit("V0.264 browser evidence is not passing or impersonated a participant.")
    if docker.get("passed") is not True or docker.get("tracked_private_secret_hits") != 0:
        raise SystemExit("V0.264 Docker boundary is not passing.")
    progress = gate["progress"]
    if progress.get("completed_participants") != 3 or progress.get("gate_passed") is not True:
        raise SystemExit("V0.264 participant coverage is incomplete.")
    promotion_gate = {
        "decision": gate["decision"],
        "passed": True,
        "participant_count": progress["participant_count"],
        "required_turns_per_participant": progress["required_turns_per_participant"],
        "completed_participants": progress["completed_participants"],
        "total_content_free_low_risk_events": progress["total_observed_low_risk_turns"],
        "credited_turns": [item["credited_turns"] for item in progress["participants"]],
        "rejected_events": gate["aggregate_evidence"]["rejected_events"],
        "raw_prompts_persisted": gate["aggregate_evidence"]["raw_prompts_persisted"],
        "participant_content_external_api_calls": gate["aggregate_evidence"]["participant_content_external_api_calls"],
        "gate_sha256": canonical_sha256(gate),
        "contract_sha256": canonical_sha256(contract),
    }
    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.264"
    target["previous_formal_version"] = "psm_v0.263"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "three_person_content_free_supervised_pilot_complete"
    target["v0_264_supervised_pilot_gate"] = promotion_gate
    target["next_stage"] = {
        "version": "PSM_V0.265",
        "objective": (
            "Collect structured content-free participant feedback on new supervised low-risk turns. Require three rated turns per "
            "participant using fixed helpfulness, clarity, state-alignment, and issue-category fields; allow no free text, direct identity, "
            "raw prompt or answer retention, external participant-content calls, automatic training, or public release claims."
        ),
        "blocked": True,
        "requires_user_input": True,
    }
    target.setdefault("primary_artifacts", {}).update({
        "v0_264_contract": "benchmarks/v0_264_supervised_pilot_contract.json",
        "v0_264_gate": "runtime/v0_264_supervised_pilot_gate.json",
        "v0_264_browser": "runtime/v0_264_supervised_pilot_browser_regression/report.json",
        "v0_264_docker": "runtime/v0_264_supervised_pilot_docker_boundary.json",
        "v0_264_checkpoint": "runtime/v0_264_supervised_pilot_checkpoint.json",
        "v0_264_promotion_manifest": "runtime/v0_264_supervised_pilot_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.264_project_status.json",
    })
    write_json(TARGET_STATUS, target)
    manifest = {
        "schema_version": "psm_v0_264_supervised_pilot_promotion_manifest_v1",
        "version": "PSM_V0.264",
        "promoted_at": "2026-07-15",
        "promoted": True,
        "decision": promotion_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "pilot_gate": promotion_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
            "browser": str(BROWSER.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": gate["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    checkpoint = read_json(CHECKPOINT)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.264",
        "target_promoted": True,
        "status": "v0_264_promoted_awaiting_structured_quality_feedback",
        "requires_user_input": False,
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
    })
    write_json(CHECKPOINT, checkpoint)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.265")


if __name__ == "__main__":
    main()
