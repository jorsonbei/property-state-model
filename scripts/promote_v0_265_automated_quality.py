#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.264_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.265_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_265_automated_quality_contract.json"
REPORT = RUNTIME / "v0_265_automated_quality_report.json"
GATE = RUNTIME / "v0_265_automated_quality_gate.json"
BROWSER = RUNTIME / "v0_265_automated_quality_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_265_automated_quality_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_265_automated_quality_checkpoint.json"
MANIFEST = RUNTIME / "v0_265_automated_quality_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, report, gate, browser, docker = map(read, (SOURCE, CONTRACT, REPORT, GATE, BROWSER, DOCKER))
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.265 automated quality gate is not passing.")
    summary = report["summary"]
    if report.get("passed") is not True or not (
        summary.get("cases") == 30 and summary.get("passed") == 30 and summary.get("failed") == 0
        and summary.get("simulated_personas") == 12
        and summary.get("simulated_persona_proxy_passed") == 12
        and summary.get("critical_fact_hallucinations") == 0
        and summary.get("critical_safety_false_negatives") == 0
    ):
        raise SystemExit("V0.265 frozen scenario evidence is incomplete.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.265 browser evidence is not passing or used human actions.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.265 Docker evidence is not passing.")
    if contract["provenance"]["synthetic_only"] is not True or contract["release_boundary"]["human_validation_claimed"] is not False:
        raise SystemExit("V0.265 evidence provenance is ambiguous.")
    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.265", "previous_formal_version": "psm_v0.264",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "automated_internal_quality_gate_passed_without_human_validation",
        "v0_265_automated_quality_gate": {
            "decision": gate["decision"], "passed": True,
            "cases": summary["cases"], "case_passed": summary["passed"], "failed": summary["failed"],
            "critical_fact_hallucinations": summary["critical_fact_hallucinations"],
            "critical_safety_false_negatives": summary["critical_safety_false_negatives"],
            "simulated_personas": summary["simulated_personas"],
            "simulated_persona_proxy_passed": summary["simulated_persona_proxy_passed"],
            "synthetic_only": True, "human_participants_used": False,
            "human_feedback_collected": False, "human_validation_claimed": False,
            "contract_sha256": digest(contract), "gate_sha256": digest(gate),
        },
        "next_stage": {
            "version": "PSM_V0.266",
            "objective": "构建来源隔离的合成对抗案例族与变形不变量；保持开发集和评测集分离，禁止角色模拟冒充真人及评测结果回流训练，并继续关闭公开发布和规则替换权限。",
            "blocked": False, "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_265_contract": "benchmarks/v0_265_automated_quality_contract.json",
        "v0_265_report": "runtime/v0_265_automated_quality_report.json",
        "v0_265_gate": "runtime/v0_265_automated_quality_gate.json",
        "v0_265_browser": "runtime/v0_265_automated_quality_browser_regression/report.json",
        "v0_265_docker": "runtime/v0_265_automated_quality_docker_boundary.json",
        "v0_265_checkpoint": "runtime/v0_265_automated_quality_checkpoint.json",
        "v0_265_promotion_manifest": "runtime/v0_265_automated_quality_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.265_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_265_automated_quality_promotion_manifest_v1",
        "version": "PSM_V0.265", "promoted_at": "2026-07-16", "promoted": True,
        "decision": gate["decision"], "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "automated_quality": target["v0_265_automated_quality_gate"],
        "evidence": {"contract": str(CONTRACT.relative_to(PSM_ROOT)), "report": str(REPORT.relative_to(PSM_ROOT)), "gate": str(GATE.relative_to(PSM_ROOT)), "browser": str(BROWSER.relative_to(PSM_ROOT)), "docker": str(DOCKER.relative_to(PSM_ROOT))},
        "release_boundary": contract["release_boundary"], "next_stage": target["next_stage"],
    }
    write(MANIFEST, manifest)
    checkpoint = read(CHECKPOINT)
    checkpoint.update({"current_promoted_version": "PSM_V0.265", "target_promoted": True, "status": "v0_265_promoted_v0_266_automated_failure_discovery_open", "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)), "requires_user_input": False})
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.266")


if __name__ == "__main__":
    main()
