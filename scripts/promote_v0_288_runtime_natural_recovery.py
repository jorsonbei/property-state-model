#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.287_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.288_project_status.json"
BOUNDARY = RUNTIME / "v0_288_host_docker_natural_recovery_boundary.json"
CHECKPOINT = RUNTIME / "v0_288_runtime_natural_recovery_checkpoint.json"
MANIFEST = RUNTIME / "v0_288_runtime_natural_recovery_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    boundary = read(BOUNDARY)
    checks = {
        "source_version_is_v0_287": source.get("current_version") == "psm_v0.287",
        "runtime_boundary_passed": boundary.get("passed") is True and all(boundary.get("checks", {}).values()),
        "host_all_sixteen_pass": boundary.get("host", {}).get("positive_passed") == 12 and boundary.get("host", {}).get("negative_passed") == 4,
        "docker_all_sixteen_pass": boundary.get("docker", {}).get("positive_passed") == 12 and boundary.get("docker", {}).get("negative_passed") == 4,
        "sentinel_disk_writes_zero": boundary.get("sentinel_disk_hits") == [],
        "persistent_memory_closed": boundary["checks"].get("persistent_memory_closed") is True,
        "external_release_closed": boundary["checks"].get("external_release_closed") is True,
    }
    if not all(checks.values()):
        raise SystemExit(f"V0.288 promotion failed: {[key for key, value in checks.items() if not value]}")
    runtime_gate = {
        "decision": "host_docker_natural_recovery_runtime_gate_passed",
        "passed": True,
        "checks": checks,
        "host_cases": 16,
        "host_passed": 16,
        "docker_cases": 16,
        "docker_passed": 16,
        "natural_reference_cases_per_runtime": 12,
        "new_task_controls_per_runtime": 4,
        "sentinel_disk_writes": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.288",
        "previous_formal_version": "psm_v0.287",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "host_docker_natural_recovery_runtime_gate_passed",
        "v0_288_runtime_natural_recovery_gate": runtime_gate,
        "next_stage": {
            "version": "PSM_V0.289",
            "objective": "执行桌面与手机真实浏览器的自然指代恢复、连续性状态提示、正常新任务交互和布局回归。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_288_runtime_boundary": str(BOUNDARY.relative_to(PSM_ROOT)),
        "v0_288_checkpoint": str(CHECKPOINT.relative_to(PSM_ROOT)),
        "v0_288_promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "project_status": "project_status_out/psm_v0.288_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_288_runtime_natural_recovery_promotion_manifest_v1",
        "version": "PSM_V0.288",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": runtime_gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "runtime_natural_recovery": runtime_gate,
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
        "schema_version": "psm_v0_288_runtime_natural_recovery_checkpoint_v1",
        "current_promoted_version": "PSM_V0.288",
        "target_promoted": True,
        "status": "v0_288_promoted_v0_289_browser_natural_recovery_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "run_v0_289_browser_natural_recovery_regression",
        "required_decision": "无。",
    }
    write(MANIFEST, manifest)
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.289")


if __name__ == "__main__":
    main()
