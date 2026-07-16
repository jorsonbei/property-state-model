#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.268_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.269_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_269_task_stability_contract.json"
REPORT = RUNTIME / "v0_269_task_stability_report.json"
GATE = RUNTIME / "v0_269_task_stability_gate.json"
RECOVERY = RUNTIME / "v0_269_recovery_report.json"
LEDGER = RUNTIME / "v0_269_task_stability_initial_failure_ledger.json"
BROWSER = RUNTIME / "v0_269_stability_browser_regression" / "report.json"
BROWSER_ATTEMPT_1 = RUNTIME / "v0_269_stability_browser_regression" / "report_attempt_1_failed.json"
BROWSER_ERRATA = PSM_ROOT / "benchmarks" / "v0_269_browser_harness_errata.json"
DOCKER = RUNTIME / "v0_269_task_stability_docker_boundary.json"
DOCKER_ATTEMPT_1 = RUNTIME / "v0_269_task_stability_docker_attempt_1_failed.json"
CHECKPOINT = RUNTIME / "v0_269_task_stability_checkpoint.json"
MANIFEST = RUNTIME / "v0_269_task_stability_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, report, gate, recovery, ledger, browser, browser_attempt_1, browser_errata, docker, docker_attempt_1 = map(read, (SOURCE, CONTRACT, REPORT, GATE, RECOVERY, LEDGER, BROWSER, BROWSER_ATTEMPT_1, BROWSER_ERRATA, DOCKER, DOCKER_ATTEMPT_1))
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.269 task-stability gate is not passing.")
    summary = report.get("summary") or {}
    if not (
        summary.get("runs") == summary.get("passed_runs") == 21
        and summary.get("failed_runs") == 0
        and summary.get("families") == 7
        and summary.get("provider_drift_events") == 0
        and summary.get("deterministic_drift_events") == 0
        and summary.get("recovery_failures") == 0
        and summary.get("p50_ms") <= contract["performance_budget"]["p50_max_ms"]
        and summary.get("p95_ms") <= contract["performance_budget"]["p95_max_ms"]
        and summary.get("max_ms") <= contract["performance_budget"]["single_run_max_ms"]
    ):
        raise SystemExit("V0.269 repeated stability or performance evidence is incomplete.")
    if ledger.get("append_only") is not True or ledger.get("contract_sha256") != digest(contract):
        raise SystemExit("V0.269 initial failure ledger is missing or changed.")
    if recovery.get("passed") is not True or not all((recovery.get("checks") or {}).values()):
        raise SystemExit("V0.269 recovery contract is not passing.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.269 browser evidence is not passing or used human actions.")
    if not (
        browser_attempt_1.get("passed") is False
        and browser_errata.get("source_task_contract_unchanged") is True
        and browser_errata.get("product_code_unchanged") is True
        and browser_errata.get("failed_attempt_retained") == str(BROWSER_ATTEMPT_1.relative_to(PSM_ROOT))
    ):
        raise SystemExit("V0.269 browser harness failure or errata is not retained.")
    if docker.get("passed") is not True or docker.get("human_feedback_collected") is not False:
        raise SystemExit("V0.269 Docker evidence is not passing or used human feedback.")
    if docker_attempt_1.get("passed") is not False or docker_attempt_1.get("product_answer_evaluated") is not False:
        raise SystemExit("V0.269 Docker startup-race failure is not retained.")
    if any(contract["source_isolation"].values()) or any(contract["release_boundary"].values()):
        raise SystemExit("V0.269 source-isolation or release boundary is open.")

    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.269",
        "previous_formal_version": "psm_v0.268",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "repeated_task_stability_performance_and_recovery_gate_passed",
        "v0_269_task_stability_gate": {
            "decision": gate["decision"],
            "passed": True,
            **{key: summary[key] for key in ("selected_cases", "families", "runs", "passed_runs", "failed_runs", "provider_drift_events", "deterministic_drift_events", "recovery_failures", "p50_ms", "p95_ms", "max_ms", "total_ms")},
            "initial_failure_count": ledger["initial_failure_count"],
            "synthetic_only": True,
            "human_validation_claimed": False,
            "contract_sha256": digest(contract),
            "gate_sha256": digest(gate),
        },
        "next_stage": {
            "version": "PSM_V0.270",
            "objective": "建立普通聊天的多轮指代、约束累积与更正恢复基准：冻结多轮对话图，验证助手只使用用户历史和已交付回答，不让隐藏审计文本、错误助手陈述或过期约束覆盖当前意图。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_269_contract": "benchmarks/v0_269_task_stability_contract.json",
        "v0_269_report": "runtime/v0_269_task_stability_report.json",
        "v0_269_gate": "runtime/v0_269_task_stability_gate.json",
        "v0_269_recovery": "runtime/v0_269_recovery_report.json",
        "v0_269_initial_failure_ledger": "runtime/v0_269_task_stability_initial_failure_ledger.json",
        "v0_269_browser": "runtime/v0_269_stability_browser_regression/report.json",
        "v0_269_browser_attempt_1_failed": "runtime/v0_269_stability_browser_regression/report_attempt_1_failed.json",
        "v0_269_browser_harness_errata": "benchmarks/v0_269_browser_harness_errata.json",
        "v0_269_docker": "runtime/v0_269_task_stability_docker_boundary.json",
        "v0_269_docker_attempt_1_failed": "runtime/v0_269_task_stability_docker_attempt_1_failed.json",
        "v0_269_checkpoint": "runtime/v0_269_task_stability_checkpoint.json",
        "v0_269_promotion_manifest": "runtime/v0_269_task_stability_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.269_project_status.json",
    })
    write(TARGET, target)

    manifest = {
        "schema_version": "psm_v0_269_task_stability_promotion_manifest_v1",
        "version": "PSM_V0.269",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "task_stability": target["v0_269_task_stability_gate"],
        "evidence": {key: str(path.relative_to(PSM_ROOT)) for key, path in {"contract": CONTRACT, "report": REPORT, "gate": GATE, "recovery": RECOVERY, "initial_failure_ledger": LEDGER, "browser": BROWSER, "browser_attempt_1_failed": BROWSER_ATTEMPT_1, "browser_harness_errata": BROWSER_ERRATA, "docker": DOCKER, "docker_attempt_1_failed": DOCKER_ATTEMPT_1}.items()},
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint = read(CHECKPOINT)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.269",
        "target_promoted": True,
        "status": "v0_269_promoted_v0_270_multiturn_constraint_graph_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "freeze_v0_270_multiturn_constraint_contract",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.270")


if __name__ == "__main__":
    main()
