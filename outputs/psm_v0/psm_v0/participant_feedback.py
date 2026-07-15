from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path


FEEDBACK_STATE_SCHEMA = "psm_v0_265_private_feedback_state_v1"
FEEDBACK_EVENT_SCHEMA = "psm_v0_265_content_free_feedback_event_v1"
PUBLIC_PROGRESS_SCHEMA = "psm_v0_265_feedback_progress_v1"
FEEDBACK_ELIGIBLE_NOT_BEFORE = "2026-07-15T10:31:00+00:00"
STATE_FIELDS = {
    "schema_version",
    "stage_version",
    "private_only",
    "retention_days",
    "eligible_not_before",
    "feedback_events",
}
EVENT_FIELDS = {
    "schema_version",
    "feedback_id",
    "participant_id",
    "trial_event_hmac_sha256",
    "submitted_at",
    "helpfulness",
    "clarity",
    "state_alignment",
    "issue_category",
    "free_text_collected",
    "raw_prompt_persisted",
    "raw_answer_persisted",
    "participant_content_sent_to_external_api",
}
STATE_ALIGNMENTS = {"yes", "partial", "no"}
ISSUE_CATEGORIES = {
    "none",
    "missed_intent",
    "possible_factual_error",
    "unclear",
    "too_verbose",
    "too_guarded",
    "unsafe_or_inappropriate",
}
SEVERE_ISSUES = {"possible_factual_error", "unsafe_or_inappropriate"}


class FeedbackError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def initialize_feedback_state() -> dict:
    return {
        "schema_version": FEEDBACK_STATE_SCHEMA,
        "stage_version": "PSM_V0.265",
        "private_only": True,
        "retention_days": 7,
        "eligible_not_before": FEEDBACK_ELIGIBLE_NOT_BEFORE,
        "feedback_events": [],
    }


def feedback_token_for_event(enrollment_state: dict, event_id: str) -> str:
    secret = bytes.fromhex(str(enrollment_state.get("audit_secret_hex") or ""))
    return hmac.new(secret, f"v0.265-feedback:{event_id}".encode(), hashlib.sha256).hexdigest()


def validate_feedback_state(state: dict) -> list[str]:
    errors = []
    if set(state) != STATE_FIELDS:
        errors.append("feedback state fields are not closed")
    if state.get("schema_version") != FEEDBACK_STATE_SCHEMA or state.get("stage_version") != "PSM_V0.265":
        errors.append("feedback state schema or stage is invalid")
    if state.get("private_only") is not True or state.get("retention_days") != 7:
        errors.append("feedback privacy or retention boundary is invalid")
    if state.get("eligible_not_before") != FEEDBACK_ELIGIBLE_NOT_BEFORE:
        errors.append("feedback eligible-turn boundary is invalid")
    tokens = []
    for event in state.get("feedback_events") or []:
        if not isinstance(event, dict) or set(event) != EVENT_FIELDS:
            errors.append("feedback event fields are not closed")
            continue
        tokens.append(event.get("trial_event_hmac_sha256"))
        if event.get("schema_version") != FEEDBACK_EVENT_SCHEMA:
            errors.append("feedback event schema is invalid")
        if event.get("participant_id") not in {"P01", "P02", "P03"}:
            errors.append("feedback participant is outside the frozen cohort")
        if not isinstance(event.get("helpfulness"), int) or event["helpfulness"] not in range(1, 6):
            errors.append("feedback helpfulness is invalid")
        if not isinstance(event.get("clarity"), int) or event["clarity"] not in range(1, 6):
            errors.append("feedback clarity is invalid")
        if event.get("state_alignment") not in STATE_ALIGNMENTS:
            errors.append("feedback state alignment is invalid")
        if event.get("issue_category") not in ISSUE_CATEGORIES:
            errors.append("feedback issue category is invalid")
        if any(
            event.get(key) is not False
            for key in (
                "free_text_collected",
                "raw_prompt_persisted",
                "raw_answer_persisted",
                "participant_content_sent_to_external_api",
            )
        ):
            errors.append("feedback event contains a prohibited content flag")
        try:
            datetime.fromisoformat(str(event.get("submitted_at") or "").replace("Z", "+00:00"))
        except ValueError:
            errors.append("feedback timestamp is invalid")
        token = str(event.get("trial_event_hmac_sha256") or "")
        if len(token) != 64 or any(character not in "0123456789abcdef" for character in token):
            errors.append("feedback event token is invalid")
    if len(tokens) != len(set(tokens)):
        errors.append("a trial event has more than one feedback record")
    return errors


def submit_feedback(
    feedback_state: dict,
    *,
    enrollment_state: dict,
    participant_id: str,
    feedback_token: str,
    helpfulness: int,
    clarity: int,
    state_alignment: str,
    issue_category: str,
    submitted_at: datetime | None = None,
) -> dict:
    if (
        not isinstance(helpfulness, int)
        or isinstance(helpfulness, bool)
        or helpfulness not in range(1, 6)
        or not isinstance(clarity, int)
        or isinstance(clarity, bool)
        or clarity not in range(1, 6)
    ):
        raise FeedbackError("feedback scores must be integers from one to five")
    if state_alignment not in STATE_ALIGNMENTS:
        raise FeedbackError("feedback state alignment is not allowed")
    if issue_category not in ISSUE_CATEGORIES:
        raise FeedbackError("feedback issue category is not allowed")
    eligible_not_before = datetime.fromisoformat(FEEDBACK_ELIGIBLE_NOT_BEFORE)
    eligible = [
        event
        for event in enrollment_state.get("audit_events") or []
        if event.get("participant_id") == participant_id
        and event.get("allowed") is True
        and event.get("categories") == ["low_risk_general"]
        and datetime.fromisoformat(str(event.get("occurred_at") or "").replace("Z", "+00:00"))
        >= eligible_not_before
    ]
    matched = next(
        (
            event
            for event in eligible
            if hmac.compare_digest(
                feedback_token_for_event(enrollment_state, str(event.get("event_id") or "")),
                str(feedback_token),
            )
        ),
        None,
    )
    if matched is None:
        raise FeedbackError("feedback token is not bound to an eligible participant turn")
    updated = purge_expired_feedback(feedback_state, now=submitted_at)
    if any(
        hmac.compare_digest(str(item.get("trial_event_hmac_sha256") or ""), str(feedback_token))
        for item in updated.get("feedback_events") or []
    ):
        raise FeedbackError("feedback has already been submitted for this turn")
    now = (submitted_at or utc_now()).astimezone(timezone.utc)
    updated["feedback_events"].append({
        "schema_version": FEEDBACK_EVENT_SCHEMA,
        "feedback_id": f"feedback-{secrets.token_hex(8)}",
        "participant_id": participant_id,
        "trial_event_hmac_sha256": feedback_token,
        "submitted_at": now.isoformat(),
        "helpfulness": helpfulness,
        "clarity": clarity,
        "state_alignment": state_alignment,
        "issue_category": issue_category,
        "free_text_collected": False,
        "raw_prompt_persisted": False,
        "raw_answer_persisted": False,
        "participant_content_sent_to_external_api": False,
    })
    errors = validate_feedback_state(updated)
    if errors:
        raise FeedbackError("feedback state failed closed: " + "; ".join(errors))
    return updated


def purge_expired_feedback(state: dict, *, now: datetime | None = None) -> dict:
    current = (now or utc_now()).astimezone(timezone.utc)
    cutoff = current - timedelta(days=int(state.get("retention_days") or 7))
    updated = {**state, "feedback_events": []}
    for event in state.get("feedback_events") or []:
        submitted = datetime.fromisoformat(event["submitted_at"].replace("Z", "+00:00"))
        if submitted >= cutoff:
            updated["feedback_events"].append(event)
    return updated


def delete_participant_feedback(state: dict, participant_id: str) -> dict:
    return {
        **state,
        "feedback_events": [
            event for event in state.get("feedback_events") or [] if event.get("participant_id") != participant_id
        ],
    }


def public_feedback_progress(state: dict, *, required_per_participant: int = 3) -> dict:
    events = state.get("feedback_events") or []
    participants = []
    for participant_id in ("P01", "P02", "P03"):
        rows = [event for event in events if event.get("participant_id") == participant_id]
        participants.append({
            "participant_id": participant_id,
            "submitted": len(rows),
            "credited": min(len(rows), required_per_participant),
            "required": required_per_participant,
            "complete": len(rows) >= required_per_participant,
        })
    complete = sum(item["complete"] for item in participants)
    return {
        "schema_version": PUBLIC_PROGRESS_SCHEMA,
        "required_feedback_per_participant": required_per_participant,
        "completed_participants": complete,
        "participant_count": 3,
        "total_feedback_events": len(events),
        "coverage_gate_passed": complete == 3,
        "participants": participants,
        "release_boundary": {
            "public_service_allowed": False,
            "training_on_feedback_allowed": False,
            "external_release_authority": False,
        },
    }


def write_feedback_state(path: Path, state: dict) -> None:
    errors = validate_feedback_state(state)
    if errors:
        raise FeedbackError("refusing to persist invalid feedback state: " + "; ".join(errors))
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


def load_feedback_state(path: Path) -> dict:
    if not path.exists():
        return initialize_feedback_state()
    stored = json.loads(path.read_text(encoding="utf-8"))
    state = purge_expired_feedback(stored)
    errors = validate_feedback_state(state)
    if errors:
        raise FeedbackError("private feedback state is invalid: " + "; ".join(errors))
    if len(state["feedback_events"]) != len(stored.get("feedback_events") or []):
        write_feedback_state(path, state)
    return state
