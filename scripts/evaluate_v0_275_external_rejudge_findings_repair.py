#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path

from psm_v0.openai_external_open_context_judge import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
ORIGINAL_JUDGE = RUNTIME / "v0_275_openai_external_open_context_judge.json"
PRIOR_REPAIRED = RUNTIME / "v0_275_external_open_context_repaired_candidate.json"
REJUDGE_PACKAGE = RUNTIME / "v0_275_external_open_context_rejudge_package.json"
REJUDGE = RUNTIME / "v0_275_openai_external_open_context_rejudge.json"
LOCAL_REPORT = RUNTIME / "v0_274_open_context_generalization_report.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_275_external_open_context_checkpoint.json"
REPAIRED = RUNTIME / "v0_275_external_open_context_second_repair_candidate.json"
REPAIR_REPORT = RUNTIME / "v0_275_external_open_context_second_repair_report.json"
REPAIR_GATE = RUNTIME / "v0_275_external_open_context_second_repair_gate.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    original_judge, prior_repaired, rejudge_package, rejudge, local_report, budget, checkpoint = map(
        read,
        (ORIGINAL_JUDGE, PRIOR_REPAIRED, REJUDGE_PACKAGE, REJUDGE, LOCAL_REPORT, BUDGET, CHECKPOINT),
    )
    source_items = rejudge_package["review_payload"]["items"]
    local_rows = local_report["rows"]
    if len(source_items) != 10 or len(local_rows) != 10:
        raise SystemExit("V0.275 second repair source coverage changed.")

    repaired_items = []
    incremental_changes = []
    for source_item, row in zip(source_items, local_rows, strict=True):
        item = copy.deepcopy(source_item)
        item["final_answer"] = row["answer"]
        repaired_items.append(item)
        if item["final_answer"] != source_item["final_answer"]:
            incremental_changes.append(item["review_id"])
    payload = copy.deepcopy(rejudge_package["review_payload"])
    payload["items"] = repaired_items
    repaired = {
        "schema_version": "psm_v0_275_external_open_context_second_repair_candidate_v1",
        "version": "PSM_V0.275-second-rejudge-candidate",
        "source_original_external_failure": "runtime/v0_275_openai_external_open_context_judge.json",
        "source_failed_external_rejudge": "runtime/v0_275_openai_external_open_context_rejudge.json",
        "source_rejudge_package": "runtime/v0_275_external_open_context_rejudge_package.json",
        "source_local_report": "runtime/v0_274_open_context_generalization_report.json",
        "source_review_payload_sha256": rejudge_package["review_payload_sha256"],
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
        "incremental_changed_item_ids": incremental_changes,
        "cumulative_changed_item_ids": ["O01", "O02", "O09", "O10"],
        "authorization": "not_authorized_monthly_budget_exhausted",
        "budget": {
            "currency": "USD",
            "maximum_api_calls": 0,
            "reserved_usd": 0.0,
            "reserved_total_month_usd": 36.0,
            "monthly_limit_usd": 36.0,
            "additional_authorization_required_usd": 4.0,
        },
        "privacy": rejudge_package["privacy"],
        "release_boundary": rejudge_package["release_boundary"],
    }
    by_id = {item["review_id"]: item for item in repaired_items}
    prior_by_id = {item["review_id"]: item for item in prior_repaired["review_payload"]["items"]}
    checks = {
        "original_external_failure_retained": (
            original_judge.get("passed") is False
            and original_judge.get("review", {}).get("failed_item_ids") == ["O01", "O02", "O10"]
        ),
        "failed_external_rejudge_retained": (
            rejudge.get("passed") is False
            and rejudge.get("review", {}).get("failed_item_ids") == ["O09"]
            and bool(rejudge.get("review", {}).get("critical_findings"))
        ),
        "rejudge_reviewed_prior_repaired_hash": (
            rejudge.get("review", {}).get("review_payload_sha256") == prior_repaired["review_payload_sha256"]
            == rejudge_package["review_payload_sha256"]
        ),
        "local_contract_passed": local_report.get("passed") is True and local_report.get("summary", {}).get("passed") == 10,
        "only_rejudge_failure_changed": incremental_changes == ["O09"],
        "o09_is_direct": by_id["O09"]["final_answer"] == "咖啡通常更苦。",
        "prior_repairs_retained": (
            by_id["O01"]["final_answer"] == "榆叶"
            and by_id["O02"]["final_answer"] == "青松厅"
            and "旧食材" in by_id["O10"]["final_answer"]
            and all(by_id[item_id]["final_answer"] == prior_by_id[item_id]["final_answer"] for item_id in ("O01", "O02", "O10"))
        ),
        "other_items_unchanged": all(
            by_id[item["review_id"]]["final_answer"] == item["final_answer"]
            for item in source_items
            if item["review_id"] != "O09"
        ),
        "payload_hash_changed": repaired["review_payload_sha256"] != rejudge_package["review_payload_sha256"],
        "new_external_call_not_authorized": repaired["budget"]["maximum_api_calls"] == 0,
        "budget_fully_reserved": float(budget.get("limit_usd", 0)) == float(budget.get("reserved_usd", 0)) == 36.0,
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "privacy_boundary_closed": repaired["privacy"].get("synthetic_only") is True
        and all(value is False for key, value in repaired["privacy"].items() if key != "synthetic_only"),
        "release_boundary_closed": not any(repaired["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_275_external_open_context_second_repair_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "original_failed_item_ids": ["O01", "O02", "O10"],
        "rejudge_failed_item_ids": ["O09"],
        "incremental_changed_item_ids": incremental_changes,
        "source_review_payload_sha256": rejudge_package["review_payload_sha256"],
        "repaired_review_payload_sha256": repaired["review_payload_sha256"],
        "external_second_rejudge_completed": False,
    }
    report = {
        "schema_version": "psm_v0_275_external_open_context_second_repair_report_v1",
        "version": "PSM_V0.275-second-rejudge-candidate",
        "passed": gate["passed"],
        "original_external_failure_retained": True,
        "first_external_rejudge_failure_retained": True,
        "failed_items_repaired_locally": incremental_changes,
        "repair": {"O09": "Return only the direct flavor comparison requested after the topic switch."},
        "local_contract_cases_passed": local_report.get("summary", {}).get("passed"),
        "external_second_rejudge_completed": False,
        "release_boundary": repaired["release_boundary"],
    }
    write(REPAIRED, repaired)
    write(REPAIR_GATE, gate)
    write(REPAIR_REPORT, report)
    if not gate["passed"]:
        raise SystemExit(f"V0.275 second local repair failed: {[key for key, value in checks.items() if not value]}")

    checkpoint.update({
        "status": "blocked_external_open_context_second_rejudge_monthly_api_budget_exhausted",
        "target_promoted": False,
        "passed": False,
        "requires_user_input": True,
        "next_action": "await_additional_v0_275_second_rejudge_budget_authorization",
        "reserved_month_usd": 36.0,
        "monthly_limit_usd": 36.0,
        "additional_authorization_required_usd": 4.0,
        "participant_content_calls": 0,
        "required_decision": "V0.275 首次重审判定 O09 失败且已本地修复；批准额外 4 美元进行一次最终外部重审，或停止 V0.275。",
        "failed_external_rejudge": str(REJUDGE.relative_to(PSM_ROOT)),
        "second_local_repair_report": str(REPAIR_REPORT.relative_to(PSM_ROOT)),
        "second_repaired_candidate": str(REPAIRED.relative_to(PSM_ROOT)),
        "second_repair_gate": str(REPAIR_GATE.relative_to(PSM_ROOT)),
    })
    write(CHECKPOINT, checkpoint)
    print(f"incremental_changed_item_ids: {incremental_changes}")
    print(f"repaired_review_payload_sha256: {repaired['review_payload_sha256']}")
    print("local_repair_passed: true")
    print("external_second_rejudge_completed: false")
    print("external_calls_authorized: 0")
    print("additional_authorization_required_usd: 4.00")


if __name__ == "__main__":
    main()
