#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.269_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.270_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_270_multiturn_constraint_contract.json"
ERRATA = PSM_ROOT / "benchmarks" / "v0_270_multiturn_constraint_errata.json"
REPORT = RUNTIME / "v0_270_multiturn_constraint_report.json"
GATE = RUNTIME / "v0_270_multiturn_constraint_gate.json"
LEDGER = RUNTIME / "v0_270_multiturn_initial_failure_ledger.json"
EVALUATOR_GAP = RUNTIME / "v0_270_evaluator_gap_report.json"
BROWSER = RUNTIME / "v0_270_multiturn_browser_regression" / "report.json"
BROWSER_FAILED = RUNTIME / "v0_270_browser_attempts_failed.json"
DOCKER = RUNTIME / "v0_270_multiturn_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_270_multiturn_constraint_checkpoint.json"
MANIFEST = RUNTIME / "v0_270_multiturn_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, errata, report, gate, ledger, evaluator_gap, browser, browser_failed, docker = map(read, (SOURCE, CONTRACT, ERRATA, REPORT, GATE, LEDGER, EVALUATOR_GAP, BROWSER, BROWSER_FAILED, DOCKER))
    summary = report.get("summary") or {}
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.270 multi-turn gate is not passing.")
    if not (
        report.get("passed") is True
        and summary.get("cases") == summary.get("passed") == 12
        and summary.get("failed") == 0
        and len(summary.get("families") or {}) == 4
        and summary.get("assistant_history_contamination") == 0
        and summary.get("stale_constraint_violations") == 0
    ):
        raise SystemExit("V0.270 frozen multi-turn evidence is incomplete.")
    if ledger.get("initial_failure_count") != 5 or ledger.get("append_only") is not True or ledger.get("contract_sha256") != digest(contract):
        raise SystemExit("V0.270 initial failure ledger is missing or changed.")
    if errata.get("source_contract_unchanged") is not True or len(errata.get("corrections") or []) != 3:
        raise SystemExit("V0.270 transparent contract errata is incomplete.")
    if evaluator_gap.get("passed") is not False or evaluator_gap.get("source_contract_changed") is not False:
        raise SystemExit("V0.270 evaluator gap is not retained.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.270 browser evidence is not passing or used human actions.")
    if browser_failed.get("passed") is not False or browser_failed.get("attempt_count") != 2 or browser_failed.get("product_code_changed") is not False:
        raise SystemExit("V0.270 failed browser-harness attempts are not retained.")
    if docker.get("passed") is not True or docker.get("human_feedback_collected") is not False:
        raise SystemExit("V0.270 Docker evidence is not passing or used human feedback.")
    if any(contract["source_isolation"].values()) or any(contract["release_boundary"].values()):
        raise SystemExit("V0.270 source-isolation or release boundary is open.")

    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.270",
        "previous_formal_version": "psm_v0.269",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "multiturn_reference_correction_and_constraint_gate_passed_after_retained_failures",
        "v0_270_multiturn_constraint_gate": {
            "decision": gate["decision"],
            "passed": True,
            "cases": summary["cases"],
            "cases_passed": summary["passed"],
            "families": len(summary["families"]),
            "initial_failure_count": ledger["initial_failure_count"],
            "assistant_history_contamination": summary["assistant_history_contamination"],
            "stale_constraint_violations": summary["stale_constraint_violations"],
            "total_duration_ms": summary["total_duration_ms"],
            "transparent_errata_count": len(errata["corrections"]),
            "evaluator_gaps_retained": 1,
            "synthetic_only": True,
            "human_validation_claimed": False,
            "contract_sha256": digest(contract),
            "errata_sha256": digest(errata),
            "gate_sha256": digest(gate),
        },
        "next_stage": {
            "version": "PSM_V0.271",
            "objective": "对冻结的 V0.270 多轮回答执行来源隔离的独立外部语义裁判，重点检查助手历史污染、话题切换、用户更正优先级与跨轮约束保持；只提交合成问答，不提交规则、私有资料或训练字段。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_270_contract": "benchmarks/v0_270_multiturn_constraint_contract.json",
        "v0_270_errata": "benchmarks/v0_270_multiturn_constraint_errata.json",
        "v0_270_report": "runtime/v0_270_multiturn_constraint_report.json",
        "v0_270_gate": "runtime/v0_270_multiturn_constraint_gate.json",
        "v0_270_initial_failure_ledger": "runtime/v0_270_multiturn_initial_failure_ledger.json",
        "v0_270_evaluator_gap": "runtime/v0_270_evaluator_gap_report.json",
        "v0_270_browser": "runtime/v0_270_multiturn_browser_regression/report.json",
        "v0_270_browser_attempts_failed": "runtime/v0_270_browser_attempts_failed.json",
        "v0_270_docker": "runtime/v0_270_multiturn_docker_boundary.json",
        "v0_270_checkpoint": "runtime/v0_270_multiturn_constraint_checkpoint.json",
        "v0_270_promotion_manifest": "runtime/v0_270_multiturn_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.270_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_270_multiturn_promotion_manifest_v1",
        "version": "PSM_V0.270",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "multiturn_constraints": target["v0_270_multiturn_constraint_gate"],
        "evidence": {key: str(path.relative_to(PSM_ROOT)) for key, path in {"contract": CONTRACT, "errata": ERRATA, "report": REPORT, "gate": GATE, "initial_failure_ledger": LEDGER, "evaluator_gap": EVALUATOR_GAP, "browser": BROWSER, "browser_attempts_failed": BROWSER_FAILED, "docker": DOCKER}.items()},
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint = read(CHECKPOINT)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.270",
        "target_promoted": True,
        "status": "v0_270_promoted_v0_271_external_multiturn_judge_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_271_external_multiturn_review_package",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.271")


if __name__ == "__main__":
    main()
