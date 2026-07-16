#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
ORIGINAL_JUDGE = RUNTIME / "v0_271_openai_external_multiturn_judge.json"
REPAIR = RUNTIME / "v0_271_external_multiturn_repair_report.json"
REJUDGE_PACKAGE = RUNTIME / "v0_271_external_multiturn_rejudge_package.json"
REJUDGE_PACKAGE_GATE = RUNTIME / "v0_271_external_multiturn_rejudge_package_gate.json"
REJUDGE = RUNTIME / "v0_271_openai_external_multiturn_rejudge.json"
RUNNER_FAILURE = RUNTIME / "v0_271_rejudge_runner_attempt_1_failed.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_271_external_multiturn_checkpoint.json"
GATE = RUNTIME / "v0_271_external_multiturn_gate.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    original, repair, package, package_gate, rejudge, runner_failure, budget, checkpoint = map(
        read,
        (ORIGINAL_JUDGE, REPAIR, REJUDGE_PACKAGE, REJUDGE_PACKAGE_GATE, REJUDGE, RUNNER_FAILURE, BUDGET, CHECKPOINT),
    )
    review = rejudge.get("review") or {}
    checks = {
        "original_external_failure_retained": (
            original.get("passed") is False
            and original.get("review", {}).get("failed_item_ids") == ["M07", "M08"]
        ),
        "local_repairs_passed": (
            repair.get("passed") is True
            and repair.get("failed_items_repaired_locally") == ["M07", "M08"]
        ),
        "rejudge_package_gate_passed": (
            package_gate.get("passed") is True
            and all((package_gate.get("checks") or {}).values())
        ),
        "rejudge_payload_hash_matches": (
            rejudge.get("review_payload_sha256") == package.get("review_payload_sha256")
        ),
        "external_rejudge_passed": rejudge.get("passed") is True and review.get("verdict") == "pass",
        "all_twelve_items_passed": (
            len(review.get("item_reviews") or []) == 12
            and all(item.get("verdict") == "pass" for item in review["item_reviews"])
        ),
        "no_failed_items": review.get("failed_item_ids") == [],
        "no_critical_findings": review.get("critical_findings") == [],
        "no_recommended_repairs": review.get("recommended_repairs") == [],
        "external_gate_checks_passed": all((rejudge.get("gate_checks") or {}).values()),
        "runner_failure_retained_without_retry": (
            runner_failure.get("passed") is False
            and runner_failure.get("external_result_passed") is True
            and runner_failure.get("api_retry_executed") is False
        ),
        "budget_exactly_authorized": (
            float(budget.get("base_limit_usd", 0)) == 20.0
            and float(budget.get("user_approved_rejudge_extension_usd", 0)) == 4.0
            and float(budget.get("limit_usd", 0)) == 24.0
            and float(budget.get("reserved_usd", 0)) == 24.0
        ),
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "submission_synthetic_only": rejudge.get("submission_scope", {}).get("synthetic_only") is True,
        "release_boundary_closed": (
            rejudge.get("release_boundary", {}).get("training_feedback_written") is False
            and rejudge.get("release_boundary", {}).get("rule_replacement_allowed") is False
            and rejudge.get("release_boundary", {}).get("public_service_allowed") is False
            and rejudge.get("release_boundary", {}).get("external_release_authority") is False
        ),
    }
    gate = {
        "schema_version": "psm_v0_271_external_multiturn_gate_v1",
        "version": "PSM_V0.271",
        "passed": all(checks.values()),
        "decision": "independent_external_multiturn_rejudge_passed_after_retained_failure_and_local_repair",
        "checks": checks,
        "external_model": rejudge.get("actual_model"),
        "items": len(review.get("item_reviews") or []),
        "items_passed": sum(item.get("verdict") == "pass" for item in review.get("item_reviews") or []),
        "failed_items": review.get("failed_item_ids"),
        "critical_findings": review.get("critical_findings"),
        "original_failed_items_retained": original.get("review", {}).get("failed_item_ids"),
        "local_repairs": repair.get("failed_items_repaired_locally"),
        "usage": rejudge.get("usage"),
        "review_payload_sha256": rejudge.get("review_payload_sha256"),
        "rejudge_package_sha256": digest(package),
        "rejudge_sha256": digest(rejudge),
        "human_feedback_collected": False,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "release_boundary": rejudge.get("release_boundary"),
    }
    write(GATE, gate)
    if not gate["passed"]:
        raise SystemExit(f"V0.271 final gate failed: {[key for key, value in checks.items() if not value]}")

    checkpoint.update({
        "status": "external_multiturn_rejudge_passed_ready_for_promotion",
        "passed": True,
        "target_promoted": False,
        "requires_user_input": False,
        "next_action": "promote_v0_271_external_multiturn_gate",
        "required_decision": "无；V0.271 已通过独立外部重审，等待自动晋级。",
        "external_rejudge_completed": True,
        "external_rejudge_passed": True,
        "external_rejudge": str(REJUDGE.relative_to(PSM_ROOT)),
        "external_gate": str(GATE.relative_to(PSM_ROOT)),
    })
    write(CHECKPOINT, checkpoint)
    print(f"gate: {GATE.relative_to(ROOT)}")
    print("passed: true")
    print("items_passed: 12/12")
    print("critical_findings: 0")
    print("api_retry_executed: false")


if __name__ == "__main__":
    main()
