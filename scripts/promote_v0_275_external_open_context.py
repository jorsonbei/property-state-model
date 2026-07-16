#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from psm_v0.openai_external_open_context_judge import (
    canonical_sha256,
    validate_external_review,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.274_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.275_project_status.json"
PREPARED_PACKAGE = RUNTIME / "v0_275_external_open_context_review_package.json"
PREPARED_GATE = RUNTIME / "v0_275_external_open_context_package_gate.json"
FIRST_AUTHORIZED_PACKAGE = RUNTIME / "v0_275_external_open_context_authorized_review_package.json"
FIRST_AUTHORIZATION_GATE = RUNTIME / "v0_275_external_open_context_authorization_gate.json"
FIRST_JUDGE = RUNTIME / "v0_275_openai_external_open_context_judge.json"
FIRST_REPAIR = RUNTIME / "v0_275_external_open_context_repaired_candidate.json"
FIRST_REPAIR_GATE = RUNTIME / "v0_275_external_open_context_repair_gate.json"
REJUDGE_PACKAGE = RUNTIME / "v0_275_external_open_context_rejudge_package.json"
REJUDGE_PACKAGE_GATE = RUNTIME / "v0_275_external_open_context_rejudge_package_gate.json"
REJUDGE = RUNTIME / "v0_275_openai_external_open_context_rejudge.json"
SECOND_REPAIR = RUNTIME / "v0_275_external_open_context_second_repair_candidate.json"
SECOND_REPAIR_GATE = RUNTIME / "v0_275_external_open_context_second_repair_gate.json"
ATTEMPT_3_PACKAGE = RUNTIME / "v0_275_external_open_context_review_attempt_3_package.json"
ATTEMPT_3_PACKAGE_GATE = RUNTIME / "v0_275_external_open_context_review_attempt_3_package_gate.json"
ATTEMPT_3_JUDGE = RUNTIME / "v0_275_openai_external_open_context_judge_attempt_3.json"
TOKEN_AUTHORITY = RUNTIME / "v0_275_autonomous_api_token_authority.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_275_external_open_context_checkpoint.json"
FINAL_GATE = RUNTIME / "v0_275_external_open_context_gate.json"
MANIFEST = RUNTIME / "v0_275_external_open_context_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    (
        source,
        prepared,
        prepared_gate,
        first_package,
        first_authorization_gate,
        first_judge,
        first_repair,
        first_repair_gate,
        rejudge_package,
        rejudge_package_gate,
        rejudge,
        second_repair,
        second_repair_gate,
        attempt_3_package,
        attempt_3_package_gate,
        attempt_3_judge,
        token_authority,
        budget,
        checkpoint,
    ) = map(
        read,
        (
            SOURCE,
            PREPARED_PACKAGE,
            PREPARED_GATE,
            FIRST_AUTHORIZED_PACKAGE,
            FIRST_AUTHORIZATION_GATE,
            FIRST_JUDGE,
            FIRST_REPAIR,
            FIRST_REPAIR_GATE,
            REJUDGE_PACKAGE,
            REJUDGE_PACKAGE_GATE,
            REJUDGE,
            SECOND_REPAIR,
            SECOND_REPAIR_GATE,
            ATTEMPT_3_PACKAGE,
            ATTEMPT_3_PACKAGE_GATE,
            ATTEMPT_3_JUDGE,
            TOKEN_AUTHORITY,
            BUDGET,
            CHECKPOINT,
        ),
    )
    validate_review_package(prepared, require_authorization=False)
    validate_review_package(first_package, require_authorization=True)
    validate_review_package(rejudge_package, require_authorization=True)
    validate_review_package(attempt_3_package, require_authorization=True)
    external_checks = validate_external_review(attempt_3_judge["review"], attempt_3_package)
    review = attempt_3_judge["review"]
    actual_call_tokens = int((attempt_3_judge.get("usage") or {}).get("total_tokens") or 0)
    observed_before = int(token_authority["observed_tokens_before_reservation"])
    observed_after = observed_before + actual_call_tokens
    token_limit = int(token_authority["token_limit"])
    checks = {
        "source_version_is_v0_274": source.get("current_version") == "psm_v0.274",
        "prepared_package_gate_passed": prepared_gate.get("passed") is True and all(prepared_gate.get("checks", {}).values()),
        "first_authorization_gate_passed": (
            first_authorization_gate.get("passed") is True
            and all(first_authorization_gate.get("checks", {}).values())
        ),
        "first_external_failure_retained": (
            first_judge.get("passed") is False
            and first_judge.get("review", {}).get("failed_item_ids") == ["O01", "O02", "O10"]
        ),
        "first_local_repairs_retained": (
            first_repair_gate.get("passed") is True
            and first_repair.get("changed_item_ids") == ["O01", "O02", "O10"]
        ),
        "first_rejudge_package_gate_passed": (
            rejudge_package_gate.get("passed") is True
            and all(rejudge_package_gate.get("checks", {}).values())
        ),
        "first_external_rejudge_failure_retained": (
            rejudge.get("passed") is False
            and rejudge.get("review", {}).get("failed_item_ids") == ["O09"]
        ),
        "second_local_repair_retained": (
            second_repair_gate.get("passed") is True
            and second_repair.get("incremental_changed_item_ids") == ["O09"]
        ),
        "attempt_3_package_gate_passed": (
            attempt_3_package_gate.get("passed") is True
            and all(attempt_3_package_gate.get("checks", {}).values())
        ),
        "attempt_3_payload_is_second_repair": (
            attempt_3_package["review_payload_sha256"] == second_repair["review_payload_sha256"]
            == review.get("review_payload_sha256")
        ),
        "attempt_3_external_review_passed": attempt_3_judge.get("passed") is True and all(external_checks.values()),
        "attempt_3_exact_ten_items_passed": (
            len(review.get("item_reviews") or []) == 10
            and all(item.get("verdict") == "pass" for item in review["item_reviews"])
        ),
        "attempt_3_no_failed_items": review.get("failed_item_ids") == [],
        "attempt_3_no_critical_findings": review.get("critical_findings") == [],
        "attempt_3_no_recommended_repairs": review.get("recommended_repairs") == [],
        "token_authority_is_one_million": token_limit == 1_000_000 and token_authority.get("approval_required") is False,
        "actual_call_within_reservation": 0 < actual_call_tokens <= int(token_authority["reserved_tokens_for_next_call"]),
        "cumulative_usage_within_authority": observed_after <= token_limit,
        "legacy_dollar_reservations_retained": float(budget.get("limit_usd", 0)) == float(budget.get("reserved_usd", 0)) == 36.0,
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "submission_synthetic_only": attempt_3_judge.get("submission_scope", {}).get("synthetic_only") is True,
        "release_boundary_closed": all(
            attempt_3_judge.get("release_boundary", {}).get(key) is False
            for key in (
                "participant_content_submitted",
                "training_feedback_written",
                "rule_replacement_allowed",
                "public_service_allowed",
                "external_release_authority",
            )
        ),
    }
    gate = {
        "schema_version": "psm_v0_275_external_open_context_gate_v1",
        "version": "PSM_V0.275",
        "passed": all(checks.values()),
        "decision": "external_open_context_review_passed_on_attempt_3_after_retained_failures_and_local_repairs",
        "checks": checks,
        "external_model": attempt_3_judge.get("actual_model"),
        "items": len(review.get("item_reviews") or []),
        "items_passed": sum(item.get("verdict") == "pass" for item in review.get("item_reviews") or []),
        "final_failed_items": review.get("failed_item_ids"),
        "final_critical_findings": review.get("critical_findings"),
        "first_failed_items_retained": ["O01", "O02", "O10"],
        "rejudge_failed_items_retained": ["O09"],
        "first_local_repairs": ["O01", "O02", "O10"],
        "second_local_repairs": ["O09"],
        "attempt_3_usage": attempt_3_judge.get("usage"),
        "observed_tokens_after_call": observed_after,
        "token_authority_limit": token_limit,
        "review_payload_sha256": attempt_3_package["review_payload_sha256"],
        "attempt_3_package_sha256": canonical_sha256(attempt_3_package),
        "attempt_3_judge_sha256": canonical_sha256(attempt_3_judge),
        "human_feedback_collected": False,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "release_boundary": attempt_3_judge["release_boundary"],
    }
    write(FINAL_GATE, gate)
    if not gate["passed"]:
        raise SystemExit(f"V0.275 promotion failed: {[key for key, value in checks.items() if not value]}")

    external_gate = {
        "decision": gate["decision"],
        "passed": True,
        "provider": attempt_3_judge["provider"],
        "model": attempt_3_judge["actual_model"],
        "items": 10,
        "items_passed": 10,
        "final_failed_items": 0,
        "final_critical_findings": 0,
        "first_failed_items_retained": ["O01", "O02", "O10"],
        "rejudge_failed_items_retained": ["O09"],
        "cumulative_local_repairs": ["O01", "O02", "O09", "O10"],
        "attempt_3_total_tokens": actual_call_tokens,
        "observed_cumulative_openai_tokens": observed_after,
        "autonomous_token_authority_limit": token_limit,
        "participant_content_calls": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "training_feedback_written": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.275",
        "previous_formal_version": "psm_v0.274",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_open_context_review_passed_on_attempt_3_after_retained_failures_and_local_repairs",
        "v0_275_external_open_context_gate": external_gate,
        "next_stage": {
            "version": "PSM_V0.276",
            "objective": "建立长时程状态压缩与恢复门：在更长、多主题、含摘要压缩的合成对话中验证远距用户事实、最新更正、未完成事项和输出约束仍能恢复；比较状态胶囊与普通窗口，并保持评测不回流训练、外部发布关闭。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_275_prepared_package": str(PREPARED_PACKAGE.relative_to(PSM_ROOT)),
        "v0_275_first_external_failure": str(FIRST_JUDGE.relative_to(PSM_ROOT)),
        "v0_275_first_repair": str(FIRST_REPAIR.relative_to(PSM_ROOT)),
        "v0_275_first_rejudge_failure": str(REJUDGE.relative_to(PSM_ROOT)),
        "v0_275_second_repair": str(SECOND_REPAIR.relative_to(PSM_ROOT)),
        "v0_275_attempt_3_package": str(ATTEMPT_3_PACKAGE.relative_to(PSM_ROOT)),
        "v0_275_attempt_3_judge": str(ATTEMPT_3_JUDGE.relative_to(PSM_ROOT)),
        "v0_275_token_authority": str(TOKEN_AUTHORITY.relative_to(PSM_ROOT)),
        "v0_275_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
        "v0_275_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_275_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.275_project_status.json",
    })
    write(TARGET, target)

    token_authority.update({
        "observed_tokens_after_call": observed_after,
        "actual_last_call_tokens": actual_call_tokens,
        "reserved_tokens_for_next_call": 0,
        "remaining_tokens": token_limit - observed_after,
        "last_result": str(ATTEMPT_3_JUDGE.relative_to(PSM_ROOT)),
        "last_result_passed": True,
    })
    write(TOKEN_AUTHORITY, token_authority)
    manifest = {
        "schema_version": "psm_v0_275_external_open_context_promotion_manifest_v1",
        "version": "PSM_V0.275",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_open_context": external_gate,
        "evidence": {
            "prepared_package": str(PREPARED_PACKAGE.relative_to(PSM_ROOT)),
            "first_external_failure": str(FIRST_JUDGE.relative_to(PSM_ROOT)),
            "first_repair": str(FIRST_REPAIR.relative_to(PSM_ROOT)),
            "first_rejudge_failure": str(REJUDGE.relative_to(PSM_ROOT)),
            "second_repair": str(SECOND_REPAIR.relative_to(PSM_ROOT)),
            "attempt_3_package": str(ATTEMPT_3_PACKAGE.relative_to(PSM_ROOT)),
            "attempt_3_judge": str(ATTEMPT_3_JUDGE.relative_to(PSM_ROOT)),
            "final_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
            "token_authority": str(TOKEN_AUTHORITY.relative_to(PSM_ROOT)),
        },
        "file_sha256": {
            "attempt_3_judge": file_sha256(ATTEMPT_3_JUDGE),
            "attempt_3_judge_markdown": file_sha256(ATTEMPT_3_JUDGE.with_suffix(".md")),
            "final_gate": file_sha256(FINAL_GATE),
        },
        "release_boundary": attempt_3_judge["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.275",
        "target_promoted": True,
        "passed": True,
        "status": "v0_275_promoted_v0_276_long_horizon_state_compression_open",
        "requires_user_input": False,
        "next_action": "build_v0_276_long_horizon_state_compression_contract",
        "required_decision": "无；继续执行 V0.276 本地长时程状态压缩验证。",
        "attempt_3_external_review": str(ATTEMPT_3_JUDGE.relative_to(PSM_ROOT)),
        "final_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("attempt_3_items_passed: 10/10")
    print(f"observed_tokens_after_call: {observed_after}")
    print("next_stage: PSM_V0.276")


if __name__ == "__main__":
    main()
