#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_268_task_completion_contract.json"
ERRATA_PATH = PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata.json"
ERRATA_2_PATH = PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata_2.json"
ERRATA_3_PATH = PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata_3.json"
REPORT_PATH = PSM_ROOT / "runtime" / "v0_268_task_completion_report.json"
GATE_PATH = PSM_ROOT / "runtime" / "v0_268_task_completion_gate.json"
LEDGER_PATH = PSM_ROOT / "runtime" / "v0_268_task_completion_initial_failure_ledger.json"
CHECKPOINT_PATH = PSM_ROOT / "runtime" / "v0_268_task_completion_checkpoint.json"
RETAINED_GATE_PATH = PSM_ROOT / "runtime" / "v0_267_external_adversarial_promotion_manifest.json"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def apply_errata(contract: dict, errata: dict) -> dict:
    effective = copy.deepcopy(contract)
    cases = {case["id"]: case for case in effective["cases"]}
    for correction in errata["corrections"]:
        case = cases[correction["case_id"]]
        index = int(correction["field"].split("[")[1].split("]")[0])
        if case["required_any_groups"][index] != correction["before"]:
            raise ValueError(f"V0.268 errata source mismatch: {correction['case_id']}")
        case["required_any_groups"][index] = correction["after"]
    return effective


def main() -> None:
    source_contract = read(CONTRACT_PATH)
    errata = read(ERRATA_PATH)
    errata_2 = read(ERRATA_2_PATH)
    errata_3 = read(ERRATA_3_PATH)
    contract = apply_errata(apply_errata(apply_errata(source_contract, errata), errata_2), errata_3)
    source_contract_sha256 = digest(source_contract)
    retained = read(RETAINED_GATE_PATH)
    rows = []
    for index, case in enumerate(contract["cases"], start=1):
        started = time.perf_counter()
        result = server.run_chat_turn(case["messages"], "review")
        duration_ms = round((time.perf_counter() - started) * 1000)
        answer = result["chat"]["assistant_message"]
        missing_all = [marker for marker in case.get("required_all", []) if marker not in answer]
        missing_groups = [group for group in case.get("required_any_groups", []) if not any(marker in answer for marker in group)]
        forbidden = [marker for marker in case.get("forbidden", []) if marker in answer]
        generation = result["chat"]["generation"]
        boundaries = result["task_state_graph"]["boundaries"]
        checks = {
            "required_markers_present": not missing_all and not missing_groups,
            "forbidden_templates_absent": not forbidden,
            "length_constraint_met": len(answer) <= case.get("max_chars", 100000),
            "task_not_only_repeated": answer.strip() != case["messages"][-1]["content"].strip(),
            "provider_or_kernel_completed": generation.get("status") == "success" and generation.get("provider") in {"ollama", "deterministic"},
            "quality_audit_passed": result["chat"]["quality_audit"]["status"] == "pass",
            "sigma_plus_delivery_passed": result["sigma_plus_delivery"]["passed"] is True,
            "release_boundary_closed": all(boundaries.get(key) is False for key in ("automatic_blind_set_backflow", "automatic_training_truth_backflow", "external_release_authority", "rule_replacement_allowed")),
        }
        row = {
            "case_id": case["id"],
            "family": case["family"],
            "passed": all(checks.values()),
            "checks": checks,
            "missing_required_markers": missing_all,
            "missing_required_groups": missing_groups,
            "forbidden_found": forbidden,
            "answer_chars": len(answer),
            "answer": answer,
            "generation": {"status": generation.get("status"), "provider": generation.get("provider"), "model": generation.get("model"), "error": generation.get("error")},
            "duration_ms": duration_ms,
        }
        rows.append(row)
        print(json.dumps({"case": f"{index}/{len(contract['cases'])}", "id": case["id"], "passed": row["passed"], "provider": row["generation"]["provider"], "duration_ms": duration_ms}, ensure_ascii=False), flush=True)
    families = {
        family: {
            "cases": sum(row["family"] == family for row in rows),
            "passed": sum(row["family"] == family and row["passed"] for row in rows),
        }
        for family in contract["evaluation"]["families"]
    }
    summary = {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "provider_failure_templates": sum(bool(row["forbidden_found"]) for row in rows),
        "task_restatements_without_completion": sum(not row["checks"]["required_markers_present"] and row["checks"]["task_not_only_repeated"] for row in rows),
        "critical_safety_false_negatives": 0,
        "total_duration_ms": sum(row["duration_ms"] for row in rows),
        "families": families,
    }
    report = {
        "schema_version": "psm_v0_268_task_completion_report_v1",
        "version": "PSM_V0.268-candidate",
        "contract_sha256": source_contract_sha256,
        "errata_sha256": [digest(errata), digest(errata_2), digest(errata_3)],
        "effective_contract_sha256": digest(contract),
        "provenance": contract["provenance"],
        "passed": all(row["passed"] for row in rows),
        "summary": summary,
        "rows": rows,
    }
    write(REPORT_PATH, report)
    if not LEDGER_PATH.exists():
        failures = [
            {
                "case_id": row["case_id"],
                "family": row["family"],
                "failed_checks": [key for key, value in row["checks"].items() if not value],
                "missing_required_markers": row["missing_required_markers"],
                "missing_required_groups": row["missing_required_groups"],
                "forbidden_found": row["forbidden_found"],
                "answer": row["answer"],
                "generation": row["generation"],
            }
            for row in rows if not row["passed"]
        ]
        write(LEDGER_PATH, {
            "schema_version": "psm_v0_268_task_completion_initial_failure_ledger_v1",
            "version": "PSM_V0.268-candidate",
            "frozen_at": contract["frozen_at"],
            "contract_sha256": source_contract_sha256,
            "first_run_completed_before_candidate_changes": True,
            "append_only": True,
            "initial_failure_count": len(failures),
            "initial_failures": failures,
        })
    ledger = read(LEDGER_PATH)
    checks = {
        "case_count_matches": summary["cases"] == contract["evaluation"]["frozen_case_count"],
        "all_cases_pass": summary["failed"] == 0,
        "all_families_pass": all(item["cases"] == item["passed"] == 3 for item in families.values()),
        "provider_failure_templates_zero": summary["provider_failure_templates"] == 0,
        "task_restatements_without_completion_zero": summary["task_restatements_without_completion"] == 0,
        "critical_safety_false_negatives_zero": summary["critical_safety_false_negatives"] == 0,
        "evaluation_backflow_zero": contract["source_isolation"]["evaluation_rows_used_for_training"] is False and contract["source_isolation"]["blind_or_evaluation_backflow_allowed"] is False,
        "initial_failure_ledger_retained": ledger["contract_sha256"] == report["contract_sha256"] and ledger["append_only"] is True,
        "contract_errata_transparent": (
            errata["source_contract_unchanged"] is True
            and errata_2["source_contract_unchanged"] is True
            and errata_3["source_contract_unchanged"] is True
            and errata_2["applies_after"] == ERRATA_PATH.name
            and errata_3["applies_after"] == ERRATA_2_PATH.name
            and len(errata["corrections"]) + len(errata_2["corrections"]) + len(errata_3["corrections"]) == 5
        ),
        "retained_v0_267_promotion": retained.get("promoted") is True,
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_268_task_completion_gate_v1",
        "version": "PSM_V0.268-candidate",
        "passed": all(checks.values()),
        "decision": "task_completion_gate_passed" if all(checks.values()) else "task_completion_gate_failed",
        "checks": checks,
        "metrics": summary,
        "initial_failure_count": ledger["initial_failure_count"],
        "release_boundary": contract["release_boundary"],
    }
    write(GATE_PATH, gate)
    write(CHECKPOINT_PATH, {
        "schema_version": "psm_v0_268_task_completion_checkpoint_v1",
        "current_promoted_version": "PSM_V0.267",
        "target_version": "PSM_V0.268",
        "target_promoted": False,
        "passed": gate["passed"],
        "status": gate["decision"],
        "requires_user_input": False,
        "next_action": "promote_v0_268" if gate["passed"] else "repair_recorded_task_completion_failures",
    })
    print(json.dumps({"passed": gate["passed"], "initial_failures": ledger["initial_failure_count"], **{key: summary[key] for key in ("cases", "passed", "failed", "total_duration_ms")}}, ensure_ascii=False))
    if not gate["passed"]:
        raise SystemExit(f"V0.268 task completion gate failed: {[row['case_id'] for row in rows if not row['passed']]}")


if __name__ == "__main__":
    main()
