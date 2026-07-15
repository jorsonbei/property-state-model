from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .external_trial_protocol import (
    PARTICIPANT_ID_PATTERN,
    SHA256_PATTERN,
    build_content_free_audit_event,
    canonical_sha256,
    purge_expired_events,
    trial_start_gate,
    validate_audit_event,
    validate_consent_receipt,
)


ENROLLMENT_SCHEMA = "psm_v0_263_private_enrollment_state_v1"
PUBLIC_STATUS_SCHEMA = "psm_v0_263_enrollment_status_v1"
OPERATOR_CARDS_SCHEMA = "psm_v0_263_operator_invitation_cards_v1"
CHECKPOINT_SCHEMA = "psm_v0_263_participant_enrollment_checkpoint_v1"
ALLOWED_ACTIONS = {
    "verify_adult",
    "display_notice",
    "acknowledge_notice",
    "consent",
    "enable_session",
    "revoke",
}
ACTION_ATTESTATIONS = {
    "verify_adult": "operator_verified_pre_vetted_adult_invitee",
    "display_notice": "operator_displayed_frozen_notice",
    "acknowledge_notice": "participant_acknowledged_notice",
    "consent": "participant_explicit_opt_in",
    "enable_session": "operator_supervision_attested",
    "revoke": "participant_withdrawal_requested",
}
PRIVATE_STATE_FIELDS = {
    "schema_version",
    "stage_version",
    "protocol_sha256",
    "participant_count",
    "prepared_at",
    "private_only",
    "status",
    "trial_active",
    "stopped",
    "stop_reasons",
    "audit_secret_hex",
    "participants",
    "audit_events",
    "trial_start_gate",
}
PARTICIPANT_FIELDS = {
    "participant_id",
    "invitation_code",
    "invitation_sha256",
    "invitee_binding_hmac_sha256",
    "adult_confirmed",
    "adult_verified_by_operator",
    "adult_verification_method",
    "adult_verified_at",
    "notice_version",
    "notice_displayed_at",
    "notice_acknowledged",
    "notice_acknowledged_at",
    "consented_at",
    "session_enabled_at",
    "operator_supervision_attested",
    "revoked_at",
}
FORBIDDEN_IDENTITY_KEYS = {
    "name",
    "full_name",
    "email",
    "phone",
    "address",
    "identity_document",
    "government_id",
    "date_of_birth",
}


class EnrollmentError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def initialize_enrollment(
    *,
    participant_count: int,
    protocol: dict,
    binding_secret: bytes,
    prepared_at: datetime | None = None,
    invitation_codes: list[str] | None = None,
) -> dict:
    scope = protocol.get("trial_scope") or {}
    minimum = int(scope.get("participant_minimum") or 0)
    maximum = int(scope.get("participant_maximum") or 0)
    if participant_count < minimum or participant_count > maximum:
        raise EnrollmentError(f"participant count must be between {minimum} and {maximum}")
    if not binding_secret or len(binding_secret) < 32:
        raise EnrollmentError("binding secret must contain at least 32 bytes")
    codes = invitation_codes or [secrets.token_urlsafe(18) for _ in range(participant_count)]
    if len(codes) != participant_count or len(set(codes)) != participant_count:
        raise EnrollmentError("invitation codes must be unique and match participant count")
    if any(len(code) < 16 for code in codes):
        raise EnrollmentError("invitation codes are too short")

    participants = []
    notice_version = protocol["consent"]["notice_version"]
    for index, code in enumerate(codes, start=1):
        participant_id = f"P{index:02d}"
        invitation_sha256 = hashlib.sha256(code.encode("utf-8")).hexdigest()
        binding = hmac.new(
            binding_secret,
            f"{participant_id}:{code}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        participants.append(
            {
                "participant_id": participant_id,
                "invitation_code": code,
                "invitation_sha256": invitation_sha256,
                "invitee_binding_hmac_sha256": binding,
                "adult_confirmed": False,
                "adult_verified_by_operator": False,
                "adult_verification_method": None,
                "adult_verified_at": None,
                "notice_version": notice_version,
                "notice_displayed_at": None,
                "notice_acknowledged": False,
                "notice_acknowledged_at": None,
                "consented_at": None,
                "session_enabled_at": None,
                "operator_supervision_attested": False,
                "revoked_at": None,
            }
        )
    prepared = (prepared_at or utc_now()).astimezone(timezone.utc)
    audit_secret = hmac.new(binding_secret, b"psm-v0.263-audit", hashlib.sha256).hexdigest()
    state = {
        "schema_version": ENROLLMENT_SCHEMA,
        "stage_version": "PSM_V0.263",
        "protocol_sha256": canonical_sha256(protocol),
        "participant_count": participant_count,
        "prepared_at": prepared.isoformat(),
        "private_only": True,
        "status": "awaiting_operator_adult_verification",
        "trial_active": False,
        "stopped": False,
        "stop_reasons": [],
        "audit_secret_hex": audit_secret,
        "participants": participants,
        "audit_events": [],
        "trial_start_gate": {
            "passed": False,
            "active_participants": 0,
            "errors": ["fewer than three active consented participants"],
        },
    }
    errors = validate_private_state(state, protocol)
    if errors:
        raise EnrollmentError("; ".join(errors))
    return state


def validate_private_state(state: dict, protocol: dict) -> list[str]:
    errors: list[str] = []
    if set(state) != PRIVATE_STATE_FIELDS:
        errors.append("private enrollment state fields are not closed")
    if state.get("schema_version") != ENROLLMENT_SCHEMA or state.get("stage_version") != "PSM_V0.263":
        errors.append("private enrollment schema or stage is invalid")
    if state.get("protocol_sha256") != canonical_sha256(protocol):
        errors.append("private enrollment state references a different frozen protocol")
    if state.get("private_only") is not True:
        errors.append("enrollment state is not marked private-only")
    count = state.get("participant_count")
    participants = state.get("participants")
    if not isinstance(count, int) or not isinstance(participants, list) or len(participants) != count:
        errors.append("participant count does not match enrollment records")
        participants = participants if isinstance(participants, list) else []
    if count is not None and count not in range(3, 6):
        errors.append("participant count is outside the approved 3-5 range")
    participant_ids = []
    invitation_hashes = []
    bindings = []
    for item in participants:
        if not isinstance(item, dict) or set(item) != PARTICIPANT_FIELDS:
            errors.append("participant enrollment fields are not closed")
            continue
        participant_id = str(item.get("participant_id") or "")
        participant_ids.append(participant_id)
        invitation_hashes.append(item.get("invitation_sha256"))
        bindings.append(item.get("invitee_binding_hmac_sha256"))
        if not PARTICIPANT_ID_PATTERN.fullmatch(participant_id):
            errors.append("participant ID is not pseudonymous")
        code = str(item.get("invitation_code") or "")
        if len(code) < 16 or hashlib.sha256(code.encode("utf-8")).hexdigest() != item.get("invitation_sha256"):
            errors.append("private invitation code does not match its hash")
        if not SHA256_PATTERN.fullmatch(str(item.get("invitee_binding_hmac_sha256") or "")):
            errors.append("invitee binding HMAC is invalid")
        if any(key in item for key in FORBIDDEN_IDENTITY_KEYS):
            errors.append("participant record contains a direct identity field")
    if len(set(participant_ids)) != len(participant_ids):
        errors.append("participant IDs are not unique")
    if len(set(invitation_hashes)) != len(invitation_hashes):
        errors.append("invitation hashes are not unique")
    if len(set(bindings)) != len(bindings):
        errors.append("invitee bindings are not one-to-one")
    if not SHA256_PATTERN.fullmatch(str(state.get("audit_secret_hex") or "")):
        errors.append("private audit secret is invalid")
    if state.get("trial_active") is True and not (state.get("trial_start_gate") or {}).get("passed"):
        errors.append("trial is active without a passing cohort gate")
    if state.get("stopped") is True and state.get("trial_active") is True:
        errors.append("stopped trial cannot remain active")
    for event in state.get("audit_events") or []:
        errors.extend(validate_audit_event(event))
    return errors


def build_consent_receipt(participant: dict) -> dict:
    return {
        "schema_version": "psm_v0_262_consent_receipt_v1",
        "participant_id": participant["participant_id"],
        "invitation_sha256": participant["invitation_sha256"],
        "invitee_binding_hmac_sha256": participant["invitee_binding_hmac_sha256"],
        "adult_confirmed": participant["adult_confirmed"],
        "adult_verified_by_operator": participant["adult_verified_by_operator"],
        "adult_verification_method": participant["adult_verification_method"],
        "adult_verified_at": participant["adult_verified_at"],
        "notice_version": participant["notice_version"],
        "notice_displayed_at": participant["notice_displayed_at"],
        "notice_acknowledged": participant["notice_acknowledged"],
        "notice_acknowledged_at": participant["notice_acknowledged_at"],
        "consented_at": participant["consented_at"],
        "session_enabled_at": participant["session_enabled_at"],
        "operator_supervision_attested": participant["operator_supervision_attested"],
        "revoked_at": participant["revoked_at"],
    }


def current_step(participant: dict) -> str:
    if participant.get("revoked_at"):
        return "revoked"
    if not participant.get("adult_verified_by_operator"):
        return "verify_adult"
    if not participant.get("notice_displayed_at"):
        return "display_notice"
    if not participant.get("notice_acknowledged"):
        return "acknowledge_notice"
    if not participant.get("consented_at"):
        return "consent"
    if not participant.get("session_enabled_at"):
        return "enable_session"
    return "ready"


def supervised_pilot_progress(state: dict, *, required_turns_per_participant: int = 3) -> dict:
    participants = state.get("participants") or []
    counts = {item.get("participant_id"): 0 for item in participants}
    for event in state.get("audit_events") or []:
        participant_id = event.get("participant_id")
        if (
            participant_id in counts
            and event.get("allowed") is True
            and event.get("categories") == ["low_risk_general"]
            and event.get("raw_prompt_persisted") is False
            and event.get("participant_content_sent_to_external_api") is False
        ):
            counts[participant_id] += 1
    participant_progress = [
        {
            "participant_id": item["participant_id"],
            "observed_turns": counts[item["participant_id"]],
            "credited_turns": min(counts[item["participant_id"]], required_turns_per_participant),
            "required_turns": required_turns_per_participant,
            "complete": counts[item["participant_id"]] >= required_turns_per_participant,
        }
        for item in participants
    ]
    completed = sum(item["complete"] for item in participant_progress)
    return {
        "schema_version": "psm_v0_264_supervised_pilot_progress_v1",
        "required_turns_per_participant": required_turns_per_participant,
        "completed_participants": completed,
        "participant_count": len(participants),
        "total_observed_low_risk_turns": sum(counts.values()),
        "gate_passed": (
            len(participants) == 3
            and completed == 3
            and state.get("trial_active") is True
            and state.get("stopped") is False
        ),
        "participants": participant_progress,
    }


def public_enrollment_status(state: dict) -> dict:
    participants = state.get("participants") or []
    counts = {
        "invited": len(participants),
        "adult_verified": sum(bool(item.get("adult_verified_by_operator")) for item in participants),
        "notice_displayed": sum(bool(item.get("notice_displayed_at")) for item in participants),
        "notice_acknowledged": sum(bool(item.get("notice_acknowledged")) for item in participants),
        "consented": sum(bool(item.get("consented_at")) for item in participants),
        "session_enabled": sum(bool(item.get("session_enabled_at")) for item in participants),
        "revoked": sum(bool(item.get("revoked_at")) for item in participants),
    }
    return {
        "schema_version": PUBLIC_STATUS_SCHEMA,
        "stage_version": state.get("stage_version"),
        "status": state.get("status"),
        "participant_count": state.get("participant_count"),
        "counts": counts,
        "trial_active": state.get("trial_active") is True,
        "stopped": state.get("stopped") is True,
        "stop_reasons": list(state.get("stop_reasons") or []),
        "requires_operator_and_participant_action": state.get("trial_active") is not True,
        "participants": [
            {
                "participant_id": item["participant_id"],
                "current_step": current_step(item),
                "adult_verified": bool(item.get("adult_verified_by_operator")),
                "notice_displayed": bool(item.get("notice_displayed_at")),
                "notice_acknowledged": bool(item.get("notice_acknowledged")),
                "consented": bool(item.get("consented_at")),
                "session_enabled": bool(item.get("session_enabled_at")),
                "revoked": bool(item.get("revoked_at")),
            }
            for item in participants
        ],
        "pilot_progress": supervised_pilot_progress(state),
        "release_boundary": {
            "supervised_invite_only_trial_active": state.get("trial_active") is True,
            "public_service_allowed": False,
            "privacy_compliance_claimed": False,
            "training_on_trial_data_allowed": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
    }


def build_enrollment_checkpoint(state: dict, *, promoted: bool = False) -> dict:
    public = public_enrollment_status(state)
    trial_active = public["trial_active"]
    stopped = public["stopped"]
    if stopped:
        status = "stopped_requires_operator_review"
        required_decision = (
            "试用已按冻结协议停止，不得自动恢复。请保留内容为空的停止证据，先完成独立操作员审查；"
            "不要在聊天或 GitHub 中提交参与者身份或敏感资料。"
        )
    elif trial_active:
        if promoted:
            status = "v0_263_promoted_supervised_pilot_active"
            required_decision = (
                "V0.263 三人登记与首轮低风险会话证据已通过。继续 V0.264 受控试用时，"
                "仍只允许三名已登记参与者在操作员现场监督下使用；不得开放公开服务。"
            )
        else:
            status = "supervised_trial_active_awaiting_first_session"
            required_decision = (
                "三人门控已通过。只允许三名已登记参与者在操作员现场监督下使用试用聊天；"
                "下一步是记录首轮低风险会话证据，不得开放公开服务。"
            )
    else:
        status = "awaiting_three_real_adult_enrollment_sequences"
        required_decision = (
            "三名受邀者到场后，请在本机 V0.263 登记页面逐一完成：操作员线下核验其为成年人、展示告知、"
            "由参与者确认并明确同意、操作员确认现场监督。不要向聊天或 GitHub 提交任何姓名、联系方式或证件。"
        )
    return {
        "schema_version": CHECKPOINT_SCHEMA,
        "current_promoted_version": "PSM_V0.263" if promoted else "PSM_V0.262",
        "target_version": "PSM_V0.263",
        "target_promoted": promoted,
        "status": status,
        "participant_count_selected": public["participant_count"],
        "pseudonymous_invitations_generated": public["counts"]["invited"],
        "adult_verified": public["counts"]["adult_verified"],
        "notice_acknowledged": public["counts"]["notice_acknowledged"],
        "explicitly_consented": public["counts"]["consented"],
        "session_enabled": public["counts"]["session_enabled"],
        "trial_active": trial_active,
        "requires_user_input": not trial_active,
        "private_state_committed_to_git": False,
        "invitation_codes_exposed_in_public_artifacts": False,
        "completed_engineering": [
            "three-participant user selection frozen without asserting adulthood or consent",
            "three unique pseudonymous invitations generated in owner-only local storage",
            "one-to-one secret-HMAC invitee binding rooted in macOS Keychain",
            "strict adult, notice, acknowledgment, consent, and supervision state machine",
            "three-of-three cohort gate before any real trial chat",
            "sensitive-data detection stops all trial sessions without automatic resume",
            "participant withdrawal deletes that participant's operational audit events",
            "desktop and mobile enrollment UI passed masked-code browser regression",
            "Docker retains the public checkpoint but excludes private enrollment state",
        ],
        "evidence": {
            "browser": "runtime/v0_263_enrollment_browser_regression/report.json",
            "docker_boundary": "runtime/v0_263_enrollment_docker_boundary.json",
            **(
                {
                    "completion_gate": "runtime/v0_263_completed_enrollment_gate.json",
                    "completed_browser": "runtime/v0_263_completed_enrollment_browser_regression/report.json",
                    "completed_docker_boundary": "runtime/v0_263_completed_enrollment_docker_boundary.json",
                    "promotion_manifest": "runtime/v0_263_enrollment_promotion_manifest.json",
                }
                if promoted
                else {}
            ),
        },
        "release_boundary": public["release_boundary"],
        "required_decision": required_decision,
    }


def write_public_checkpoint(path: Path, state: dict) -> None:
    manifest_path = path.with_name("v0_263_enrollment_promotion_manifest.json")
    promoted = False
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promoted = (
                manifest.get("schema_version") == "psm_v0_263_enrollment_promotion_manifest_v1"
                and manifest.get("version") == "PSM_V0.263"
                and manifest.get("promoted") is True
            )
        except (OSError, json.JSONDecodeError):
            promoted = False
    checkpoint = build_enrollment_checkpoint(state, promoted=promoted)
    serialized = json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n"
    if any(
        secret in serialized
        for secret in (
            "invitation_code\"",
            "invitation_sha256",
            "invitee_binding_hmac_sha256",
            "audit_secret_hex",
        )
    ):
        raise EnrollmentError("public enrollment checkpoint contains a private field")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    temporary.write_text(serialized, encoding="utf-8")
    os.replace(temporary, path)


def operator_invitation_cards(state: dict) -> dict:
    return {
        "schema_version": OPERATOR_CARDS_SCHEMA,
        "private_local_operator_view": True,
        "cache_allowed": False,
        "participants": [
            {
                "participant_id": item["participant_id"],
                "invitation_code": item["invitation_code"],
            }
            for item in state.get("participants") or []
        ],
    }


def apply_enrollment_action(
    state: dict,
    *,
    participant_id: str,
    invitation_code: str,
    action: str,
    attestation: str,
    protocol: dict,
    occurred_at: datetime | None = None,
) -> dict:
    if action not in ALLOWED_ACTIONS:
        raise EnrollmentError("enrollment action is not allowed")
    if attestation != ACTION_ATTESTATIONS[action]:
        raise EnrollmentError("required operator or participant attestation is missing")
    if state.get("stopped") and action != "revoke":
        raise EnrollmentError("enrollment is stopped and cannot automatically resume")
    updated = copy.deepcopy(state)
    participant = next(
        (item for item in updated["participants"] if item["participant_id"] == participant_id),
        None,
    )
    if participant is None:
        raise EnrollmentError("pseudonymous participant is not in the selected cohort")
    supplied_hash = hashlib.sha256(str(invitation_code).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, participant["invitation_sha256"]):
        raise EnrollmentError("invitation code is invalid")

    now = (occurred_at or utc_now()).astimezone(timezone.utc)
    if action == "verify_adult":
        _require_step(participant, action)
        participant["adult_confirmed"] = True
        participant["adult_verified_by_operator"] = True
        participant["adult_verification_method"] = "operator_verified_pre_vetted_adult_invitee"
        participant["adult_verified_at"] = _ordered_timestamp(participant, now)
    elif action == "display_notice":
        _require_step(participant, action)
        participant["notice_displayed_at"] = _ordered_timestamp(participant, now)
    elif action == "acknowledge_notice":
        _require_step(participant, action)
        participant["notice_acknowledged"] = True
        participant["notice_acknowledged_at"] = _ordered_timestamp(participant, now)
    elif action == "consent":
        _require_step(participant, action)
        participant["consented_at"] = _ordered_timestamp(participant, now)
    elif action == "enable_session":
        _require_step(participant, action)
        participant["operator_supervision_attested"] = True
        participant["session_enabled_at"] = _ordered_timestamp(participant, now)
        receipt_errors = validate_consent_receipt(build_consent_receipt(participant), protocol)
        if receipt_errors:
            raise EnrollmentError("consent receipt failed closed: " + "; ".join(receipt_errors))
    elif action == "revoke":
        if participant.get("revoked_at"):
            raise EnrollmentError("consent is already revoked")
        participant["revoked_at"] = _ordered_timestamp(participant, now)
        updated["audit_events"] = [
            event
            for event in updated.get("audit_events") or []
            if event.get("participant_id") != participant_id
        ]
        updated["stopped"] = True
        updated["stop_reasons"] = ["participant_withdrawal_or_revoked_consent"]

    _refresh_cohort_state(updated, protocol)
    errors = validate_private_state(updated, protocol)
    if errors:
        raise EnrollmentError("updated enrollment state is invalid: " + "; ".join(errors))
    return updated


def stop_enrollment(state: dict, *, reason: str, protocol: dict) -> dict:
    if reason not in set(protocol.get("stop_conditions") or []):
        raise EnrollmentError("trial stop reason is not in the frozen protocol")
    updated = copy.deepcopy(state)
    updated["stopped"] = True
    updated["trial_active"] = False
    updated["stop_reasons"] = list(dict.fromkeys([*(updated.get("stop_reasons") or []), reason]))
    _refresh_cohort_state(updated, protocol)
    errors = validate_private_state(updated, protocol)
    if errors:
        raise EnrollmentError("stopped enrollment state is invalid: " + "; ".join(errors))
    return updated


def validate_trial_access(
    state: dict,
    *,
    participant_id: str,
    invitation_code: str,
    protocol: dict,
) -> list[str]:
    errors = []
    if state.get("trial_active") is not True or not (state.get("trial_start_gate") or {}).get("passed"):
        errors.append("three-participant cohort gate is not passing")
    if state.get("stopped") is True:
        errors.append("trial is stopped")
    participant = next(
        (item for item in state.get("participants") or [] if item.get("participant_id") == participant_id),
        None,
    )
    if participant is None:
        errors.append("participant is not in the selected cohort")
        return errors
    supplied_hash = hashlib.sha256(str(invitation_code).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, str(participant.get("invitation_sha256") or "")):
        errors.append("invitation code is invalid")
    errors.extend(validate_consent_receipt(build_consent_receipt(participant), protocol))
    return errors


def record_prompt_audit(
    state: dict,
    *,
    participant_id: str,
    prompt: str,
    decision: dict,
    latency_ms: int,
    token_count: int,
    occurred_at: datetime | None = None,
    event_id: str | None = None,
) -> dict:
    updated = copy.deepcopy(state)
    if not any(item.get("participant_id") == participant_id for item in updated.get("participants") or []):
        raise EnrollmentError("audit participant is not in the selected cohort")
    now = (occurred_at or utc_now()).astimezone(timezone.utc)
    event = build_content_free_audit_event(
        event_id=event_id or f"trial-{secrets.token_hex(8)}",
        participant_id=participant_id,
        prompt=prompt,
        decision=decision,
        occurred_at=now.isoformat(),
        audit_secret=bytes.fromhex(updated["audit_secret_hex"]),
        latency_ms=latency_ms,
        token_count=token_count,
    )
    if validate_audit_event(event):
        raise EnrollmentError("content-free audit event is invalid")
    retained, _ = purge_expired_events(
        list(updated.get("audit_events") or []) + [event],
        now=now,
        retention_days=7,
    )
    updated["audit_events"] = retained
    return updated


def write_private_state(path: Path, state: dict, protocol: dict) -> None:
    errors = validate_private_state(state, protocol)
    if errors:
        raise EnrollmentError("refusing to persist invalid private state: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_private_state(path: Path, protocol: dict) -> dict:
    state = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_private_state(state, protocol)
    if errors:
        raise EnrollmentError("private enrollment state is invalid: " + "; ".join(errors))
    return state


def _require_step(participant: dict, expected: str) -> None:
    actual = current_step(participant)
    if actual != expected:
        raise EnrollmentError(f"enrollment action is out of order: expected {actual}")


def _ordered_timestamp(participant: dict, now: datetime) -> str:
    existing = [
        participant.get(field)
        for field in (
            "adult_verified_at",
            "notice_displayed_at",
            "notice_acknowledged_at",
            "consented_at",
            "session_enabled_at",
            "revoked_at",
        )
        if participant.get(field)
    ]
    if existing:
        latest = max(datetime.fromisoformat(value.replace("Z", "+00:00")) for value in existing)
        if now <= latest:
            now = latest + timedelta(microseconds=1)
    return now.astimezone(timezone.utc).isoformat()


def _refresh_cohort_state(state: dict, protocol: dict) -> None:
    receipts = [
        build_consent_receipt(item)
        for item in state["participants"]
        if item.get("session_enabled_at")
    ]
    gate = trial_start_gate(receipts, protocol)
    if len(receipts) != state["participant_count"]:
        gate["passed"] = False
        missing = state["participant_count"] - len(receipts)
        gate["errors"] = list(gate.get("errors") or []) + [f"{missing} selected participants are not session-enabled"]
    state["trial_start_gate"] = gate
    if state.get("stopped"):
        state["trial_active"] = False
        state["status"] = "stopped_requires_operator_review"
    elif gate["passed"]:
        state["trial_active"] = True
        state["status"] = "supervised_trial_active"
    else:
        state["trial_active"] = False
        steps = {current_step(item) for item in state["participants"]}
        state["status"] = (
            "awaiting_operator_adult_verification"
            if steps == {"verify_adult"}
            else "three_participant_enrollment_in_progress"
        )
