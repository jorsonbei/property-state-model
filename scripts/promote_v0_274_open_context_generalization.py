#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.273_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.274_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_274_open_context_generalization_contract.json"
REPORT = RUNTIME / "v0_274_open_context_generalization_report.json"
GATE = RUNTIME / "v0_274_open_context_generalization_gate.json"
LEDGER = RUNTIME / "v0_274_open_context_initial_failure_ledger.json"
BROWSER = RUNTIME / "v0_274_open_context_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_274_open_context_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_274_open_context_generalization_checkpoint.json"
MANIFEST = RUNTIME / "v0_274_open_context_generalization_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, report, gate, ledger, browser, docker = map(
        read,
        (SOURCE, CONTRACT, REPORT, GATE, LEDGER, BROWSER, DOCKER),
    )
    summary = report.get("summary") or {}
    checks = {
        "source_version_is_v0_273": source.get("current_version") == "psm_v0.273",
        "gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "all_ten_cases_passed": report.get("passed") is True and summary.get("cases") == summary.get("passed") == 10,
        "all_five_families_passed": len(summary.get("families") or {}) == 5 and all(item["cases"] == item["passed"] == 2 for item in summary["families"].values()),
        "state_capsule_present_for_all": summary.get("capsule_missing") == 0,
        "stale_state_violations_zero": summary.get("stale_state_violations") == 0,
        "initial_failures_retained": ledger.get("initial_failure_count") == 10 and ledger.get("append_only") is True and ledger.get("contract_sha256") == digest(contract),
        "browser_passed": browser.get("passed") is True and all(browser.get("checks", {}).values()),
        "docker_passed": docker.get("passed") is True and all(docker.get("checks", {}).values()),
        "human_feedback_zero": browser.get("human_feedback_collected") is False and docker.get("human_feedback_collected") is False,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.274 promotion failed: {[key for key, value in checks.items() if not value]}")

    open_context_gate = {
        "decision": gate["decision"],
        "passed": True,
        "cases": summary["cases"],
        "cases_passed": summary["passed"],
        "families": len(summary["families"]),
        "initial_failure_count": ledger["initial_failure_count"],
        "state_capsule_missing": summary["capsule_missing"],
        "stale_state_violations": summary["stale_state_violations"],
        "total_duration_ms": summary["total_duration_ms"],
        "synthetic_only": True,
        "human_validation_claimed": False,
        "evaluation_rows_used_for_training": False,
        "contract_sha256": digest(contract),
        "gate_sha256": digest(gate),
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.274",
        "previous_formal_version": "psm_v0.273",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "open_context_user_authoritative_state_capsule_gate_passed_after_retained_failures",
        "v0_274_open_context_generalization_gate": open_context_gate,
        "next_stage": {
            "version": "PSM_V0.275",
            "objective": "对冻结的 V0.274 开放式长对话回答执行来源隔离的独立外部语义评审，检查未见改写、远距事实、最新更正、未完成事项、约束继承和自然换题；只提交合成问答，不提交规则、私人资料或训练字段。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_274_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_274_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_274_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_274_initial_failure_ledger": str(LEDGER.relative_to(PSM_ROOT)),
        "v0_274_browser": str(BROWSER.relative_to(PSM_ROOT)),
        "v0_274_docker": str(DOCKER.relative_to(PSM_ROOT)),
        "v0_274_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_274_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.274_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_274_open_context_generalization_promotion_manifest_v1",
        "version": "PSM_V0.274",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "open_context_generalization": open_context_gate,
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
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
        "current_promoted_version": "PSM_V0.274",
        "target_promoted": True,
        "status": "v0_274_promoted_v0_275_external_open_context_review_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_275_external_open_context_review_package",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.275")


if __name__ == "__main__":
    main()
