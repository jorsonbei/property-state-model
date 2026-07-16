#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_272_long_context_state_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_272_long_context_state_report.json"
BUDGET = PSM_ROOT / "runtime" / "v0_267_api_budget_ledger.json"
STATUS = PSM_ROOT / "project_status_out" / "psm_v0.272_project_status.json"
PACKAGE = PSM_ROOT / "runtime" / "v0_273_external_long_context_review_package.json"
GATE = PSM_ROOT / "runtime" / "v0_273_external_long_context_package_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_273_external_long_context_checkpoint.json"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.openai_external_contract_judge import canonical_sha256  # noqa: E402
from psm_v0.openai_external_long_context_judge import (  # noqa: E402
    DIMENSIONS,
    PREPARED_AUTHORIZATION,
    validate_review_package,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    contract = read(CONTRACT)
    report = read(REPORT)
    budget = read(BUDGET)
    status = read(STATUS)
    summary = report.get("summary") or {}
    if not (
        status.get("current_version") == "psm_v0.272"
        and report.get("passed") is True
        and summary.get("cases") == summary.get("passed") == 10
        and summary.get("failed") == 0
    ):
        raise SystemExit("V0.272 promoted long-context answers are not ready for packaging.")
    if not (
        float(budget.get("limit_usd", 0)) == 24.0
        and float(budget.get("reserved_usd", 0)) == 24.0
        and budget.get("participant_content_calls") == 0
    ):
        raise SystemExit("V0.273 expected exhausted synthetic API budget is not retained.")
    cases = {case["id"]: case for case in contract["cases"]}
    rows = {row["case_id"]: row for row in report["rows"]}
    items = [
        {
            "review_id": f"L{index:02d}",
            "family": cases[case_id]["family"],
            "conversation": cases[case_id]["messages"],
            "final_answer": rows[case_id]["answer"],
        }
        for index, case_id in enumerate([case["id"] for case in contract["cases"]], start=1)
    ]
    payload = {"rubric_dimensions": list(DIMENSIONS), "items": items}
    package = {
        "schema_version": "psm_v0_273_external_long_context_review_package_v1",
        "version": "PSM_V0.273-candidate",
        "authorization": PREPARED_AUTHORIZATION,
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
            "maximum_api_calls": 0,
            "reserved_usd": 0.0,
            "reserved_total_month_usd": 24.0,
            "monthly_limit_usd": 24.0,
            "additional_authorization_required_usd": 4.0,
            "blocked_reason": "monthly_api_budget_exhausted",
        },
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
        "release_boundary": contract["release_boundary"],
    }
    validate_review_package(package, require_authorization=False)
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [
        token
        for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers")
        if token in serialized
    ]
    checks = {
        "source_v0_272_passed": report.get("passed") is True,
        "exact_item_count": len(items) == 10,
        "exact_family_coverage": len({item["family"] for item in items}) == 5,
        "minimum_seven_messages_per_item": all(len(item["conversation"]) >= 7 for item in items),
        "payload_hash_locked": canonical_sha256(payload) == package["review_payload_sha256"],
        "privacy_boundary_closed": package["privacy"]["synthetic_only"] is True and all(
            value is False for key, value in package["privacy"].items() if key != "synthetic_only"
        ),
        "prohibited_material_absent": not prohibited,
        "external_api_call_disabled": package["budget"]["maximum_api_calls"] == 0,
        "monthly_budget_fully_reserved": package["budget"]["reserved_total_month_usd"] == package["budget"]["monthly_limit_usd"] == 24.0,
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "release_boundary_closed": not any(package["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_273_external_long_context_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "prohibited_material_found": prohibited,
        "review_payload_sha256": package["review_payload_sha256"],
        "authorization": PREPARED_AUTHORIZATION,
    }
    write(PACKAGE, package)
    write(GATE, gate)
    if not gate["passed"]:
        raise SystemExit(f"V0.273 package gate failed: {[key for key, value in checks.items() if not value]}")

    blocked_status = copy.deepcopy(status)
    blocked_status["next_stage"].update({"blocked": True, "requires_user_input": True})
    blocked_status.setdefault("primary_artifacts", {}).update({
        "v0_273_external_package": "runtime/v0_273_external_long_context_review_package.json",
        "v0_273_external_package_gate": "runtime/v0_273_external_long_context_package_gate.json",
        "v0_273_checkpoint": "runtime/v0_273_external_long_context_checkpoint.json",
    })
    write(STATUS, blocked_status)
    write(CHECKPOINT, {
        "schema_version": "psm_v0_273_external_long_context_checkpoint_v1",
        "current_promoted_version": "PSM_V0.272",
        "target_version": "PSM_V0.273",
        "target_promoted": False,
        "passed": False,
        "status": "blocked_external_long_context_judge_monthly_api_budget_exhausted",
        "requires_user_input": True,
        "next_action": "await_additional_v0_273_external_judge_budget_authorization",
        "review_payload_sha256": package["review_payload_sha256"],
        "reserved_month_usd": 24.0,
        "monthly_limit_usd": 24.0,
        "additional_authorization_required_usd": 4.0,
        "participant_content_calls": 0,
        "package_gate_passed": True,
        "required_decision": "批准额外 4 美元 OpenAI 合成长对话独立评审预算，或停止 V0.273 外部评审。",
        "review_package": str(PACKAGE.relative_to(PSM_ROOT)),
        "package_gate": str(GATE.relative_to(PSM_ROOT)),
    })
    print(f"package: {PACKAGE.relative_to(ROOT)}")
    print(f"payload_sha256: {package['review_payload_sha256']}")
    print("items: 10")
    print("package_gate: passed")
    print("authorized_api_calls: 0")
    print("blocker: additional_usd_4_external_judge_budget_required")


if __name__ == "__main__":
    main()
