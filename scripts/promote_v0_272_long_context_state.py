#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.271_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.272_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_272_long_context_state_contract.json"
ERRATA = PSM_ROOT / "benchmarks" / "v0_272_long_context_state_errata.json"
REPORT = RUNTIME / "v0_272_long_context_state_report.json"
GATE = RUNTIME / "v0_272_long_context_state_gate.json"
LEDGER = RUNTIME / "v0_272_long_context_initial_failure_ledger.json"
BROWSER = RUNTIME / "v0_272_long_context_browser_regression" / "report.json"
DOCKER_ATTEMPT_1 = RUNTIME / "v0_272_long_context_docker_attempt_1_failed.json"
DOCKER = RUNTIME / "v0_272_long_context_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_272_long_context_state_checkpoint.json"
MANIFEST = RUNTIME / "v0_272_long_context_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, errata, report, gate, ledger, browser, docker_attempt, docker = map(
        read,
        (SOURCE, CONTRACT, ERRATA, REPORT, GATE, LEDGER, BROWSER, DOCKER_ATTEMPT_1, DOCKER),
    )
    summary = report.get("summary") or {}
    if source.get("current_version") != "psm_v0.271":
        raise SystemExit("V0.272 promotion source is not PSM V0.271.")
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.272 long-context gate is not passing.")
    if not (
        report.get("passed") is True
        and summary.get("cases") == summary.get("passed") == 10
        and summary.get("failed") == 0
        and len(summary.get("families") or {}) == 5
        and summary.get("assistant_history_contamination") == 0
        and summary.get("stale_state_violations") == 0
    ):
        raise SystemExit("V0.272 long-context evidence is incomplete.")
    if ledger.get("initial_failure_count") != 10 or ledger.get("append_only") is not True or ledger.get("contract_sha256") != digest(contract):
        raise SystemExit("V0.272 initial failure ledger is missing or changed.")
    if errata.get("source_contract_unchanged") is not True or len(errata.get("corrections") or []) != 1:
        raise SystemExit("V0.272 transparent domain errata is incomplete.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.272 browser evidence is not passing or used human actions.")
    if not (
        docker_attempt.get("passed") is False
        and docker_attempt.get("product_chat_failure") is False
        and docker_attempt.get("source_contract_changed") is False
        and docker.get("passed") is True
        and docker.get("human_feedback_collected") is False
    ):
        raise SystemExit("V0.272 Docker failure history or final boundary is incomplete.")
    if any(contract["source_isolation"].values()) or any(contract["release_boundary"].values()):
        raise SystemExit("V0.272 source-isolation or release boundary is open.")

    long_context_gate = {
        "decision": gate["decision"],
        "passed": True,
        "cases": summary["cases"],
        "cases_passed": summary["passed"],
        "families": len(summary["families"]),
        "initial_failure_count": ledger["initial_failure_count"],
        "assistant_history_contamination": summary["assistant_history_contamination"],
        "stale_state_violations": summary["stale_state_violations"],
        "total_duration_ms": summary["total_duration_ms"],
        "transparent_errata_count": len(errata["corrections"]),
        "docker_failures_retained": 1,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "contract_sha256": digest(contract),
        "errata_sha256": digest(errata),
        "gate_sha256": digest(gate),
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.272",
        "previous_formal_version": "psm_v0.271",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "long_context_state_continuity_and_conflict_recovery_gate_passed_after_retained_failures",
        "v0_272_long_context_state_gate": long_context_gate,
        "next_stage": {
            "version": "PSM_V0.273",
            "objective": "对冻结的 V0.272 长对话状态回答执行来源隔离的独立外部语义裁判，重点检查用户事实权威、最新更正、未解任务、跨轮约束与持续话题切换；只提交合成问答，不提交规则、私有资料或训练字段。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_272_contract": "benchmarks/v0_272_long_context_state_contract.json",
        "v0_272_errata": "benchmarks/v0_272_long_context_state_errata.json",
        "v0_272_report": "runtime/v0_272_long_context_state_report.json",
        "v0_272_gate": "runtime/v0_272_long_context_state_gate.json",
        "v0_272_initial_failure_ledger": "runtime/v0_272_long_context_initial_failure_ledger.json",
        "v0_272_browser": "runtime/v0_272_long_context_browser_regression/report.json",
        "v0_272_docker_attempt_1_failed": "runtime/v0_272_long_context_docker_attempt_1_failed.json",
        "v0_272_docker": "runtime/v0_272_long_context_docker_boundary.json",
        "v0_272_checkpoint": "runtime/v0_272_long_context_state_checkpoint.json",
        "v0_272_promotion_manifest": "runtime/v0_272_long_context_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.272_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_272_long_context_promotion_manifest_v1",
        "version": "PSM_V0.272",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "long_context_state": long_context_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "errata": str(ERRATA.relative_to(PSM_ROOT)),
            "report": str(REPORT.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
            "initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
            "browser": str(BROWSER.relative_to(PSM_ROOT)),
            "docker_attempt_1_failed": str(DOCKER_ATTEMPT_1.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint = read(CHECKPOINT)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.272",
        "target_promoted": True,
        "status": "v0_272_promoted_v0_273_external_long_context_package_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_273_external_long_context_review_package",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.273")


if __name__ == "__main__":
    main()
