#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
ORIGINAL_PACKAGE = PSM_ROOT / "runtime" / "v0_271_external_multiturn_review_package.json"
JUDGE = PSM_ROOT / "runtime" / "v0_271_openai_external_multiturn_judge.json"
REPAIR_REPORT = PSM_ROOT / "runtime" / "v0_271_external_multiturn_repair_report.json"
REPAIRED_PACKAGE = PSM_ROOT / "runtime" / "v0_271_external_multiturn_repaired_candidate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_271_external_multiturn_checkpoint.json"
BUDGET_LEDGER = PSM_ROOT / "runtime" / "v0_267_api_budget_ledger.json"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402
from psm_v0.openai_external_contract_judge import canonical_sha256  # noqa: E402


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    package = read(ORIGINAL_PACKAGE)
    judge = read(JUDGE)
    budget = read(BUDGET_LEDGER)
    if judge.get("passed") is not False or judge.get("review", {}).get("failed_item_ids") != ["M07", "M08"]:
        raise SystemExit("V0.271 expected external failure set is not retained.")
    items = {item["review_id"]: item for item in package["review_payload"]["items"]}
    context = server.load_project_context()
    repaired_rows = []
    for review_id in ("M07", "M08"):
        item = items[review_id]
        result = server.run_chat_turn(item["conversation"], "review")
        answer = result["chat"]["assistant_message"]
        if review_id == "M07":
            expected = f"当前项目版本是 {context['current_version']}。"
        else:
            expected = "成熟香蕉通常更软。"
        checks = {
            "exact_direct_answer": answer == expected,
            "quality_audit_passed": result["chat"]["quality_audit"]["status"] == "pass",
            "sigma_plus_delivery_passed": result["sigma_plus_delivery"]["passed"] is True,
            "external_release_closed": result["task_state_graph"]["boundaries"]["external_release_authority"] is False,
            "rule_replacement_closed": result["task_state_graph"]["boundaries"]["rule_replacement_allowed"] is False,
        }
        repaired_rows.append({
            "review_id": review_id,
            "passed": all(checks.values()),
            "checks": checks,
            "original_answer": item["final_answer"],
            "repaired_answer": answer,
            "expected_answer": expected,
            "generation": {key: result["chat"]["generation"].get(key) for key in ("status", "provider", "model", "error")},
        })
    repair_report = {
        "schema_version": "psm_v0_271_external_multiturn_repair_report_v1",
        "version": "PSM_V0.271-candidate",
        "passed": all(row["passed"] for row in repaired_rows),
        "external_failed_item_ids": judge["review"]["failed_item_ids"],
        "external_failure_retained": True,
        "failed_items_repaired_locally": [row["review_id"] for row in repaired_rows if row["passed"]],
        "rows": repaired_rows,
        "human_feedback_collected": False,
        "evaluation_rows_used_for_training": False,
        "external_rejudge_completed": False,
        "external_rejudge_blocker": "monthly_api_budget_exhausted",
    }
    write(REPAIR_REPORT, repair_report)
    if not repair_report["passed"]:
        raise SystemExit("V0.271 external findings are not fully repaired locally.")

    repaired = copy.deepcopy(package)
    repaired["schema_version"] = "psm_v0_271_external_multiturn_repaired_candidate_v1"
    repaired["authorization"] = "not_authorized_for_additional_call_budget_exhausted"
    repaired["created_at"] = "2026-07-16"
    repaired["source_failed_review_payload_sha256"] = package["review_payload_sha256"]
    repaired["source_external_judge"] = "runtime/v0_271_openai_external_multiturn_judge.json"
    repaired["local_repair_report"] = "runtime/v0_271_external_multiturn_repair_report.json"
    repaired_items = {item["review_id"]: item for item in repaired["review_payload"]["items"]}
    for row in repaired_rows:
        repaired_items[row["review_id"]]["final_answer"] = row["repaired_answer"]
    repaired["review_payload_sha256"] = canonical_sha256(repaired["review_payload"])
    repaired["budget"] = {
        "currency": "USD",
        "maximum_api_calls": 0,
        "reserved_usd": 0.0,
        "reserved_total_month_usd": float(budget["reserved_usd"]),
        "monthly_limit_usd": float(budget["limit_usd"]),
        "blocked_reason": "monthly_api_budget_exhausted",
        "additional_rejudge_reservation_required_usd": 4.0,
    }
    write(REPAIRED_PACKAGE, repaired)

    checkpoint = read(CHECKPOINT)
    checkpoint.update({
        "status": "blocked_external_rejudge_monthly_api_budget_exhausted",
        "passed": False,
        "target_promoted": False,
        "requires_user_input": True,
        "required_decision": "批准额外 4 美元 OpenAI 合成多轮语义重审预算，或停止 V0.271 外部重审。",
        "next_action": "await_additional_v0_271_rejudge_budget_authorization",
        "local_repairs_completed": True,
        "failed_items_repaired_locally": ["M07", "M08"],
        "repaired_candidate": str(REPAIRED_PACKAGE.relative_to(PSM_ROOT)),
        "reserved_month_usd": float(budget["reserved_usd"]),
        "monthly_limit_usd": float(budget["limit_usd"]),
    })
    write(CHECKPOINT, checkpoint)
    print("local_repairs_passed: true")
    print("failed_items_repaired: M07,M08")
    print(f"repaired_payload_sha256: {repaired['review_payload_sha256']}")
    print("external_rejudge_completed: false")
    print("blocker: monthly_api_budget_exhausted")


if __name__ == "__main__":
    main()
