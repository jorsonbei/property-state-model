#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from psm_v0.openai_external_long_context_judge import canonical_sha256, validate_external_review, validate_review_package


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.272_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.273_project_status.json"
PREPARED_PACKAGE = RUNTIME / "v0_273_external_long_context_review_package.json"
PREPARED_GATE = RUNTIME / "v0_273_external_long_context_package_gate.json"
AUTHORIZED_PACKAGE = RUNTIME / "v0_273_external_long_context_authorized_review_package.json"
AUTHORIZATION_GATE = RUNTIME / "v0_273_external_long_context_authorization_gate.json"
JUDGE = RUNTIME / "v0_273_openai_external_long_context_judge.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
CHECKPOINT = RUNTIME / "v0_273_external_long_context_checkpoint.json"
FINAL_GATE = RUNTIME / "v0_273_external_long_context_gate.json"
MANIFEST = RUNTIME / "v0_273_external_long_context_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source, prepared, prepared_gate, package, authorization_gate, judge, budget, checkpoint = map(
        read,
        (SOURCE, PREPARED_PACKAGE, PREPARED_GATE, AUTHORIZED_PACKAGE, AUTHORIZATION_GATE, JUDGE, BUDGET, CHECKPOINT),
    )
    validate_review_package(prepared, require_authorization=False)
    validate_review_package(package, require_authorization=True)
    external_checks = validate_external_review(judge["review"], package)
    reservations = [
        item
        for item in budget.get("reservations", [])
        if item.get("reservation_id") == "V0_273_EXTERNAL_LONG_CONTEXT_REVIEW_ATTEMPT_1"
    ]
    item_reviews = judge.get("review", {}).get("item_reviews", [])
    checks = {
        "source_version_is_v0_272": source.get("current_version") == "psm_v0.272",
        "prepared_package_gate_passed": prepared_gate.get("passed") is True and all(prepared_gate.get("checks", {}).values()),
        "authorization_gate_passed": authorization_gate.get("passed") is True and all(authorization_gate.get("checks", {}).values()),
        "prepared_payload_hash_retained": prepared["review_payload_sha256"] == package["review_payload_sha256"],
        "authorized_package_hash_match": authorization_gate.get("authorized_package_sha256") == canonical_sha256(package),
        "external_review_passed": judge.get("passed") is True and all(external_checks.values()),
        "external_review_exact_ten_items": len(item_reviews) == 10,
        "external_review_all_items_passed": all(item.get("verdict") == "pass" for item in item_reviews),
        "external_review_has_no_failed_ids": judge.get("review", {}).get("failed_item_ids") == [],
        "external_review_has_no_critical_findings": judge.get("review", {}).get("critical_findings") == [],
        "external_review_requires_no_repairs": judge.get("review", {}).get("recommended_repairs") == [],
        "single_budget_reservation_retained": len(reservations) == 1 and reservations[0].get("reserved_cost_usd") == "4.00",
        "budget_exactly_twenty_eight_usd": float(budget.get("limit_usd", 0)) == float(budget.get("reserved_usd", 0)) == 28.0,
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "release_boundary_closed": (
            judge.get("release_boundary", {}).get("participant_content_submitted") is False
            and judge.get("release_boundary", {}).get("training_feedback_written") is False
            and judge.get("release_boundary", {}).get("rule_replacement_allowed") is False
            and judge.get("release_boundary", {}).get("public_service_allowed") is False
            and judge.get("release_boundary", {}).get("external_release_authority") is False
        ),
    }
    gate = {
        "schema_version": "psm_v0_273_external_long_context_gate_v1",
        "passed": all(checks.values()),
        "decision": "external_long_context_semantic_review_passed",
        "checks": checks,
        "review_payload_sha256": package["review_payload_sha256"],
        "authorized_package_sha256": canonical_sha256(package),
        "external_review_sha256": canonical_sha256(judge),
        "actual_model": judge.get("actual_model"),
        "usage": judge.get("usage"),
        "failed_item_ids": judge.get("review", {}).get("failed_item_ids"),
        "critical_findings": judge.get("review", {}).get("critical_findings"),
        "recommended_repairs": judge.get("review", {}).get("recommended_repairs"),
    }
    write(FINAL_GATE, gate)
    if not gate["passed"]:
        raise SystemExit(f"V0.273 promotion failed: {[key for key, value in checks.items() if not value]}")

    external_gate = {
        "decision": gate["decision"],
        "passed": True,
        "items": len(item_reviews),
        "items_passed": sum(item["verdict"] == "pass" for item in item_reviews),
        "families": len({item["family"] for item in package["review_payload"]["items"]}),
        "failed_item_ids": [],
        "critical_findings": [],
        "recommended_repairs": [],
        "actual_model": judge["actual_model"],
        "total_tokens": judge.get("usage", {}).get("total_tokens", 0),
        "review_payload_sha256": package["review_payload_sha256"],
        "participant_content_calls": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.273",
        "previous_formal_version": "psm_v0.272",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_long_context_semantic_review_passed_10_of_10",
        "v0_273_external_long_context_gate": external_gate,
        "next_stage": {
            "version": "PSM_V0.274",
            "objective": "建立开放式长对话泛化门：对同一状态约束生成未见过的改写、插入噪声和自然追问，验证状态胶囊能够驱动正常聊天而非只命中固定模板；本地模型只负责语言生成，不得控制风险、路由或发布边界。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_273_prepared_package": str(PREPARED_PACKAGE.relative_to(PSM_ROOT)),
        "v0_273_prepared_gate": str(PREPARED_GATE.relative_to(PSM_ROOT)),
        "v0_273_authorized_package": str(AUTHORIZED_PACKAGE.relative_to(PSM_ROOT)),
        "v0_273_authorization_gate": str(AUTHORIZATION_GATE.relative_to(PSM_ROOT)),
        "v0_273_external_judge": str(JUDGE.relative_to(PSM_ROOT)),
        "v0_273_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
        "v0_273_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_273_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.273_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_273_external_long_context_promotion_manifest_v1",
        "version": "PSM_V0.273",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_long_context_review": external_gate,
        "evidence": {
            "prepared_package": str(PREPARED_PACKAGE.relative_to(PSM_ROOT)),
            "prepared_gate": str(PREPARED_GATE.relative_to(PSM_ROOT)),
            "authorized_package": str(AUTHORIZED_PACKAGE.relative_to(PSM_ROOT)),
            "authorization_gate": str(AUTHORIZATION_GATE.relative_to(PSM_ROOT)),
            "external_judge": str(JUDGE.relative_to(PSM_ROOT)),
            "external_judge_markdown": str(JUDGE.with_suffix(".md").relative_to(PSM_ROOT)),
            "final_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
            "budget_ledger": str(BUDGET.relative_to(PSM_ROOT)),
        },
        "file_sha256": {
            "external_judge": file_sha256(JUDGE),
            "external_judge_markdown": file_sha256(JUDGE.with_suffix(".md")),
            "final_gate": file_sha256(FINAL_GATE),
        },
        "release_boundary": judge["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.273",
        "target_promoted": True,
        "passed": True,
        "status": "v0_273_promoted_v0_274_open_context_generalization_open",
        "requires_user_input": False,
        "next_action": "build_v0_274_open_context_generalization_contract",
        "external_review": str(JUDGE.relative_to(PSM_ROOT)),
        "final_gate": str(FINAL_GATE.relative_to(PSM_ROOT)),
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.274")


if __name__ == "__main__":
    main()
