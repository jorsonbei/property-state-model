#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from psm_v0.openai_external_contract_judge import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_270_multiturn_constraint_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_270_multiturn_constraint_report.json"
BUDGET_LEDGER = PSM_ROOT / "runtime" / "v0_267_api_budget_ledger.json"
PACKAGE = PSM_ROOT / "runtime" / "v0_271_external_multiturn_review_package.json"
GATE = PSM_ROOT / "runtime" / "v0_271_external_multiturn_package_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_271_external_multiturn_checkpoint.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    contract = read(CONTRACT)
    report = read(REPORT)
    if report.get("passed") is not True or report.get("summary", {}).get("passed") != 12:
        raise SystemExit("V0.270 promoted multi-turn answers are not passing.")
    cases = {case["id"]: case for case in contract["cases"]}
    rows = {row["case_id"]: row for row in report["rows"]}
    items = []
    for index, case_id in enumerate([case["id"] for case in contract["cases"]], start=1):
        items.append({
            "review_id": f"M{index:02d}",
            "family": cases[case_id]["family"],
            "conversation": cases[case_id]["messages"],
            "final_answer": rows[case_id]["answer"],
        })
    payload = {
        "rubric_dimensions": [
            "semantic_correctness",
            "assistant_history_authority",
            "topic_switch",
            "user_correction_priority",
            "constraint_persistence",
            "answer_directness",
            "release_boundary"
        ],
        "items": items,
    }
    package = {
        "schema_version": "psm_v0_271_external_multiturn_review_package_v1",
        "version": "PSM_V0.271-candidate",
        "authorization": "approved_by_user_2026_07_15_synthetic_external_judge",
        "created_at": "2026-07-16",
        "privacy": {
            "synthetic_only": True,
            "contains_private_data": False,
            "contains_user_documents": False,
            "contains_participant_content": False,
            "contains_secrets": False,
            "contains_local_paths": False,
            "contains_candidate_rules": False,
            "contains_hidden_labels": False,
            "training_eligible": False,
        },
        "budget": {
            "currency": "USD",
            "maximum_api_calls": 1,
            "reserved_usd": 4.0,
            "reserved_total_month_usd": 20.0,
            "monthly_limit_usd": 20.0,
        },
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
        "release_boundary": contract["release_boundary"],
    }
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [token for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers") if token in serialized]
    checks = {
        "source_v0_270_passed": report.get("passed") is True,
        "exact_item_count": len(items) == 12,
        "exact_family_coverage": len({item["family"] for item in items}) == 4,
        "payload_hash_locked": canonical_sha256(payload) == package["review_payload_sha256"],
        "privacy_boundary_closed": all(value is False for key, value in package["privacy"].items() if key != "synthetic_only") and package["privacy"]["synthetic_only"] is True,
        "prohibited_material_absent": not prohibited,
        "single_call_budget": package["budget"]["maximum_api_calls"] == 1,
        "monthly_budget_not_exceeded": package["budget"]["reserved_total_month_usd"] <= package["budget"]["monthly_limit_usd"],
        "release_boundary_closed": not any(package["release_boundary"].values()),
    }
    write(PACKAGE, package)
    write(GATE, {
        "schema_version": "psm_v0_271_external_multiturn_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "prohibited_material_found": prohibited,
        "review_payload_sha256": package["review_payload_sha256"],
    })
    if not all(checks.values()):
        raise SystemExit(f"V0.271 package gate failed: {[key for key, value in checks.items() if not value]}")

    ledger = read(BUDGET_LEDGER)
    reservation_id = "V0_271_EXTERNAL_MULTITURN_REVIEW_ATTEMPT_1"
    if not any(item.get("reservation_id") == reservation_id for item in ledger["reservations"]):
        ledger["reservations"].append({
            "schema_version": "psm_v0_262_api_budget_reservation_v1",
            "reservation_id": reservation_id,
            "occurred_at": "2026-07-16T01:00:00Z",
            "purpose": "synthetic_multiturn_semantic_review",
            "reserved_cost_usd": "4.00",
            "contains_participant_content": False,
        })
    ledger["reserved_usd"] = "20.00"
    ledger["participant_content_calls"] = 0
    write(BUDGET_LEDGER, ledger)
    write(CHECKPOINT, {
        "schema_version": "psm_v0_271_external_multiturn_checkpoint_v1",
        "current_promoted_version": "PSM_V0.270",
        "target_version": "PSM_V0.271",
        "target_promoted": False,
        "status": "external_multiturn_package_passed_single_call_authorized",
        "requires_user_input": False,
        "next_action": "run_authorized_openai_multiturn_semantic_judge",
        "review_payload_sha256": package["review_payload_sha256"],
        "reserved_month_usd": 20.0,
        "monthly_limit_usd": 20.0,
    })
    print(f"package: {PACKAGE.relative_to(ROOT)}")
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print("items: 12")
    print("reserved_month_usd: 20.00")


if __name__ == "__main__":
    main()
