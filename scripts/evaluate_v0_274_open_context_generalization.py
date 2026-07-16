#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_274_open_context_generalization_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_274_open_context_generalization_report.json"
GATE = PSM_ROOT / "runtime" / "v0_274_open_context_generalization_gate.json"
LEDGER = PSM_ROOT / "runtime" / "v0_274_open_context_initial_failure_ledger.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_274_open_context_generalization_checkpoint.json"
RETAINED = PSM_ROOT / "runtime" / "v0_273_external_long_context_promotion_manifest.json"
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


def main() -> None:
    contract = read(CONTRACT)
    retained = read(RETAINED)
    rows = []
    for index, case in enumerate(contract["cases"], start=1):
        started = time.perf_counter()
        result = server.run_chat_turn(case["messages"], "review")
        duration_ms = round((time.perf_counter() - started) * 1000)
        answer = result["chat"]["assistant_message"]
        generation = result["chat"]["generation"]
        boundaries = result["task_state_graph"]["boundaries"]
        continuity = result["chat"]["state_continuity"]
        missing = [marker for marker in case.get("required_all", []) if marker not in answer]
        forbidden = [marker for marker in case.get("forbidden", []) if marker in answer]
        nonempty_lines = [line for line in answer.splitlines() if line.strip()]
        capsule = generation.get("state_capsule") or {}
        checks = {
            "required_markers_present": not missing,
            "stale_or_forbidden_state_absent": not forbidden,
            "maximum_line_constraint_met": len(nonempty_lines) <= case.get("max_nonempty_lines", 100000),
            "exact_line_constraint_met": len(nonempty_lines) == case.get("exact_nonempty_lines", len(nonempty_lines)),
            "generation_completed": generation.get("status") == "success",
            "local_generation_or_state_resolution": generation.get("provider") in {"ollama", "deterministic"},
            "user_authoritative_state_capsule_present": capsule.get("user_authoritative") is True,
            "state_capsule_has_remote_history": capsule.get("active_user_statements", 0) >= 5,
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
            "missing_required_markers": missing,
            "forbidden_found": forbidden,
            "generation": {key: generation.get(key) for key in ("status", "provider", "model", "error", "state_capsule")},
            "history_messages": continuity["history_messages"],
            "duration_ms": duration_ms,
        }
        rows.append(row)
        print(json.dumps({"case": f"{index}/{len(contract['cases'])}", "id": case["id"], "passed": row["passed"], "provider": generation.get("provider"), "duration_ms": duration_ms}, ensure_ascii=False), flush=True)

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
        "stale_state_violations": sum(bool(row["forbidden_found"]) for row in rows),
        "capsule_missing": sum(not row["checks"]["user_authoritative_state_capsule_present"] for row in rows),
        "total_duration_ms": sum(row["duration_ms"] for row in rows),
        "families": families,
    }
    report = {
        "schema_version": "psm_v0_274_open_context_generalization_report_v1",
        "version": "PSM_V0.274-candidate",
        "contract_sha256": digest(contract),
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
                "missing_required_markers": row["missing_required_markers"],
                "forbidden_found": row["forbidden_found"],
                "answer": row["answer"],
                "generation": row["generation"],
            }
            for row in rows
            if not row["passed"]
        ]
        write(LEDGER, {
            "schema_version": "psm_v0_274_open_context_initial_failure_ledger_v1",
            "version": "PSM_V0.274-candidate",
            "frozen_at": contract["frozen_at"],
            "contract_sha256": digest(contract),
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
        "state_capsule_present_for_all": summary["capsule_missing"] == 0,
        "stale_state_violations_zero": summary["stale_state_violations"] == contract["evaluation"]["maximum_stale_state_violations"],
        "initial_failure_ledger_retained": ledger.get("contract_sha256") == digest(contract) and ledger.get("append_only") is True,
        "retained_v0_273_promotion": retained.get("promoted") is True,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_274_open_context_generalization_gate_v1",
        "version": "PSM_V0.274-candidate",
        "passed": all(checks.values()),
        "decision": "open_context_generalization_gate_passed" if all(checks.values()) else "open_context_generalization_gate_failed",
        "checks": checks,
        "metrics": summary,
        "initial_failure_count": ledger["initial_failure_count"],
        "release_boundary": contract["release_boundary"],
    }
    write(GATE, gate)
    write(CHECKPOINT, {
        "schema_version": "psm_v0_274_open_context_generalization_checkpoint_v1",
        "current_promoted_version": "PSM_V0.273",
        "target_version": "PSM_V0.274",
        "target_promoted": False,
        "passed": gate["passed"],
        "status": gate["decision"],
        "requires_user_input": False,
        "next_action": "run_v0_274_browser_and_docker_boundaries" if gate["passed"] else "repair_recorded_open_context_failures",
    })
    print(json.dumps({"passed": gate["passed"], "initial_failures": ledger["initial_failure_count"], **{key: summary[key] for key in ("cases", "passed", "failed", "stale_state_violations", "capsule_missing", "total_duration_ms")}}, ensure_ascii=False))
    if not gate["passed"]:
        raise SystemExit(f"V0.274 open-context gate failed: {[row['case_id'] for row in rows if not row['passed']]}")


if __name__ == "__main__":
    main()
