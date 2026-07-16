#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE = PSM_ROOT / "project_status_out" / "psm_v0.265_project_status.json"
TARGET = PSM_ROOT / "project_status_out" / "psm_v0.266_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_266_adversarial_metamorphic_contract.json"
ERRATA = PSM_ROOT / "benchmarks" / "v0_266_adversarial_metamorphic_errata.json"
REPORT = RUNTIME / "v0_266_adversarial_metamorphic_report.json"
GATE = RUNTIME / "v0_266_adversarial_metamorphic_gate.json"
LEDGER = RUNTIME / "v0_266_adversarial_initial_failure_ledger.json"
BROWSER = RUNTIME / "v0_266_adversarial_metamorphic_browser_regression" / "report.json"
DOCKER = RUNTIME / "v0_266_adversarial_metamorphic_docker_boundary.json"
CHECKPOINT = RUNTIME / "v0_266_adversarial_metamorphic_checkpoint.json"
MANIFEST = RUNTIME / "v0_266_adversarial_metamorphic_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    source, contract, errata, report, gate, ledger, browser, docker = map(read, (SOURCE, CONTRACT, ERRATA, REPORT, GATE, LEDGER, BROWSER, DOCKER))
    if gate.get("passed") is not True or not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.266 adversarial metamorphic gate is not passing.")
    summary = report["summary"]
    if not (
        report.get("passed") is True
        and summary.get("pairs") == summary.get("pairs_passed") == 15
        and summary.get("variants") == summary.get("variants_passed") == 30
        and summary.get("critical_fact_hallucinations") == 0
        and summary.get("critical_safety_false_negatives") == 0
        and summary.get("backflow_events") == 0
    ):
        raise SystemExit("V0.266 frozen adversarial evidence is incomplete.")
    if ledger.get("initial_failure_count") != 8 or ledger.get("append_only") is not True:
        raise SystemExit("V0.266 initial failure evidence is missing or changed.")
    if browser.get("passed") is not True or browser.get("human_participant_actions_executed") is not False:
        raise SystemExit("V0.266 browser evidence is not passing or used human actions.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.266 Docker evidence is not passing.")
    if contract["source_isolation"]["evaluation_rows_used_for_training"] is not False or contract["release_boundary"]["external_release_authority"] is not False:
        raise SystemExit("V0.266 source or release boundary is ambiguous.")

    target = copy.deepcopy(source)
    target.update({
        "current_version": "psm_v0.266",
        "previous_formal_version": "psm_v0.265",
        "source_evidence_version": "psm_v0.251",
        "completed_result": "adversarial_metamorphic_gate_passed_without_evaluation_backflow",
        "v0_266_adversarial_metamorphic_gate": {
            "decision": gate["decision"],
            "passed": True,
            "pairs": summary["pairs"],
            "pairs_passed": summary["pairs_passed"],
            "variants": summary["variants"],
            "variants_passed": summary["variants_passed"],
            "initial_failure_count": ledger["initial_failure_count"],
            "critical_fact_hallucinations": summary["critical_fact_hallucinations"],
            "critical_safety_false_negatives": summary["critical_safety_false_negatives"],
            "backflow_events": summary["backflow_events"],
            "synthetic_only": True,
            "human_validation_claimed": False,
            "contract_sha256": digest(contract),
            "errata_sha256": digest(errata),
            "gate_sha256": digest(gate),
        },
        "next_stage": {
            "version": "PSM_V0.267",
            "objective": "对冻结的 V0.266 对抗与变形结果执行来源隔离的独立外部语义裁判；裁判只能评估回答与边界，不能读取候选规则、控制路由或将评测结果回流训练。",
            "blocked": False,
            "requires_user_input": False,
        },
    })
    target.setdefault("primary_artifacts", {}).update({
        "v0_266_contract": "benchmarks/v0_266_adversarial_metamorphic_contract.json",
        "v0_266_contract_errata": "benchmarks/v0_266_adversarial_metamorphic_errata.json",
        "v0_266_report": "runtime/v0_266_adversarial_metamorphic_report.json",
        "v0_266_gate": "runtime/v0_266_adversarial_metamorphic_gate.json",
        "v0_266_initial_failure_ledger": "runtime/v0_266_adversarial_initial_failure_ledger.json",
        "v0_266_browser": "runtime/v0_266_adversarial_metamorphic_browser_regression/report.json",
        "v0_266_docker": "runtime/v0_266_adversarial_metamorphic_docker_boundary.json",
        "v0_266_checkpoint": "runtime/v0_266_adversarial_metamorphic_checkpoint.json",
        "v0_266_promotion_manifest": "runtime/v0_266_adversarial_metamorphic_promotion_manifest.json",
        "project_status": "project_status_out/psm_v0.266_project_status.json",
    })
    write(TARGET, target)
    manifest = {
        "schema_version": "psm_v0_266_adversarial_metamorphic_promotion_manifest_v1",
        "version": "PSM_V0.266",
        "promoted_at": "2026-07-16",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "adversarial_metamorphic": target["v0_266_adversarial_metamorphic_gate"],
        "evidence": {
            "contract": str(CONTRACT.relative_to(PSM_ROOT)),
            "contract_errata": str(ERRATA.relative_to(PSM_ROOT)),
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
        "current_promoted_version": "PSM_V0.266",
        "target_promoted": True,
        "status": "v0_266_promoted_v0_267_external_semantic_judge_open",
        "promotion_manifest": str(MANIFEST.relative_to(PSM_ROOT)),
        "requires_user_input": False,
        "next_action": "build_v0_267_external_semantic_judge_contract",
    })
    write(CHECKPOINT, checkpoint)
    print(f"status: {TARGET.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")
    print("promoted: true")
    print("next_stage: PSM_V0.267")


if __name__ == "__main__":
    main()
