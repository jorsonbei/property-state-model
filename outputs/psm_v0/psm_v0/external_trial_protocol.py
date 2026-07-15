from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


PROTOCOL_SCHEMA = "psm_invite_only_external_trial_protocol_v1"
CONSENT_SCHEMA = "psm_v0_262_consent_receipt_v1"
AUDIT_SCHEMA = "psm_v0_262_content_free_audit_event_v1"
BUDGET_SCHEMA = "psm_v0_262_api_budget_reservation_v1"
PARTICIPANT_ID_PATTERN = re.compile(r"^P(?:0[1-9]|[1-9][0-9])$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

DIRECT_IDENTIFIER_PATTERNS = (
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?:密码|密碼|password|passwd|api[ _-]?key|secret|token)\s*[:=]", re.IGNORECASE),
)
PROHIBITED_DOMAIN_PATTERNS = {
    "medical_decision": re.compile(r"诊断|診斷|病历|病歷|处方|處方|药量|藥量|停药|停藥|medical record|diagnos|dosage", re.IGNORECASE),
    "legal_decision": re.compile(r"我的案件|起诉|起訴|应诉|應訴|法院传票|法院傳票|律师|律師|legal case|lawsuit", re.IGNORECASE),
    "trading_decision": re.compile(r"买入|買入|卖出|賣出|下单|下單|券商账户|券商賬戶|brokerage account|which stock|trade now", re.IGNORECASE),
    "private_document_processing": re.compile(r"私人文件|未公开|未公開|保密文档|保密文檔|unpublished manuscript|private document", re.IGNORECASE),
    "minor_data": re.compile(r"我(?:今年)?(?:1[0-7]|[0-9])岁|我(?:今年)?(?:1[0-7]|[0-9])歲|I am (?:1[0-7]|[0-9]) years old", re.IGNORECASE),
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_protocol(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def validate_protocol(protocol: dict) -> list[str]:
    errors: list[str] = []
    if protocol.get("schema_version") != PROTOCOL_SCHEMA or protocol.get("status") != "frozen":
        errors.append("protocol schema or frozen status is invalid")
    authorization = protocol.get("authorization") or {}
    if authorization.get("approved_by_user") is not True or authorization.get("approved_plan") != "v0_262_conservative_invite_only":
        errors.append("conservative protocol is not explicitly authorized")
    scope = protocol.get("trial_scope") or {}
    if scope.get("participant_minimum") != 3 or scope.get("participant_maximum") != 5:
        errors.append("participant range must be exactly 3-5")
    if any(scope.get(name) is not False for name in ("automated_recruitment", "public_signup", "anonymous_public_access")):
        errors.append("public or automated participant access is open")
    if scope.get("adult_only") is not True or scope.get("operator_present_required") is not True:
        errors.append("adult or operator-supervision boundary is missing")
    if scope.get("pre_vetted_adult_invite_list_required") is not True or scope.get("self_asserted_adulthood_sufficient") is not False:
        errors.append("operator-vetted adult invite binding is missing")
    deployment = protocol.get("deployment") or {}
    if deployment.get("host_bind") != "127.0.0.1" or deployment.get("public_internet_exposure") is not False:
        errors.append("deployment is not local-only")
    data_policy = protocol.get("data_policy") or {}
    if data_policy.get("raw_prompt_server_persistence") is not False:
        errors.append("raw prompt persistence is enabled")
    if data_policy.get("participant_content_external_api_submission") is not False:
        errors.append("participant content external submission is enabled")
    if data_policy.get("unknown_data_class") != "reject":
        errors.append("unknown data classes do not fail closed")
    consent = protocol.get("consent") or {}
    if any(consent.get(name) is not True for name in ("notice_must_be_displayed_before_acknowledgment", "explicit_opt_in_before_first_message", "adult_confirmation_required", "adult_verification_by_operator_required", "invitee_binding_hmac_required", "session_enablement_requires_all_prior_steps", "withdrawal_available_at_any_time", "withdrawal_triggers_deletion")):
        errors.append("consent or withdrawal boundary is incomplete")
    retention = protocol.get("retention") or {}
    if retention.get("raw_prompt_days") != 0 or retention.get("operational_metadata_days") != 7:
        errors.append("retention is not zero-day raw and seven-day metadata")
    if retention.get("deletion_failure_stops_trial") is not True:
        errors.append("deletion failure does not stop the trial")
    budget = protocol.get("api_budget") or {}
    if Decimal(str(budget.get("calendar_month_limit"))) != Decimal("20.0"):
        errors.append("monthly API budget is not 20 USD")
    if budget.get("participant_content_calls_allowed") is not False or budget.get("unknown_cost_or_purpose") != "reject":
        errors.append("API purpose or participant-content budget boundary is open")
    boundary = protocol.get("release_boundary") or {}
    prohibited_true = (
        "participant_enrollment_completed",
        "public_service_allowed",
        "privacy_compliance_claimed",
        "production_readiness_claimed",
        "medical_legal_trading_authority",
        "training_on_trial_data_allowed",
        "rule_replacement_allowed",
        "external_release_authority",
    )
    if any(boundary.get(name) is not False for name in prohibited_true):
        errors.append("protocol opens a prohibited release authority")
    return errors


def validate_consent_receipt(receipt: dict, protocol: dict) -> list[str]:
    errors: list[str] = []
    allowed = {
        "schema_version", "participant_id", "invitation_sha256", "invitee_binding_hmac_sha256",
        "adult_confirmed", "adult_verified_by_operator", "adult_verification_method",
        "adult_verified_at", "notice_version", "notice_displayed_at", "notice_acknowledged",
        "notice_acknowledged_at", "consented_at", "session_enabled_at",
        "operator_supervision_attested", "revoked_at",
    }
    if set(receipt) != allowed:
        errors.append("consent receipt fields are not closed")
    if receipt.get("schema_version") != CONSENT_SCHEMA:
        errors.append("consent receipt schema is invalid")
    if not PARTICIPANT_ID_PATTERN.fullmatch(str(receipt.get("participant_id") or "")):
        errors.append("participant ID is not pseudonymous PNN format")
    if not SHA256_PATTERN.fullmatch(str(receipt.get("invitation_sha256") or "")):
        errors.append("invitation hash is invalid")
    if not SHA256_PATTERN.fullmatch(str(receipt.get("invitee_binding_hmac_sha256") or "")):
        errors.append("invitee binding HMAC is invalid")
    if receipt.get("adult_confirmed") is not True or receipt.get("adult_verified_by_operator") is not True:
        errors.append("adult status is not confirmed and operator verified")
    if receipt.get("adult_verification_method") != "operator_verified_pre_vetted_adult_invitee":
        errors.append("adult verification method is not allowed")
    if receipt.get("operator_supervision_attested") is not True:
        errors.append("operator supervision is not attested")
    consent = protocol["consent"]
    if receipt.get("notice_version") != consent["notice_version"] or receipt.get("notice_acknowledged") is not True:
        errors.append("notice was not explicitly acknowledged")
    timestamp_fields = (
        "adult_verified_at", "notice_displayed_at", "notice_acknowledged_at",
        "consented_at", "session_enabled_at",
    )
    parsed_timestamps = {}
    for field in timestamp_fields:
        try:
            parsed_timestamps[field] = parse_timestamp(str(receipt.get(field) or ""))
        except (TypeError, ValueError):
            errors.append(f"{field} is invalid")
    if len(parsed_timestamps) == len(timestamp_fields):
        sequence = [parsed_timestamps[field] for field in timestamp_fields]
        if sequence != sorted(sequence) or len(set(sequence)) != len(sequence):
            errors.append("adult verification, notice, consent, and session enablement are not strictly ordered")
    revoked_at = receipt.get("revoked_at")
    if revoked_at is not None:
        try:
            parse_timestamp(str(revoked_at))
        except (TypeError, ValueError):
            errors.append("revocation timestamp is invalid")
        errors.append("consent has been revoked")
    return errors


def active_participant_ids(receipts: list[dict], protocol: dict) -> set[str]:
    valid = set()
    for receipt in receipts:
        if not validate_consent_receipt(receipt, protocol):
            valid.add(receipt["participant_id"])
    return valid


def trial_start_gate(receipts: list[dict], protocol: dict) -> dict:
    participant_ids = active_participant_ids(receipts, protocol)
    scope = protocol["trial_scope"]
    errors = []
    if len(participant_ids) < scope["participant_minimum"]:
        errors.append("fewer than three active consented participants")
    if len(participant_ids) > scope["participant_maximum"]:
        errors.append("more than five active consented participants")
    if len(participant_ids) != len(receipts):
        errors.append("one or more consent receipts are invalid, revoked, or duplicated")
    bindings = [receipt.get("invitee_binding_hmac_sha256") for receipt in receipts]
    if len(set(bindings)) != len(bindings):
        errors.append("invitee bindings are not one-to-one")
    return {"passed": not errors, "active_participants": len(participant_ids), "errors": errors}


def inspect_prompt(prompt: str, protocol: dict) -> dict:
    reasons: list[str] = []
    categories: list[str] = []
    if not isinstance(prompt, str) or not prompt.strip():
        return {"allowed": False, "categories": ["empty_or_invalid"], "reasons": ["prompt must be non-empty text"]}
    if any(pattern.search(prompt) for pattern in DIRECT_IDENTIFIER_PATTERNS):
        categories.append("direct_identifiers")
        reasons.append("possible direct identifier or contact detail detected")
    if any(pattern.search(prompt) for pattern in SECRET_PATTERNS):
        categories.append("credentials_or_secrets")
        reasons.append("possible credential or secret detected")
    for category, pattern in PROHIBITED_DOMAIN_PATTERNS.items():
        if pattern.search(prompt):
            categories.append(category)
            reasons.append(f"prohibited trial domain detected: {category}")
    categories = sorted(set(categories))
    return {"allowed": not categories, "categories": categories or ["low_risk_general"], "reasons": reasons}


def build_content_free_audit_event(
    *,
    event_id: str,
    participant_id: str,
    prompt: str,
    decision: dict,
    occurred_at: str,
    audit_secret: bytes,
    latency_ms: int,
    token_count: int,
) -> dict:
    if not audit_secret:
        raise ValueError("audit secret is required")
    prompt_hmac = hmac.new(audit_secret, prompt.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "schema_version": AUDIT_SCHEMA,
        "event_id": event_id,
        "participant_id": participant_id,
        "occurred_at": occurred_at,
        "prompt_hmac_sha256": prompt_hmac,
        "allowed": decision["allowed"],
        "categories": list(decision["categories"]),
        "latency_ms": latency_ms,
        "token_count": token_count,
        "raw_prompt_persisted": False,
        "participant_content_sent_to_external_api": False,
    }


def validate_audit_event(event: dict) -> list[str]:
    expected = {
        "schema_version", "event_id", "participant_id", "occurred_at", "prompt_hmac_sha256",
        "allowed", "categories", "latency_ms", "token_count", "raw_prompt_persisted",
        "participant_content_sent_to_external_api",
    }
    errors = []
    if set(event) != expected:
        errors.append("audit event schema is not closed")
    if event.get("schema_version") != AUDIT_SCHEMA:
        errors.append("audit event schema is invalid")
    if not SHA256_PATTERN.fullmatch(str(event.get("prompt_hmac_sha256") or "")):
        errors.append("prompt HMAC is invalid")
    if event.get("raw_prompt_persisted") is not False or event.get("participant_content_sent_to_external_api") is not False:
        errors.append("audit event opens content persistence or external submission")
    if any(key in event for key in ("prompt", "messages", "content", "response")):
        errors.append("audit event contains raw content")
    try:
        parse_timestamp(str(event.get("occurred_at") or ""))
    except (TypeError, ValueError):
        errors.append("audit timestamp is invalid")
    return errors


def purge_expired_events(events: list[dict], *, now: datetime, retention_days: int = 7) -> tuple[list[dict], list[dict]]:
    cutoff = now.astimezone(timezone.utc) - timedelta(days=retention_days)
    retained = []
    tombstones = []
    for event in events:
        occurred_at = parse_timestamp(event["occurred_at"])
        if occurred_at < cutoff:
            tombstones.append(
                {
                    "event_id": event["event_id"],
                    "deleted_at": now.astimezone(timezone.utc).isoformat(),
                    "reason": "retention_expired",
                    "content_retained": False,
                }
            )
        else:
            retained.append(event)
    return retained, tombstones


def reserve_api_budget(
    reservations: list[dict],
    *,
    reservation_id: str,
    occurred_at: str,
    purpose: str,
    reserved_cost_usd: Decimal,
    contains_participant_content: bool,
    protocol: dict,
) -> tuple[bool, dict | None, str | None]:
    allowed_purposes = set(protocol["api_budget"]["allowed_external_api_purposes"])
    if purpose not in allowed_purposes:
        return False, None, "external API purpose is not allowed"
    if contains_participant_content:
        return False, None, "participant content cannot be sent to an external API"
    if reserved_cost_usd <= 0:
        return False, None, "reserved cost must be positive and known"
    month = parse_timestamp(occurred_at).strftime("%Y-%m")
    used = sum(
        Decimal(str(item["reserved_cost_usd"]))
        for item in reservations
        if parse_timestamp(item["occurred_at"]).strftime("%Y-%m") == month
    )
    limit = Decimal(str(protocol["api_budget"]["calendar_month_limit"]))
    if used + reserved_cost_usd > limit:
        return False, None, "monthly API budget would be exceeded"
    reservation = {
        "schema_version": BUDGET_SCHEMA,
        "reservation_id": reservation_id,
        "occurred_at": occurred_at,
        "purpose": purpose,
        "reserved_cost_usd": str(reserved_cost_usd.quantize(Decimal("0.01"))),
        "contains_participant_content": False,
    }
    return True, reservation, None


def stop_gate(*, consent_errors: list[str], prompt_decision: dict, budget_allowed: bool, incident_open: bool, deletion_failed: bool) -> dict:
    reasons = []
    if consent_errors:
        reasons.append("missing_invalid_or_revoked_consent")
    if not prompt_decision.get("allowed"):
        reasons.append("prohibited_or_unknown_data_detected")
    if not budget_allowed:
        reasons.append("monthly_api_budget_would_be_exceeded")
    if incident_open:
        reasons.append("unresolved_security_or_privacy_incident")
    if deletion_failed:
        reasons.append("retention_or_deletion_failure")
    return {"stop_required": bool(reasons), "reasons": reasons, "automatic_resume_allowed": False}
