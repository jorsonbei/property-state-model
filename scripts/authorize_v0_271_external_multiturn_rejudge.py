#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
ORIGINAL_JUDGE = RUNTIME / "v0_271_openai_external_multiturn_judge.json"
REPAIR_REPORT = RUNTIME / "v0_271_external_multiturn_repair_report.json"
REPAIRED_CANDIDATE = RUNTIME / "v0_271_external_multiturn_repaired_candidate.json"
BUDGET_LEDGER = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_271_external_multiturn_checkpoint.json"
REJUDGE_PACKAGE = RUNTIME / "v0_271_external_multiturn_rejudge_package.json"
REJUDGE_GATE = RUNTIME / "v0_271_external_multiturn_rejudge_package_gate.json"

BASE_LIMIT_USD = 20.0
ADDITIONAL_AUTHORIZATION_USD = 4.0
EFFECTIVE_LIMIT_USD = BASE_LIMIT_USD + ADDITIONAL_AUTHORIZATION_USD
RESERVATION_ID = "V0_271_EXTERNAL_MULTITURN_REVIEW_ATTEMPT_2"
AUTHORIZATION = "approved_by_user_2026_07_16_additional_usd_4_synthetic_rejudge"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    original_judge = read(ORIGINAL_JUDGE)
    repair = read(REPAIR_REPORT)
    repaired = read(REPAIRED_CANDIDATE)
    ledger = read(BUDGET_LEDGER)
    checkpoint = read(CHECKPOINT)

    prior_failure_retained = (
        original_judge.get("passed") is False
        and original_judge.get("review", {}).get("failed_item_ids") == ["M07", "M08"]
    )
    local_repairs_pass = (
        repair.get("passed") is True
        and repair.get("failed_items_repaired_locally") == ["M07", "M08"]
        and repair.get("external_rejudge_completed") is False
    )
    prior_budget_is_closed = (
        float(ledger.get("limit_usd", 0)) == BASE_LIMIT_USD
        and float(ledger.get("reserved_usd", 0)) == BASE_LIMIT_USD
        and ledger.get("participant_content_calls") == 0
    )
    prior_checkpoint_is_blocked = (
        checkpoint.get("status") == "blocked_external_rejudge_monthly_api_budget_exhausted"
        and checkpoint.get("requires_user_input") is True
        and checkpoint.get("target_promoted") is False
    )
    items = {item["review_id"]: item for item in repaired["review_payload"]["items"]}
    repaired_answers_are_direct = (
        items["M07"]["final_answer"] == "当前项目版本是 PSM V0.270。"
        and items["M08"]["final_answer"] == "成熟香蕉通常更软。"
    )

    package = copy.deepcopy(repaired)
    package.update({
        "schema_version": "psm_v0_271_external_multiturn_review_package_v1",
        "version": "PSM_V0.271-rejudge-candidate",
        "authorization": AUTHORIZATION,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_scope": "one_synthetic_multiturn_semantic_rejudge_only",
        "source_failed_judge": "runtime/v0_271_openai_external_multiturn_judge.json",
        "source_repair_report": "runtime/v0_271_external_multiturn_repair_report.json",
    })
    package["budget"] = {
        "currency": "USD",
        "maximum_api_calls": 1,
        "reserved_usd": ADDITIONAL_AUTHORIZATION_USD,
        "reserved_total_month_usd": EFFECTIVE_LIMIT_USD,
        "monthly_limit_usd": EFFECTIVE_LIMIT_USD,
        "base_monthly_limit_usd": BASE_LIMIT_USD,
        "user_approved_additional_usd": ADDITIONAL_AUTHORIZATION_USD,
        "authorization_scope": "synthetic_multiturn_rejudge_only",
    }
    package.pop("source_external_judge", None)
    package.pop("local_repair_report", None)
    package.pop("source_failed_review_payload_sha256", None)

    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [
        token
        for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers")
        if token in serialized
    ]
    checks = {
        "prior_external_failure_retained": prior_failure_retained,
        "local_repairs_pass": local_repairs_pass,
        "prior_budget_is_closed": prior_budget_is_closed,
        "prior_checkpoint_is_blocked": prior_checkpoint_is_blocked,
        "repaired_answers_are_direct": repaired_answers_are_direct,
        "review_payload_hash_unchanged_from_repaired_candidate": (
            package["review_payload_sha256"] == repaired["review_payload_sha256"]
        ),
        "synthetic_privacy_boundary_closed": (
            package["privacy"].get("synthetic_only") is True
            and all(value is False for key, value in package["privacy"].items() if key != "synthetic_only")
        ),
        "release_boundary_closed": not any(package["release_boundary"].values()),
        "single_rejudge_call_authorized": package["budget"]["maximum_api_calls"] == 1,
        "additional_budget_exactly_four_usd": package["budget"]["user_approved_additional_usd"] == 4.0,
        "participant_content_calls_zero": ledger.get("participant_content_calls") == 0,
        "prohibited_material_absent": not prohibited,
    }
    gate = {
        "schema_version": "psm_v0_271_external_multiturn_rejudge_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "prohibited_material_found": prohibited,
        "review_payload_sha256": package["review_payload_sha256"],
        "authorization": AUTHORIZATION,
        "budget_extension_scope": "synthetic_multiturn_rejudge_only",
    }
    if not gate["passed"]:
        write(REJUDGE_GATE, gate)
        raise SystemExit(f"V0.271 rejudge authorization failed: {[key for key, value in checks.items() if not value]}")

    reservations = ledger.setdefault("reservations", [])
    existing = [item for item in reservations if item.get("reservation_id") == RESERVATION_ID]
    if existing and (
        len(existing) != 1
        or existing[0].get("reserved_cost_usd") != "4.00"
        or existing[0].get("contains_participant_content") is not False
    ):
        raise SystemExit("V0.271 rejudge reservation conflicts with the approved scope.")
    if not existing:
        reservations.append({
            "schema_version": "psm_v0_262_api_budget_reservation_v1",
            "reservation_id": RESERVATION_ID,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "synthetic_multiturn_semantic_rejudge",
            "reserved_cost_usd": "4.00",
            "contains_participant_content": False,
            "authorization_scope": "user_approved_v0_271_rejudge_only",
        })
    ledger.update({
        "base_limit_usd": "20.00",
        "user_approved_rejudge_extension_usd": "4.00",
        "limit_usd": "24.00",
        "reserved_usd": "24.00",
        "participant_content_calls": 0,
    })
    checkpoint.update({
        "status": "external_multiturn_rejudge_package_passed_single_call_authorized",
        "requires_user_input": False,
        "next_action": "run_authorized_openai_multiturn_semantic_rejudge",
        "review_payload_sha256": package["review_payload_sha256"],
        "reserved_month_usd": EFFECTIVE_LIMIT_USD,
        "monthly_limit_usd": EFFECTIVE_LIMIT_USD,
        "base_monthly_limit_usd": BASE_LIMIT_USD,
        "user_approved_additional_usd": ADDITIONAL_AUTHORIZATION_USD,
        "authorization_scope": "synthetic_multiturn_rejudge_only",
        "required_decision": "额外 4 美元合成多轮重审预算已获批准。",
        "rejudge_package": str(REJUDGE_PACKAGE.relative_to(PSM_ROOT)),
    })

    write(REJUDGE_PACKAGE, package)
    write(REJUDGE_GATE, gate)
    write(BUDGET_LEDGER, ledger)
    write(CHECKPOINT, checkpoint)
    print(f"package: {REJUDGE_PACKAGE.relative_to(ROOT)}")
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print("rejudge_calls_authorized: 1")
    print("additional_budget_usd: 4.00")
    print("reserved_month_usd: 24.00")
    print("participant_content_calls: 0")


if __name__ == "__main__":
    main()
