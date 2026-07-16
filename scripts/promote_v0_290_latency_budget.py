#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.289_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.290_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_290_latency_budget_contract.json"
REPORT = RUNTIME / "v0_290_latency_budget_report.json"
GATE = RUNTIME / "v0_290_latency_budget_gate.json"
CHECKPOINT = RUNTIME / "v0_290_latency_budget_checkpoint.json"
MANIFEST = RUNTIME / "v0_290_latency_budget_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    contract = read(CONTRACT)
    report = read(REPORT)
    gate = read(GATE)
    checks = {
        "source_version_is_v0_289": source.get("current_version") == "psm_v0.289",
        "contract_frozen_and_synthetic": contract.get("frozen") is True and contract.get("synthetic_only") is True,
        "latency_report_passed": report.get("passed") is True and all(report.get("checks", {}).values()),
        "latency_gate_passed": gate.get("passed") is True and all(gate.get("checks", {}).values()),
        "host_categories_pass": all(item.get("passed") for item in gate.get("host", {}).values()),
        "docker_categories_pass": all(item.get("passed") for item in gate.get("docker", {}).values()),
        "fallbacks_zero": report["checks"].get("fallbacks_zero") is True,
        "external_release_closed": report.get("external_release_authority") is False,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.290 promotion failed: {[key for key, value in checks.items() if not value]}")
    latency_gate = {
        "decision": "latency_budget_gate_passed",
        "passed": True,
        "checks": checks,
        "host": gate["host"],
        "docker": gate["docker"],
        "fallbacks": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.290",
        "previous_formal_version": "psm_v0.289",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "latency_budget_gate_passed",
        "v0_290_latency_budget_gate": latency_gate,
        "next_stage": {
            "version": "PSM_V0.291",
            "objective": "根据实测本地模型延迟建立更严格的用户体验目标，并评估取消请求、分段状态与流式输出的最小实现。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_290_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "v0_290_report": str(REPORT.relative_to(PSM_ROOT)),
        "v0_290_gate": str(GATE.relative_to(PSM_ROOT)),
        "v0_290_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_290_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.290_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_290_latency_budget_promotion_manifest_v1",
        "version": "PSM_V0.290",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": latency_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "latency_budget": latency_gate,
        "release_boundary": {
            "human_validation_claimed": False,
            "persistent_conversation_memory_enabled": False,
            "public_service_allowed": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "next_stage": target["next_stage"],
    }
    checkpoint = {
        "schema_version": "psm_v0_290_latency_budget_checkpoint_v1",
        "current_promoted_version": "PSM_V0.290",
        "target_promoted": True,
        "status": "v0_290_promoted_v0_291_interaction_latency_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_291_interaction_latency_contract",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.291")


if __name__ == "__main__":
    main()
