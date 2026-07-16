#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from psm_v0.openai_external_long_context_judge import (
    APPROVED_AUTHORIZATION,
    canonical_sha256,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
PREPARED_PACKAGE = RUNTIME / "v0_273_external_long_context_review_package.json"
PREPARED_GATE = RUNTIME / "v0_273_external_long_context_package_gate.json"
AUTHORIZED_PACKAGE = RUNTIME / "v0_273_external_long_context_authorized_review_package.json"
AUTHORIZATION_GATE = RUNTIME / "v0_273_external_long_context_authorization_gate.json"
BUDGET_LEDGER = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_273_external_long_context_checkpoint.json"

BASE_LIMIT_USD = 20.0
PRIOR_EXTENSIONS_USD = 4.0
ADDITIONAL_AUTHORIZATION_USD = 4.0
EFFECTIVE_LIMIT_USD = BASE_LIMIT_USD + PRIOR_EXTENSIONS_USD + ADDITIONAL_AUTHORIZATION_USD
RESERVATION_ID = "V0_273_EXTERNAL_LONG_CONTEXT_REVIEW_ATTEMPT_1"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    prepared = read(PREPARED_PACKAGE)
    prepared_gate = read(PREPARED_GATE)
    ledger = read(BUDGET_LEDGER)
    checkpoint = read(CHECKPOINT)

    validate_review_package(prepared, require_authorization=False)
    prior_budget_closed = (
        float(ledger.get("limit_usd", 0)) == 24.0
        and float(ledger.get("reserved_usd", 0)) == 24.0
        and ledger.get("participant_content_calls") == 0
    )
    prior_checkpoint_blocked = (
        checkpoint.get("status") == "blocked_external_long_context_judge_monthly_api_budget_exhausted"
        and checkpoint.get("requires_user_input") is True
        and checkpoint.get("target_promoted") is False
    )

    package = copy.deepcopy(prepared)
    package.update({
        "authorization": APPROVED_AUTHORIZATION,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_scope": "one_synthetic_long_context_semantic_review_only",
        "source_prepared_package": "runtime/v0_273_external_long_context_review_package.json",
    })
    package["budget"] = {
        "currency": "USD",
        "maximum_api_calls": 1,
        "reserved_usd": ADDITIONAL_AUTHORIZATION_USD,
        "reserved_total_month_usd": EFFECTIVE_LIMIT_USD,
        "monthly_limit_usd": EFFECTIVE_LIMIT_USD,
        "base_monthly_limit_usd": BASE_LIMIT_USD,
        "prior_user_approved_extensions_usd": PRIOR_EXTENSIONS_USD,
        "user_approved_additional_usd": ADDITIONAL_AUTHORIZATION_USD,
        "authorization_scope": "synthetic_long_context_review_only",
    }
    validate_review_package(package, require_authorization=True)

    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [
        token
        for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers")
        if token in serialized
    ]
    checks = {
        "prepared_package_gate_passed": prepared_gate.get("passed") is True,
        "prepared_payload_hash_retained": package["review_payload_sha256"] == prepared["review_payload_sha256"],
        "prior_budget_closed": prior_budget_closed,
        "prior_checkpoint_blocked": prior_checkpoint_blocked,
        "single_external_call_authorized": package["budget"]["maximum_api_calls"] == 1,
        "additional_budget_exactly_four_usd": package["budget"]["user_approved_additional_usd"] == 4.0,
        "effective_limit_exactly_twenty_eight_usd": package["budget"]["monthly_limit_usd"] == 28.0,
        "participant_content_calls_zero": ledger.get("participant_content_calls") == 0,
        "privacy_boundary_closed": package["privacy"].get("synthetic_only") is True
        and all(value is False for key, value in package["privacy"].items() if key != "synthetic_only"),
        "release_boundary_closed": not any(package["release_boundary"].values()),
        "prohibited_material_absent": not prohibited,
    }
    gate = {
        "schema_version": "psm_v0_273_external_long_context_authorization_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "authorization": APPROVED_AUTHORIZATION,
        "authorization_scope": "one_synthetic_long_context_semantic_review_only",
        "review_payload_sha256": package["review_payload_sha256"],
        "authorized_package_sha256": canonical_sha256(package),
        "prohibited_material_found": prohibited,
    }
    if not gate["passed"]:
        write(AUTHORIZATION_GATE, gate)
        raise SystemExit(f"V0.273 authorization failed: {[key for key, value in checks.items() if not value]}")

    reservations = ledger.setdefault("reservations", [])
    existing = [item for item in reservations if item.get("reservation_id") == RESERVATION_ID]
    if existing and (
        len(existing) != 1
        or existing[0].get("reserved_cost_usd") != "4.00"
        or existing[0].get("contains_participant_content") is not False
    ):
        raise SystemExit("V0.273 reservation conflicts with the approved scope.")
    if not existing:
        reservations.append({
            "schema_version": "psm_v0_262_api_budget_reservation_v1",
            "reservation_id": RESERVATION_ID,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "synthetic_long_context_semantic_review",
            "reserved_cost_usd": "4.00",
            "contains_participant_content": False,
            "authorization_scope": "user_approved_v0_273_review_only",
        })
    ledger.update({
        "base_limit_usd": "20.00",
        "user_approved_rejudge_extension_usd": "4.00",
        "user_approved_v0_273_extension_usd": "4.00",
        "limit_usd": "28.00",
        "reserved_usd": "28.00",
        "participant_content_calls": 0,
    })
    checkpoint.update({
        "status": "external_long_context_package_passed_single_call_authorized",
        "requires_user_input": False,
        "next_action": "run_authorized_openai_long_context_semantic_judge",
        "reserved_month_usd": EFFECTIVE_LIMIT_USD,
        "monthly_limit_usd": EFFECTIVE_LIMIT_USD,
        "base_monthly_limit_usd": BASE_LIMIT_USD,
        "user_approved_additional_usd": ADDITIONAL_AUTHORIZATION_USD,
        "participant_content_calls": 0,
        "authorization_scope": "synthetic_long_context_review_only",
        "required_decision": "额外 4 美元合成长对话独立评审预算已获批准。",
        "authorized_review_package": "runtime/v0_273_external_long_context_authorized_review_package.json",
        "authorization_gate": "runtime/v0_273_external_long_context_authorization_gate.json",
    })

    write(AUTHORIZED_PACKAGE, package)
    write(AUTHORIZATION_GATE, gate)
    write(BUDGET_LEDGER, ledger)
    write(CHECKPOINT, checkpoint)
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print(f"authorized_package_sha256: {gate['authorized_package_sha256']}")
    print("external_calls_authorized: 1")
    print("additional_budget_usd: 4.00")
    print("reserved_month_usd: 28.00")
    print("participant_content_calls: 0")


if __name__ == "__main__":
    main()
