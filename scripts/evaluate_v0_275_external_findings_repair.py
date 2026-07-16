#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path

from psm_v0.openai_external_open_context_judge import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
ORIGINAL_PACKAGE = RUNTIME / "v0_275_external_open_context_review_package.json"
EXTERNAL_JUDGE = RUNTIME / "v0_275_openai_external_open_context_judge.json"
LOCAL_REPORT = RUNTIME / "v0_274_open_context_generalization_report.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_275_external_open_context_checkpoint.json"
REPAIRED = RUNTIME / "v0_275_external_open_context_repaired_candidate.json"
REPAIR_REPORT = RUNTIME / "v0_275_external_open_context_repair_report.json"
REPAIR_GATE = RUNTIME / "v0_275_external_open_context_repair_gate.json"

EXPECTED_FAILED_IDS = ["O01", "O02", "O10"]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    original, judge, local_report, budget, checkpoint = map(
        read,
        (ORIGINAL_PACKAGE, EXTERNAL_JUDGE, LOCAL_REPORT, BUDGET, CHECKPOINT),
    )
    original_items = original["review_payload"]["items"]
    local_rows = local_report["rows"]
    if len(original_items) != 10 or len(local_rows) != 10:
        raise SystemExit("V0.275 repair source coverage changed.")
    repaired_items = []
    changed_ids = []
    for original_item, row in zip(original_items, local_rows, strict=True):
        item = copy.deepcopy(original_item)
        item["final_answer"] = row["answer"]
        repaired_items.append(item)
        if item["final_answer"] != original_item["final_answer"]:
            changed_ids.append(item["review_id"])
    payload = copy.deepcopy(original["review_payload"])
    payload["items"] = repaired_items
    repaired = {
        "schema_version": "psm_v0_275_external_open_context_repaired_candidate_v1",
        "version": "PSM_V0.275-rejudge-candidate",
        "source_failed_external_judge": "runtime/v0_275_openai_external_open_context_judge.json",
        "source_original_package": "runtime/v0_275_external_open_context_review_package.json",
        "source_local_report": "runtime/v0_274_open_context_generalization_report.json",
        "source_review_payload_sha256": original["review_payload_sha256"],
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
        "changed_item_ids": changed_ids,
        "authorization": "not_authorized_monthly_budget_exhausted",
        "budget": {
            "currency": "USD",
            "maximum_api_calls": 0,
            "reserved_usd": 0.0,
            "reserved_total_month_usd": 32.0,
            "monthly_limit_usd": 32.0,
            "additional_authorization_required_usd": 4.0,
        },
        "privacy": original["privacy"],
        "release_boundary": original["release_boundary"],
    }
    repaired_by_id = {item["review_id"]: item for item in repaired_items}
    checks = {
        "original_external_failure_retained": judge.get("passed") is False and judge.get("review", {}).get("failed_item_ids") == EXPECTED_FAILED_IDS,
        "external_critical_finding_retained": bool(judge.get("review", {}).get("critical_findings")),
        "local_contract_passed": local_report.get("passed") is True and local_report.get("summary", {}).get("passed") == 10,
        "only_failed_items_changed": changed_ids == EXPECTED_FAILED_IDS,
        "o01_is_direct": repaired_by_id["O01"]["final_answer"] == "榆叶",
        "o02_is_direct": repaired_by_id["O02"]["final_answer"] == "青松厅",
        "o10_is_plain_analogy": (
            "旧食材" in repaired_by_id["O10"]["final_answer"]
            and "新鲜食材" in repaired_by_id["O10"]["final_answer"]
            and all(marker not in repaired_by_id["O10"]["final_answer"] for marker in ("生产放行", "上线", "审批", "φ", "证伪"))
        ),
        "passing_items_unchanged": all(
            repaired_by_id[item["review_id"]]["final_answer"] == item["final_answer"]
            for item in original_items
            if item["review_id"] not in EXPECTED_FAILED_IDS
        ),
        "payload_hash_changed": repaired["review_payload_sha256"] != original["review_payload_sha256"],
        "rejudge_not_authorized": repaired["budget"]["maximum_api_calls"] == 0,
        "budget_fully_reserved": float(budget.get("limit_usd", 0)) == float(budget.get("reserved_usd", 0)) == 32.0,
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "privacy_boundary_closed": repaired["privacy"].get("synthetic_only") is True and all(value is False for key, value in repaired["privacy"].items() if key != "synthetic_only"),
        "release_boundary_closed": not any(repaired["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_275_external_open_context_repair_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "source_failed_item_ids": EXPECTED_FAILED_IDS,
        "changed_item_ids": changed_ids,
        "source_review_payload_sha256": original["review_payload_sha256"],
        "repaired_review_payload_sha256": repaired["review_payload_sha256"],
        "external_rejudge_completed": False,
    }
    report = {
        "schema_version": "psm_v0_275_external_open_context_repair_report_v1",
        "version": "PSM_V0.275-rejudge-candidate",
        "passed": gate["passed"],
        "external_failure_retained": True,
        "failed_items_repaired_locally": changed_ids,
        "repairs": {
            "O01": "Return only the recalled user label.",
            "O02": "Return only the recalled venue.",
            "O10": "Keep the kitchen analogy plain and remove internal or release language.",
        },
        "local_contract_cases_passed": local_report.get("summary", {}).get("passed"),
        "external_rejudge_completed": False,
        "release_boundary": repaired["release_boundary"],
    }
    write(REPAIRED, repaired)
    write(REPAIR_GATE, gate)
    write(REPAIR_REPORT, report)
    if not gate["passed"]:
        raise SystemExit(f"V0.275 local repair failed: {[key for key, value in checks.items() if not value]}")
    checkpoint.update({
        "status": "blocked_external_open_context_rejudge_monthly_api_budget_exhausted",
        "target_promoted": False,
        "passed": False,
        "requires_user_input": True,
        "next_action": "await_additional_v0_275_external_rejudge_budget_authorization",
        "reserved_month_usd": 32.0,
        "monthly_limit_usd": 32.0,
        "additional_authorization_required_usd": 4.0,
        "participant_content_calls": 0,
        "required_decision": "批准额外 4 美元 OpenAI 合成开放式长对话重审预算，或停止 V0.275 外部重审。",
        "failed_external_review": str(EXTERNAL_JUDGE.relative_to(PSM_ROOT)),
        "local_repair_report": str(REPAIR_REPORT.relative_to(PSM_ROOT)),
        "repaired_candidate": str(REPAIRED.relative_to(PSM_ROOT)),
        "repair_gate": str(REPAIR_GATE.relative_to(PSM_ROOT)),
    })
    write(CHECKPOINT, checkpoint)
    print(f"changed_item_ids: {changed_ids}")
    print(f"repaired_review_payload_sha256: {repaired['review_payload_sha256']}")
    print("local_repair_passed: true")
    print("external_rejudge_completed: false")
    print("external_calls_authorized: 0")
    print("additional_authorization_required_usd: 4.00")


if __name__ == "__main__":
    main()
