#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from psm_v0.openai_external_open_context_judge import (
    APPROVED_REJUDGE_AUTHORIZATION,
    canonical_sha256,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
ORIGINAL_JUDGE = RUNTIME / "v0_275_openai_external_open_context_judge.json"
REPAIR_REPORT = RUNTIME / "v0_275_external_open_context_repair_report.json"
REPAIR_GATE = RUNTIME / "v0_275_external_open_context_repair_gate.json"
REPAIRED_CANDIDATE = RUNTIME / "v0_275_external_open_context_repaired_candidate.json"
BUDGET_LEDGER = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_275_external_open_context_checkpoint.json"
REJUDGE_PACKAGE = RUNTIME / "v0_275_external_open_context_rejudge_package.json"
REJUDGE_GATE = RUNTIME / "v0_275_external_open_context_rejudge_package_gate.json"

BASE_LIMIT_USD = 20.0
PRIOR_EXTENSIONS_USD = 12.0
ADDITIONAL_AUTHORIZATION_USD = 4.0
EFFECTIVE_LIMIT_USD = BASE_LIMIT_USD + PRIOR_EXTENSIONS_USD + ADDITIONAL_AUTHORIZATION_USD
RESERVATION_ID = "V0_275_EXTERNAL_OPEN_CONTEXT_REVIEW_ATTEMPT_2"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    original_judge = read(ORIGINAL_JUDGE)
    repair_report = read(REPAIR_REPORT)
    repair_gate = read(REPAIR_GATE)
    repaired = read(REPAIRED_CANDIDATE)
    ledger = read(BUDGET_LEDGER)
    checkpoint = read(CHECKPOINT)

    package = copy.deepcopy(repaired)
    package.update({
        "schema_version": "psm_v0_275_external_open_context_review_package_v1",
        "version": "PSM_V0.275-rejudge-candidate",
        "authorization": APPROVED_REJUDGE_AUTHORIZATION,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_scope": "one_synthetic_open_context_semantic_rejudge_only",
        "source_failed_judge": "runtime/v0_275_openai_external_open_context_judge.json",
        "source_repair_report": "runtime/v0_275_external_open_context_repair_report.json",
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
        "authorization_scope": "synthetic_open_context_rejudge_only",
    }
    package.pop("source_failed_external_judge", None)
    package.pop("source_original_package", None)
    package.pop("source_local_report", None)
    validate_review_package(package, require_authorization=True)

    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [
        token
        for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers")
        if token in serialized
    ]
    checks = {
        "original_external_failure_retained": (
            original_judge.get("passed") is False
            and original_judge.get("review", {}).get("failed_item_ids") == ["O01", "O02", "O10"]
        ),
        "local_repair_report_passed": (
            repair_report.get("passed") is True
            and repair_report.get("failed_items_repaired_locally") == ["O01", "O02", "O10"]
            and repair_report.get("external_rejudge_completed") is False
        ),
        "local_repair_gate_passed": repair_gate.get("passed") is True and all(repair_gate.get("checks", {}).values()),
        "repaired_payload_hash_retained": package["review_payload_sha256"] == repaired["review_payload_sha256"],
        "only_failed_items_changed": repaired.get("changed_item_ids") == ["O01", "O02", "O10"],
        "prior_budget_closed": float(ledger.get("limit_usd", 0)) == float(ledger.get("reserved_usd", 0)) == 32.0,
        "prior_checkpoint_blocked": (
            checkpoint.get("status") == "blocked_external_open_context_rejudge_monthly_api_budget_exhausted"
            and checkpoint.get("requires_user_input") is True
            and checkpoint.get("target_promoted") is False
        ),
        "single_rejudge_call_authorized": package["budget"]["maximum_api_calls"] == 1,
        "additional_budget_exactly_four_usd": package["budget"]["user_approved_additional_usd"] == 4.0,
        "effective_limit_exactly_thirty_six_usd": package["budget"]["monthly_limit_usd"] == 36.0,
        "participant_content_calls_zero": ledger.get("participant_content_calls") == 0,
        "privacy_boundary_closed": package["privacy"].get("synthetic_only") is True
        and all(value is False for key, value in package["privacy"].items() if key != "synthetic_only"),
        "release_boundary_closed": not any(package["release_boundary"].values()),
        "prohibited_material_absent": not prohibited,
    }
    gate = {
        "schema_version": "psm_v0_275_external_open_context_rejudge_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "authorization": APPROVED_REJUDGE_AUTHORIZATION,
        "authorization_scope": "one_synthetic_open_context_semantic_rejudge_only",
        "review_payload_sha256": package["review_payload_sha256"],
        "authorized_package_sha256": canonical_sha256(package),
        "prohibited_material_found": prohibited,
    }
    if not gate["passed"]:
        write(REJUDGE_GATE, gate)
        raise SystemExit(f"V0.275 rejudge authorization failed: {[key for key, value in checks.items() if not value]}")

    reservations = ledger.setdefault("reservations", [])
    existing = [item for item in reservations if item.get("reservation_id") == RESERVATION_ID]
    if existing and (
        len(existing) != 1
        or existing[0].get("reserved_cost_usd") != "4.00"
        or existing[0].get("contains_participant_content") is not False
    ):
        raise SystemExit("V0.275 rejudge reservation conflicts with the approved scope.")
    if not existing:
        reservations.append({
            "schema_version": "psm_v0_262_api_budget_reservation_v1",
            "reservation_id": RESERVATION_ID,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "synthetic_open_context_semantic_rejudge",
            "reserved_cost_usd": "4.00",
            "contains_participant_content": False,
            "authorization_scope": "user_approved_v0_275_rejudge_only",
        })
    ledger.update({
        "base_limit_usd": "20.00",
        "user_approved_v0_275_rejudge_extension_usd": "4.00",
        "limit_usd": "36.00",
        "reserved_usd": "36.00",
        "participant_content_calls": 0,
    })
    checkpoint.update({
        "status": "external_open_context_rejudge_package_passed_single_call_authorized",
        "requires_user_input": False,
        "next_action": "run_authorized_openai_open_context_semantic_rejudge",
        "review_payload_sha256": package["review_payload_sha256"],
        "reserved_month_usd": EFFECTIVE_LIMIT_USD,
        "monthly_limit_usd": EFFECTIVE_LIMIT_USD,
        "base_monthly_limit_usd": BASE_LIMIT_USD,
        "user_approved_additional_usd": ADDITIONAL_AUTHORIZATION_USD,
        "authorization_scope": "synthetic_open_context_rejudge_only",
        "required_decision": "额外 4 美元合成开放式长对话重审预算已获批准。",
        "rejudge_package": str(REJUDGE_PACKAGE.relative_to(PSM_ROOT)),
        "rejudge_package_gate": str(REJUDGE_GATE.relative_to(PSM_ROOT)),
    })
    write(REJUDGE_PACKAGE, package)
    write(REJUDGE_GATE, gate)
    write(BUDGET_LEDGER, ledger)
    write(CHECKPOINT, checkpoint)
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print(f"authorized_package_sha256: {gate['authorized_package_sha256']}")
    print("external_rejudge_calls_authorized: 1")
    print("additional_budget_usd: 4.00")
    print("reserved_month_usd: 36.00")
    print("participant_content_calls: 0")


if __name__ == "__main__":
    main()
