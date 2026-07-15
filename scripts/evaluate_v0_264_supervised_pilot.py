from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_264_supervised_pilot_contract.json"
PARENT = PSM_ROOT / "runtime" / "v0_263_enrollment_promotion_manifest.json"
PRIVATE_STATE = PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"
PROTOCOL = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"
OUT = PSM_ROOT / "runtime" / "v0_264_supervised_pilot_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_264_supervised_pilot_checkpoint.json"
MANIFEST = PSM_ROOT / "runtime" / "v0_264_supervised_pilot_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the V0.264 supervised three-person pilot.")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    from psm_v0.external_trial_protocol import load_protocol, validate_audit_event
    from psm_v0.participant_enrollment import (
        load_private_state,
        supervised_pilot_progress,
        validate_private_state,
    )

    contract = read_json(CONTRACT)
    parent = read_json(PARENT)
    protocol = load_protocol(PROTOCOL)
    state = load_private_state(PRIVATE_STATE, protocol)
    progress = supervised_pilot_progress(state)
    events = state.get("audit_events") or []
    expected_parent_hash = (contract.get("parent_promotion") or {}).get("canonical_sha256")
    contract_scope = contract.get("scope") or {}
    checks = {
        "contract_schema_valid": contract.get("schema_version") == "psm_v0_264_supervised_pilot_contract_v1",
        "parent_v0_263_promoted": parent.get("version") == "PSM_V0.263" and parent.get("promoted") is True,
        "parent_promotion_hash_locked": expected_parent_hash == canonical_sha256(parent),
        "private_state_valid": not validate_private_state(state, protocol),
        "exact_frozen_three_person_scope": (
            contract_scope.get("participant_ids") == ["P01", "P02", "P03"]
            and progress.get("participant_count") == 3
        ),
        "operator_supervised_trial_active": state.get("trial_active") is True and state.get("stopped") is False,
        "audit_events_schema_valid": all(not validate_audit_event(event) for event in events),
        "audit_events_content_free": all(
            event.get("raw_prompt_persisted") is False
            and event.get("participant_content_sent_to_external_api") is False
            and "prompt" not in event
            and "answer" not in event
            for event in events
        ),
        "no_rejected_or_prohibited_events": all(event.get("allowed") is True for event in events),
        "all_observed_events_low_risk_general": all(
            event.get("categories") == ["low_risk_general"] for event in events
        ),
        "all_three_participants_meet_three_turn_minimum": progress.get("gate_passed") is True,
        "release_authority_remains_closed": all(
            (contract.get("release_boundary") or {}).get(key) is False
            for key in (
                "public_service_allowed",
                "privacy_compliance_claimed",
                "production_readiness_claimed",
                "training_on_trial_data_allowed",
                "rule_replacement_allowed",
                "external_release_authority",
            )
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    participant_progress = progress.get("participants") or []
    missing = [
        {
            "participant_id": item["participant_id"],
            "credited_turns": item["credited_turns"],
            "required_turns": item["required_turns"],
            "remaining_turns": max(0, item["required_turns"] - item["credited_turns"]),
        }
        for item in participant_progress
        if not item["complete"]
    ]
    passed = not failed_checks
    gate = {
        "schema_version": "psm_v0_264_supervised_pilot_gate_v1",
        "version": "PSM_V0.264",
        "passed": passed,
        "decision": "three_person_supervised_pilot_complete" if passed else "blocked_on_real_participant_turn_coverage",
        "checks": checks,
        "progress": progress,
        "missing_turn_coverage": missing,
        "aggregate_evidence": {
            "content_free_events": len(events),
            "allowed_low_risk_events": sum(
                event.get("allowed") is True and event.get("categories") == ["low_risk_general"]
                for event in events
            ),
            "rejected_events": sum(event.get("allowed") is False for event in events),
            "raw_prompts_persisted": sum(event.get("raw_prompt_persisted") is True for event in events),
            "participant_content_external_api_calls": sum(
                event.get("participant_content_sent_to_external_api") is True for event in events
            ),
        },
        "release_boundary": contract.get("release_boundary"),
    }
    decision = (
        "三名化名参与者均已完成至少三次低风险现场监督会话；可以进入独立质量复核，但仍不得开放公开服务。"
        if passed
        else "V0.264 需要真实参与者继续现场监督试用："
        + "；".join(
            f"{item['participant_id']} 还需 {item['remaining_turns']} 次低风险一般问题"
            for item in missing
        )
        + "。不要输入姓名、联络方式、证件、秘密、医疗、法律或交易决策资料。"
    )
    promoted = False
    if MANIFEST.exists():
        manifest = read_json(MANIFEST)
        promoted = (
            manifest.get("schema_version") == "psm_v0_264_supervised_pilot_promotion_manifest_v1"
            and manifest.get("version") == "PSM_V0.264"
            and manifest.get("promoted") is True
        )
    checkpoint = {
        "schema_version": "psm_v0_264_supervised_pilot_checkpoint_v1",
        "current_promoted_version": "PSM_V0.264" if promoted else "PSM_V0.263",
        "target_version": "PSM_V0.264",
        "target_promoted": promoted,
        "status": "v0_264_promoted_awaiting_structured_quality_feedback" if promoted else gate["decision"],
        "requires_user_input": not passed,
        "progress": progress,
        "missing_turn_coverage": missing,
        "private_state_committed_to_git": False,
        "raw_chat_content_committed_to_git": False,
        "release_boundary": contract.get("release_boundary"),
        "required_decision": decision,
    }
    write_json(OUT, gate)
    write_json(CHECKPOINT, checkpoint)
    print(json.dumps(checkpoint, ensure_ascii=False, indent=2))
    if not passed and not args.allow_incomplete:
        raise SystemExit("V0.264 supervised pilot is incomplete: " + ", ".join(failed_checks))


if __name__ == "__main__":
    main()
