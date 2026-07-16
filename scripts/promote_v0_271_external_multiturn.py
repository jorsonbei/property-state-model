#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.270_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.271_project_status.json"
ORIGINAL_PACKAGE = RUNTIME / "v0_271_external_multiturn_review_package.json"
ORIGINAL_PACKAGE_GATE = RUNTIME / "v0_271_external_multiturn_package_gate.json"
ORIGINAL_JUDGE = RUNTIME / "v0_271_openai_external_multiturn_judge.json"
REPAIR = RUNTIME / "v0_271_external_multiturn_repair_report.json"
REPAIRED_CANDIDATE = RUNTIME / "v0_271_external_multiturn_repaired_candidate.json"
REJUDGE_PACKAGE = RUNTIME / "v0_271_external_multiturn_rejudge_package.json"
REJUDGE_PACKAGE_GATE = RUNTIME / "v0_271_external_multiturn_rejudge_package_gate.json"
REJUDGE = RUNTIME / "v0_271_openai_external_multiturn_rejudge.json"
RUNNER_FAILURE = RUNTIME / "v0_271_rejudge_runner_attempt_1_failed.json"
FINAL_GATE = RUNTIME / "v0_271_external_multiturn_gate.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_271_external_multiturn_checkpoint.json"
MANIFEST = RUNTIME / "v0_271_external_multiturn_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    (
        source,
        original_package,
        original_package_gate,
        original_judge,
        repair,
        repaired_candidate,
        rejudge_package,
        rejudge_package_gate,
        rejudge,
        runner_failure,
        final_gate,
        budget,
        checkpoint,
    ) = map(
        read,
        (
            SOURCE,
            ORIGINAL_PACKAGE,
            ORIGINAL_PACKAGE_GATE,
            ORIGINAL_JUDGE,
            REPAIR,
            REPAIRED_CANDIDATE,
            REJUDGE_PACKAGE,
            REJUDGE_PACKAGE_GATE,
            REJUDGE,
            RUNNER_FAILURE,
            FINAL_GATE,
            BUDGET,
            CHECKPOINT,
        ),
    )
    review = rejudge.get("review") or {}
    if source.get("current_version") != "psm_v0.270":
        raise SystemExit("V0.271 promotion source is not PSM V0.270.")
    if original_package_gate.get("passed") is not True or original_judge.get("passed") is not False:
        raise SystemExit("V0.271 original package or retained external failure is invalid.")
    if original_judge.get("review", {}).get("failed_item_ids") != ["M07", "M08"]:
        raise SystemExit("V0.271 original failed item set changed.")
    if repair.get("passed") is not True or repair.get("failed_items_repaired_locally") != ["M07", "M08"]:
        raise SystemExit("V0.271 local repair evidence is incomplete.")
    if repaired_candidate.get("review_payload_sha256") != rejudge_package.get("review_payload_sha256"):
        raise SystemExit("V0.271 repaired candidate changed before rejudge.")
    if rejudge_package_gate.get("passed") is not True or not all((rejudge_package_gate.get("checks") or {}).values()):
        raise SystemExit("V0.271 rejudge package gate is not passing.")
    if not (
        final_gate.get("passed") is True
        and all((final_gate.get("checks") or {}).values())
        and rejudge.get("passed") is True
        and review.get("verdict") == "pass"
        and review.get("failed_item_ids") == []
        and review.get("critical_findings") == []
        and len(review.get("item_reviews") or []) == 12
        and all(item.get("verdict") == "pass" for item in review["item_reviews"])
    ):
        raise SystemExit("V0.271 independent external rejudge is not passing.")
    if runner_failure.get("api_retry_executed") is not False or runner_failure.get("external_result_passed") is not True:
        raise SystemExit("V0.271 runner failure or no-retry boundary is not retained.")
    if not (
        float(budget.get("base_limit_usd", 0)) == 20.0
        and float(budget.get("user_approved_rejudge_extension_usd", 0)) == 4.0
        and float(budget.get("limit_usd", 0)) == 24.0
        and float(budget.get("reserved_usd", 0)) == 24.0
        and budget.get("participant_content_calls") == 0
    ):
        raise SystemExit("V0.271 authorized budget ledger is invalid.")
    if any(original_package["release_boundary"].values()):
        raise SystemExit("V0.271 source release boundary is open.")
    if any(
        rejudge["release_boundary"].get(key) is not False
        for key in ("training_feedback_written", "rule_replacement_allowed", "public_service_allowed", "external_release_authority")
    ):
        raise SystemExit("V0.271 rejudge release boundary is open.")

    external_gate = {
        "decision": final_gate["decision"],
        "passed": True,
        "provider": rejudge["provider"],
        "model": rejudge["actual_model"],
        "items": len(review["item_reviews"]),
        "items_passed": len(review["item_reviews"]),
        "final_failed_items": 0,
        "final_critical_findings": 0,
        "original_failed_items_retained": ["M07", "M08"],
        "local_repairs": ["M07", "M08"],
        "rejudge_total_tokens": int(rejudge.get("usage", {}).get("total_tokens", 0)),
        "runner_failures_retained": 1,
        "api_retries_after_pass": 0,
        "base_budget_usd": 20.0,
        "user_approved_extension_usd": 4.0,
        "reserved_monthly_budget_usd": 24.0,
        "participant_content_calls": 0,
        "synthetic_only": True,
        "training_feedback_written": False,
        "human_validation_claimed": False,
        "package_sha256": digest(rejudge_package),
        "judge_sha256": digest(rejudge),
        "gate_sha256": digest(final_gate),
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.271",
        "previous_formal_version": "psm_v0.270",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_multiturn_rejudge_passed_after_retained_failure_and_local_repair",
        "v0_271_external_multiturn_gate": external_gate,
        "next_stage": {
            "version": "PSM_V0.272",
            "objective": "冻结长对话状态连续性与冲突恢复契约，验证用户事实、明确更正、未解事项和输出约束经过多个干扰轮次后仍可恢复；助手历史不得升级为用户事实，旧风险不得跨越明确话题切换。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_271_original_package": "runtime/v0_271_external_multiturn_review_package.json",
        "v0_271_original_package_gate": "runtime/v0_271_external_multiturn_package_gate.json",
        "v0_271_original_external_failure": "runtime/v0_271_openai_external_multiturn_judge.json",
        "v0_271_repair_report": "runtime/v0_271_external_multiturn_repair_report.json",
        "v0_271_repaired_candidate": "runtime/v0_271_external_multiturn_repaired_candidate.json",
        "v0_271_rejudge_package": "runtime/v0_271_external_multiturn_rejudge_package.json",
        "v0_271_rejudge_package_gate": "runtime/v0_271_external_multiturn_rejudge_package_gate.json",
        "v0_271_external_rejudge": "runtime/v0_271_openai_external_multiturn_rejudge.json",
        "v0_271_runner_failure": "runtime/v0_271_rejudge_runner_attempt_1_failed.json",
        "v0_271_gate": "runtime/v0_271_external_multiturn_gate.json",
        "v0_271_budget": "runtime/v0_267_api_budget_ledger.json",
        "v0_271_checkpoint": "runtime/v0_271_external_multiturn_checkpoint.json",
        "v0_271_promotion_manifest": "runtime/v0_271_external_multiturn_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.271_project_status.json",
    })
    write(TARGET, target)

    manifest = {
        "schema_version": "psm_v0_271_external_multiturn_promotion_manifest_v1",
        "version": "PSM_V0.271",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": final_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_multiturn": external_gate,
        "evidence": {
            "original_package": str(ORIGINAL_PACKAGE.relative_to(PSM_ROOT)),
            "original_package_gate": str(ORIGINAL_PACKAGE_GATE.relative_to(PSM_ROOT)),
            "original_failure": str(ORIGINAL_JUDGE.relative_to(PSM_ROOT)),
            "repair": str(REPAIR.relative_to(PSM_ROOT)),
            "repaired_candidate": str(REPAIRED_CANDIDATE.relative_to(PSM_ROOT)),
            "rejudge_package": str(REJUDGE_PACKAGE.relative_to(PSM_ROOT)),
            "rejudge_package_gate": str(REJUDGE_PACKAGE_GATE.relative_to(PSM_ROOT)),
            "rejudge": str(REJUDGE.relative_to(PSM_ROOT)),
            "runner_failure": str(RUNNER_FAILURE.relative_to(PSM_ROOT)),
            "final_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
            "budget": str(BUDGET.relative_to(PSM_ROOT)),
        },
        "release_boundary": original_package["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.271",
        "target_promoted": True,
        "status": "v0_271_promoted_v0_272_long_context_state_continuity_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "freeze_v0_272_long_context_state_continuity_contract",
        "required_decision": "无；继续执行 V0.272 自动化长对话状态连续性验证。",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.272")


if __name__ == "__main__":
    main()
