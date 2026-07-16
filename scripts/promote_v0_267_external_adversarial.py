#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.266_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.267_project_status.json"
PACKAGE = RUNTIME / "v0_267_external_adversarial_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_267_external_adversarial_package_gate.json"
REPAIR = RUNTIME / "v0_267_external_adversarial_repair_report.json"
JUDGE = RUNTIME / "v0_267_openai_external_adversarial_judge.json"
ATTEMPT_1 = RUNTIME / "v0_267_openai_external_adversarial_judge_attempt_1_failed.json"
ATTEMPT_2 = RUNTIME / "v0_267_openai_external_adversarial_judge_attempt_2_failed.json"
ATTEMPT_3 = RUNTIME / "v0_267_openai_external_adversarial_judge_attempt_3_failed.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
BROWSER = RUNTIME / "v0_267_external_adversarial_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_267_external_adversarial_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_267_external_adversarial_checkpoint.json"
MANIFEST = RUNTIME / "v0_267_external_adversarial_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, package, package_gate, repair, judge, attempt_1, attempt_2, attempt_3, budget, browser, docker = map(
        read,
        (SOURCE, PACKAGE, PACKAGE_GATE, REPAIR, JUDGE, ATTEMPT_1, ATTEMPT_2, ATTEMPT_3, BUDGET, BROWSER, DOCKER),
    )
    if package_gate.get("passed") is not True or not all((package_gate.get("checks") or {}).values()):
        raise SystemExit("V0.267 external package gate is not passing.")
    review = judge.get("review") or {}
    if not (
        judge.get("passed") is True
        and review.get("verdict") == "pass"
        and review.get("failed_pair_ids") == []
        and review.get("critical_findings") == []
        and len(review.get("pair_reviews") or []) == 15
        and all(item.get("verdict") == "pass" for item in review["pair_reviews"])
    ):
        raise SystemExit("V0.267 final external semantic judge is not passing.")
    if attempt_1.get("passed") is not False or attempt_2.get("passed") is not False or attempt_3.get("passed") is not False:
        raise SystemExit("V0.267 failed-attempt history is incomplete.")
    if repair.get("passed") is not True or repair.get("failed_external_pairs_repaired") != ["R07", "R08", "R09"]:
        raise SystemExit("V0.267 external findings were not repaired locally.")
    if float(budget.get("reserved_usd", 0)) != 16.0 or float(budget.get("limit_usd", 0)) != 20.0 or budget.get("participant_content_calls") != 0:
        raise SystemExit("V0.267 API budget ledger is invalid.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.267 browser evidence is not passing.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.267 Docker evidence is not passing.")
    if any(package["release_boundary"].values()) or package["privacy"]["training_eligible"] is not False:
        raise SystemExit("V0.267 source or release boundary is open.")

    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.267",
        "previous_formal_version": "psm_v0.266",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "independent_external_adversarial_semantic_judge_passed_after_retained_failures_and_repairs",
        "v0_267_external_adversarial_gate": {
            "passed": True,
            "provider": judge["provider"],
            "model": judge["actual_model"],
            "pairs": len(review["pair_reviews"]),
            "pairs_passed": sum(item["verdict"] == "pass" for item in review["pair_reviews"]),
            "final_failed_pairs": len(review["failed_pair_ids"]),
            "final_critical_findings": len(review["critical_findings"]),
            "failed_attempts_retained": 3,
            "external_findings_repaired": ["R07", "R08", "R09"],
            "reserved_monthly_budget_usd": float(budget["reserved_usd"]),
            "monthly_budget_limit_usd": float(budget["limit_usd"]),
            "participant_content_calls": budget["participant_content_calls"],
            "training_feedback_written": False,
            "human_validation_claimed": False,
            "package_sha256": digest(package),
            "judge_sha256": digest(judge),
        },
        "next_stage": {
            "version": "PSM_V0.268",
            "objective": "构建来源隔离的普通聊天任务完成度基准，覆盖翻译、改写、比较、解释、提取、摘要与规划；要求实际完成用户动作，禁止用边界说明、模型失败模板或任务复述代替答案。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_267_package": "runtime/v0_267_external_adversarial_review_package.json",
        "v0_267_package_gate": "runtime/v0_267_external_adversarial_package_gate.json",
        "v0_267_repair_report": "runtime/v0_267_external_adversarial_repair_report.json",
        "v0_267_external_judge": "runtime/v0_267_openai_external_adversarial_judge.json",
        "v0_267_attempt_1_failed": "runtime/v0_267_openai_external_adversarial_judge_attempt_1_failed.json",
        "v0_267_attempt_2_failed": "runtime/v0_267_openai_external_adversarial_judge_attempt_2_failed.json",
        "v0_267_attempt_3_failed": "runtime/v0_267_openai_external_adversarial_judge_attempt_3_failed.json",
        "v0_267_budget": "runtime/v0_267_api_budget_ledger.json",
        "v0_267_browser": "runtime/v0_267_external_adversarial_browser_regression/report.json",
        "v0_267_docker": "runtime/v0_267_external_adversarial_docker_boundary.json",
        "v0_267_checkpoint": "runtime/v0_267_external_adversarial_checkpoint.json",
        "v0_267_promotion_manifest": "runtime/v0_267_external_adversarial_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.267_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_267_external_adversarial_promotion_manifest_v1",
        "version": "PSM_V0.267",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": "independent_external_adversarial_semantic_judge_passed",
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "external_adversarial": target["v0_267_external_adversarial_gate"],
        "evidence": {
            "package": str(PACKAGE.relative_to(PSM_ROOT)),
            "package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
            "repair": str(REPAIR.relative_to(PSM_ROOT)),
            "final_judge": str(JUDGE.relative_to(PSM_ROOT)),
            "failed_attempts": [str(path.relative_to(PSM_ROOT)) for path in (ATTEMPT_1, ATTEMPT_2, ATTEMPT_3)],
            "budget": str(BUDGET.relative_to(PSM_ROOT)),
            "browser": str(BROWSER.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": package["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint = read(CHECKPOINT)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.267",
        "target_promoted": True,
        "status": "v0_267_promoted_v0_268_task_completion_benchmark_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "freeze_v0_268_task_completion_contract",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.268")


if __name__ == "__main__":
    main()
