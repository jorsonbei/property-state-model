#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_272_long_context_state_contract.json"
ERRATA = PSM_ROOT / "benchmarks" / "v0_272_long_context_state_errata.json"
REPORT = PSM_ROOT / "runtime" / "v0_272_long_context_state_report.json"
GATE = PSM_ROOT / "runtime" / "v0_272_long_context_state_gate.json"
LEDGER = PSM_ROOT / "runtime" / "v0_272_long_context_initial_failure_ledger.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_272_long_context_state_checkpoint.json"
RETAINED_MANIFEST = PSM_ROOT / "runtime" / "v0_271_external_multiturn_promotion_manifest.json"
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
    effective = json.loads(json.dumps(contract, ensure_ascii=False))
    cases = {case["id"]: case for case in effective["cases"]}
    for correction in errata["corrections"]:
        case = cases[correction["case_id"]]
        if case.get(correction["field"]) != correction["before"]:
            raise ValueError(f"V0.272 errata source mismatch: {correction['case_id']}:{correction['field']}")
        case[correction["field"]] = correction["after"]
    return effective


def main() -> None:
    source_contract = read(CONTRACT)
    errata = read(ERRATA)
    contract = apply_errata(source_contract, errata)
    retained = read(RETAINED_MANIFEST)
    server.OLLAMA_BASE_URL = "http://127.0.0.1:1"
    rows = []
    for index, case in enumerate(contract["cases"], start=1):
        started = time.perf_counter()
        result = server.run_chat_turn(case["messages"], "review")
        duration_ms = round((time.perf_counter() - started) * 1000)
        answer = result["chat"]["assistant_message"]
        packet = result["packet"]
        generation = result["chat"]["generation"]
        continuity = result["chat"]["state_continuity"]
        boundaries = result["task_state_graph"]["boundaries"]
        missing = [marker for marker in case.get("required_all", []) if marker not in answer]
        forbidden = [marker for marker in case.get("forbidden", []) if marker in answer]
        nonempty_lines = [line for line in answer.splitlines() if line.strip()]
        checks = {
            "domain_matches": packet["domain"] == case["expected_domain"],
            "exact_answer_matches_when_frozen": "expected_exact" not in case or answer == case["expected_exact"],
            "required_markers_present": not missing,
            "stale_or_forbidden_state_absent": not forbidden,
            "line_constraint_met": len(nonempty_lines) <= case.get("max_nonempty_lines", 100000),
            "deterministic_generation_completed": generation.get("status") == "success" and generation.get("provider") == "deterministic",
            "quality_audit_passed": result["chat"]["quality_audit"]["status"] == "pass",
            "sigma_plus_delivery_passed": result["sigma_plus_delivery"]["passed"] is True,
            "long_history_retained": continuity["history_messages"] >= contract["evaluation"]["minimum_history_messages"],
            "assistant_history_excluded_from_state_audit": result["chat"]["audit_text"] == case["messages"][-1]["content"],
            "release_boundary_closed": all(
                boundaries.get(key) is False
                for key in (
                    "automatic_blind_set_backflow",
                    "automatic_training_truth_backflow",
                    "external_release_authority",
                    "rule_replacement_allowed",
                )
            ),
        }
        row = {
            "case_id": case["id"],
            "family": case["family"],
            "passed": all(checks.values()),
            "checks": checks,
            "answer": answer,
            "actual_domain": packet["domain"],
            "actual_risk": packet["omega"]["risk_level"],
            "missing_required_markers": missing,
            "forbidden_found": forbidden,
            "generation": {key: generation.get(key) for key in ("status", "provider", "model", "error")},
            "history_messages": continuity["history_messages"],
            "duration_ms": duration_ms,
        }
        rows.append(row)
        print(json.dumps({"case": f"{index}/{len(contract['cases'])}", "id": case["id"], "passed": row["passed"], "domain": row["actual_domain"], "duration_ms": duration_ms}, ensure_ascii=False), flush=True)

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
        "assistant_history_contamination": sum(not row["checks"]["assistant_history_excluded_from_state_audit"] for row in rows),
        "stale_state_violations": sum(bool(row["forbidden_found"]) for row in rows),
        "total_duration_ms": sum(row["duration_ms"] for row in rows),
        "families": families,
    }
    report = {
        "schema_version": "psm_v0_272_long_context_state_report_v1",
        "version": "PSM_V0.272-candidate",
        "contract_sha256": digest(source_contract),
        "errata_sha256": digest(errata),
        "effective_contract_sha256": digest(contract),
        "provenance": contract["provenance"],
        "provider_mode": contract["provider_mode"],
        "passed": summary["failed"] == 0,
        "summary": summary,
        "rows": rows,
    }
    write(REPORT, report)

    if not LEDGER.exists():
        failures = [
            {
                "case_id": row["case_id"],
                "family": row["family"],
                "failed_checks": [key for key, value in row["checks"].items() if not value],
                "actual_domain": row["actual_domain"],
                "actual_risk": row["actual_risk"],
                "missing_required_markers": row["missing_required_markers"],
                "forbidden_found": row["forbidden_found"],
                "answer": row["answer"],
                "generation": row["generation"],
            }
            for row in rows
            if not row["passed"]
        ]
        write(LEDGER, {
            "schema_version": "psm_v0_272_long_context_initial_failure_ledger_v1",
            "version": "PSM_V0.272-candidate",
            "frozen_at": contract["frozen_at"],
            "contract_sha256": digest(source_contract),
            "first_run_completed_before_candidate_changes": True,
            "append_only": True,
            "initial_failure_count": len(failures),
            "initial_failures": failures,
        })
    ledger = read(LEDGER)
    checks = {
        "case_count_matches": summary["cases"] == contract["evaluation"]["frozen_case_count"],
        "all_cases_pass": summary["failed"] == 0,
        "all_families_pass": all(
            item["cases"] == item["passed"] == contract["evaluation"]["cases_per_family"]
            for item in families.values()
        ),
        "assistant_history_contamination_zero": summary["assistant_history_contamination"] == contract["evaluation"]["maximum_assistant_history_contamination"],
        "stale_state_violations_zero": summary["stale_state_violations"] == contract["evaluation"]["maximum_stale_state_violations"],
        "initial_failure_ledger_retained": ledger.get("contract_sha256") == digest(source_contract) and ledger.get("append_only") is True,
        "contract_errata_transparent": errata.get("source_contract_unchanged") is True and len(errata.get("corrections") or []) == 1,
        "retained_v0_271_promotion": retained.get("promoted") is True,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_272_long_context_state_gate_v1",
        "version": "PSM_V0.272-candidate",
        "passed": all(checks.values()),
        "decision": "long_context_state_continuity_gate_passed" if all(checks.values()) else "long_context_state_continuity_gate_failed",
        "checks": checks,
        "metrics": summary,
        "initial_failure_count": ledger["initial_failure_count"],
        "transparent_errata_count": len(errata["corrections"]),
        "release_boundary": contract["release_boundary"],
    }
    write(GATE, gate)
    write(CHECKPOINT, {
        "schema_version": "psm_v0_272_long_context_state_checkpoint_v1",
        "current_promoted_version": "PSM_V0.271",
        "target_version": "PSM_V0.272",
        "target_promoted": False,
        "passed": gate["passed"],
        "status": gate["decision"],
        "requires_user_input": False,
        "next_action": "run_v0_272_browser_and_docker_boundaries" if gate["passed"] else "repair_recorded_long_context_failures",
    })
    print(json.dumps({"passed": gate["passed"], "initial_failures": ledger["initial_failure_count"], **{key: summary[key] for key in ("cases", "passed", "failed", "assistant_history_contamination", "stale_state_violations", "total_duration_ms")}}, ensure_ascii=False))
    if not gate["passed"]:
        raise SystemExit(f"V0.272 long-context gate failed: {[row['case_id'] for row in rows if not row['passed']]}")


if __name__ == "__main__":
    main()
