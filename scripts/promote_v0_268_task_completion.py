#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.267_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.268_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_268_task_completion_contract.json"
ERRATA = [
    PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata.json",
    PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata_2.json",
    PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata_3.json",
]
REPORT = RUNTIME / "v0_268_task_completion_report.json"
GATE = RUNTIME / "v0_268_task_completion_gate.json"
LEDGER = RUNTIME / "v0_268_task_completion_initial_failure_ledger.json"
BROWSER = RUNTIME / "v0_268_task_completion_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_268_task_completion_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_268_task_completion_checkpoint.json"
MANIFEST = RUNTIME / "v0_268_task_completion_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source = read(SOURCE)
    contract = read(CONTRACT)
    errata = [read(path) for path in ERRATA]
    report = read(REPORT)
    gate = read(GATE)
    ledger = read(LEDGER)
    browser = read(BROWSER)
    docker = read(DOCKER)

    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.268 task-completion gate is not passing.")
    summary = report.get("summary") or {}
    families = summary.get("families") or {}
    if not (
        report.get("passed") is True
        and summary.get("cases") == summary.get("passed") == 21
        and summary.get("failed") == 0
        and len(families) == 7
        and all(item.get("cases") == item.get("passed") == 3 for item in families.values())
        and summary.get("provider_failure_templates") == 0
        and summary.get("task_restatements_without_completion") == 0
        and summary.get("critical_safety_false_negatives") == 0
    ):
        raise SystemExit("V0.268 frozen task-completion evidence is incomplete.")
    if ledger.get("initial_failure_count") != 5 or ledger.get("append_only") is not True:
        raise SystemExit("V0.268 initial failure ledger is missing or changed.")
    if not (
        len(errata) == 3
        and all(item.get("source_contract_unchanged") is True for item in errata)
        and errata[1].get("applies_after") == ERRATA[0].name
        and errata[2].get("applies_after") == ERRATA[1].name
    ):
        raise SystemExit("V0.268 transparent errata chain is incomplete.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.268 browser evidence is not passing or used human actions.")
    if docker.get("passed") is not True or docker.get("human_feedback_collected") is not False:
        raise SystemExit("V0.268 Docker evidence is not passing or used human feedback.")
    if any(contract["release_boundary"].values()) or contract["source_isolation"]["evaluation_rows_used_for_training"] is not False:
        raise SystemExit("V0.268 source-isolation or release boundary is open.")

    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.268",
        "previous_formal_version": "psm_v0.267",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "ordinary_chat_task_completion_gate_passed_with_retained_initial_failures",
        "v0_268_task_completion_gate": {
            "decision": gate["decision"],
            "passed": True,
            "cases": summary["cases"],
            "cases_passed": summary["passed"],
            "families": len(families),
            "families_passed": sum(item["cases"] == item["passed"] == 3 for item in families.values()),
            "initial_failure_count": ledger["initial_failure_count"],
            "transparent_errata_count": len(errata),
            "provider_failure_templates": summary["provider_failure_templates"],
            "task_restatements_without_completion": summary["task_restatements_without_completion"],
            "critical_safety_false_negatives": summary["critical_safety_false_negatives"],
            "total_duration_ms": summary["total_duration_ms"],
            "synthetic_only": True,
            "human_validation_claimed": False,
            "contract_sha256": digest(contract),
            "errata_sha256": [digest(item) for item in errata],
            "gate_sha256": digest(gate),
        },
        "next_stage": {
            "version": "PSM_V0.269",
            "objective": "建立本地模型任务完成度的重复稳定性与性能预算：对冻结任务执行多轮重复回放，测量输出不变量、p50/p95 延迟、超时、取消、重试与降级恢复；任何失败模板、任务漂移或发布边界变化均阻止晋升。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_268_contract": "benchmarks/v0_268_task_completion_contract.json",
        "v0_268_contract_errata": [str(path.relative_to(PSM_ROOT)) for path in ERRATA],
        "v0_268_report": "runtime/v0_268_task_completion_report.json",
        "v0_268_gate": "runtime/v0_268_task_completion_gate.json",
        "v0_268_initial_failure_ledger": "runtime/v0_268_task_completion_initial_failure_ledger.json",
        "v0_268_browser": "runtime/v0_268_task_completion_browser_regression/report.json",
        "v0_268_docker": "runtime/v0_268_task_completion_docker_boundary.json",
        "v0_268_checkpoint": "runtime/v0_268_task_completion_checkpoint.json",
        "v0_268_promotion_manifest": "runtime/v0_268_task_completion_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.268_project_status.json",
    })
    write(TARGET, target)

    manifest = {
        "schema_version": "psm_v0_268_task_completion_promotion_manifest_v1",
        "version": "PSM_V0.268",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "task_completion": target["v0_268_task_completion_gate"],
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "contract_errata": [str(path.relative_to(PSM_ROOT)) for path in ERRATA],
            "report": str(REPORT.relative_to(PSM_ROOT)),
            "gate": str(GATE.relative_to(PSM_ROOT)),
            "initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
            "browser": str(BROWSER.relative_to(PSM_ROOT)),
            "docker": str(DOCKER.relative_to(PSM_ROOT)),
        },
        "release_boundary": contract["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)

    checkpoint = read(CHECKPOINT)
    checkpoint.update({
        "current_promoted_version": "PSM_V0.268",
        "target_promoted": True,
        "status": "v0_268_promoted_v0_269_stability_and_performance_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "freeze_v0_269_stability_and_performance_contract",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.269")


if __name__ == "__main__":
    main()
