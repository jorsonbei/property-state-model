from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.participant_feedback import (  # noqa: E402
    FEEDBACK_ELIGIBLE_NOT_BEFORE,
    SEVERE_ISSUES,
    load_feedback_state,
    public_feedback_progress,
    validate_feedback_state,
)


CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_265_structured_feedback_contract.json"
FEEDBACK_PATH = PSM_ROOT / "private_runtime" / "v0_265" / "feedback_state.json"
GATE_PATH = PSM_ROOT / "runtime" / "v0_265_structured_feedback_gate.json"
CHECKPOINT_PATH = PSM_ROOT / "runtime" / "v0_265_structured_feedback_checkpoint.json"
BROWSER_PATH = PSM_ROOT / "runtime" / "v0_265_structured_feedback_browser_regression" / "report.json"
DOCKER_PATH = PSM_ROOT / "runtime" / "v0_265_structured_feedback_docker_boundary.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the PSM V0.265 structured participant feedback gate.")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    contract = read_json(CONTRACT_PATH)
    parent_path = PSM_ROOT / contract["parent_promotion"]["path"]
    parent = read_json(parent_path)
    browser = read_json(BROWSER_PATH) if BROWSER_PATH.exists() else {}
    docker = read_json(DOCKER_PATH) if DOCKER_PATH.exists() else {}
    feedback = load_feedback_state(FEEDBACK_PATH)
    validation_errors = validate_feedback_state(feedback)
    progress = public_feedback_progress(
        feedback,
        required_per_participant=contract["scope"]["required_rated_turns_per_participant"],
    )
    events = feedback["feedback_events"]
    coverage_passed = progress["coverage_gate_passed"]
    med_helpfulness = statistics.median(item["helpfulness"] for item in events) if events else None
    med_clarity = statistics.median(item["clarity"] for item in events) if events else None
    aligned = sum(item["state_alignment"] in {"yes", "partial"} for item in events)
    alignment_ratio = aligned / len(events) if events else None
    no_alignment_events = sum(item["state_alignment"] == "no" for item in events)
    severe_issue_events = sum(item["issue_category"] in SEVERE_ISSUES for item in events)
    quality = contract["quality_gate"]
    quality_checks = {
        "median_helpfulness": med_helpfulness is not None and med_helpfulness >= quality["median_helpfulness_minimum"],
        "median_clarity": med_clarity is not None and med_clarity >= quality["median_clarity_minimum"],
        "alignment_ratio": alignment_ratio is not None
        and alignment_ratio >= quality["minimum_yes_or_partial_alignment_ratio"],
        "no_alignment_events": no_alignment_events <= quality["maximum_no_alignment_events"],
        "severe_issue_events": severe_issue_events <= quality["maximum_severe_issue_events"],
    }
    quality_evaluated = coverage_passed
    quality_passed = quality_evaluated and all(quality_checks.values())
    parent_hash = canonical_sha256(parent)
    checks = {
        "parent_v0_264_promoted": parent.get("promoted") is True and parent.get("version") == "PSM_V0.264",
        "parent_manifest_hash_locked": parent_hash == contract["parent_promotion"]["canonical_sha256"],
        "feedback_state_valid": not validation_errors,
        "feedback_state_private_only": feedback.get("private_only") is True,
        "retention_seven_days": feedback.get("retention_days") == 7,
        "new_turn_boundary_locked": (
            feedback.get("eligible_not_before") == FEEDBACK_ELIGIBLE_NOT_BEFORE
            and contract["scope"].get("eligible_turn_not_before_utc") == FEEDBACK_ELIGIBLE_NOT_BEFORE
        ),
        "fixed_fields_only": all(item.get("free_text_collected") is False for item in events),
        "raw_content_not_persisted": all(
            item.get("raw_prompt_persisted") is False and item.get("raw_answer_persisted") is False
            for item in events
        ),
        "participant_content_external_calls_zero": all(
            item.get("participant_content_sent_to_external_api") is False for item in events
        ),
        "browser_evidence_passed_without_participant_impersonation": (
            browser.get("passed") is True
            and browser.get("human_participant_actions_executed") is False
            and browser.get("backend_feedback_submitted") is False
            and browser.get("checks", {}).get("free_text_field_present") is False
        ),
        "docker_private_state_boundary_passed": docker.get("passed") is True,
        "three_rated_turns_per_participant": coverage_passed,
        "quality_thresholds_passed": quality_passed,
    }
    passed = all(checks.values())
    if not coverage_passed:
        decision = "awaiting_structured_participant_feedback"
    elif quality_passed:
        decision = "structured_participant_feedback_gate_passed"
    else:
        decision = "structured_participant_feedback_quality_gate_failed"

    gate = {
        "schema_version": "psm_v0_265_structured_feedback_gate_v1",
        "version": "PSM_V0.265",
        "parent_version": "PSM_V0.264",
        "decision": decision,
        "passed": passed,
        "checks": checks,
        "progress": progress,
        "quality": {
            "evaluated": quality_evaluated,
            "passed": quality_passed,
            "median_helpfulness": med_helpfulness,
            "median_clarity": med_clarity,
            "yes_or_partial_alignment_ratio": alignment_ratio,
            "no_alignment_events": no_alignment_events,
            "severe_issue_events": severe_issue_events,
            "threshold_checks": quality_checks if quality_evaluated else None,
        },
        "privacy_evidence": {
            "feedback_events": len(events),
            "free_text_events": sum(item.get("free_text_collected") is True for item in events),
            "raw_prompt_events": sum(item.get("raw_prompt_persisted") is True for item in events),
            "raw_answer_events": sum(item.get("raw_answer_persisted") is True for item in events),
            "participant_content_external_api_calls": sum(
                item.get("participant_content_sent_to_external_api") is True for item in events
            ),
            "validation_errors": validation_errors,
        },
        "release_boundary": contract["release_boundary"],
    }
    write_json(GATE_PATH, gate)

    remaining = [
        f"{item['participant_id']} 还需 {max(0, item['required'] - item['credited'])} 次"
        for item in progress["participants"]
        if not item["complete"]
    ]
    if not coverage_passed:
        required_decision = (
            "需要用户介入：请让 P01、P02、P03 各自在操作员现场监督下提出三个新的低风险一般问题，"
            "并在每个回答下提交有帮助程度、清楚程度、状态对齐和主要问题四项结构化回馈。"
            f"当前剩余：{'；'.join(remaining)}。不要输入身份、联系、医疗、法律、交易或其他私人资料。"
        )
    elif quality_passed:
        required_decision = "V0.265 结构化回馈覆盖与质量门均已通过，可以进入下一阶段独立复核。"
    else:
        required_decision = "V0.265 已收齐结构化回馈，但质量门未通过；必须先分析固定评分残差，不得晋升。"
    checkpoint = {
        "schema_version": "psm_v0_265_structured_feedback_checkpoint_v1",
        "current_promoted_version": "PSM_V0.264",
        "target_version": "PSM_V0.265",
        "target_promoted": False,
        "status": decision,
        "requires_user_input": not coverage_passed,
        "progress": progress,
        "quality_evaluated": quality_evaluated,
        "completed_engineering": [
            "closed fixed-field feedback schema with no free text",
            "per-turn HMAC feedback token bound to an eligible low-risk participant event",
            "one feedback submission per eligible turn",
            "seven-day private structured-feedback retention",
            "participant withdrawal deletes that participant's feedback",
            "raw prompts and answers remain unpersisted and outside external APIs",
            "aggregate-only public progress and quality gate",
            "desktop and mobile fixed-field browser regression without participant impersonation",
            "Docker exclusion of private enrollment and feedback state",
        ],
        "evidence": {
            "contract": str(CONTRACT_PATH.relative_to(PSM_ROOT)),
            "gate": str(GATE_PATH.relative_to(PSM_ROOT)),
            "browser": str(BROWSER_PATH.relative_to(PSM_ROOT)),
            "docker_boundary": str(DOCKER_PATH.relative_to(PSM_ROOT)),
        },
        "release_boundary": contract["release_boundary"],
        "required_decision": required_decision,
    }
    write_json(CHECKPOINT_PATH, checkpoint)
    print(json.dumps(checkpoint, ensure_ascii=False, indent=2))
    if not passed and not args.allow_incomplete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
