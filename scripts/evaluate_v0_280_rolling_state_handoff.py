#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_280_rolling_state_handoff_contract.json"
LEDGER = PSM_ROOT / "runtime" / "v0_280_window_truncation_initial_failure_ledger.json"
REPORT = PSM_ROOT / "runtime" / "v0_280_rolling_state_handoff_report.json"
GATE = PSM_ROOT / "runtime" / "v0_280_rolling_state_handoff_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_280_rolling_state_handoff_checkpoint.json"
RETAINED = PSM_ROOT / "runtime" / "v0_279_external_incremental_stress_promotion_manifest.json"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402
from psm_v0.chat_prompt import build_conversation_state_capsule  # noqa: E402


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
    ledger = read(LEDGER)
    retained = read(RETAINED)
    rows = []
    for index, case in enumerate(contract["cases"], start=1):
        full_capsule = build_conversation_state_capsule(case["messages"])
        rolling_user_statements = full_capsule["user_statements"]
        started = time.perf_counter()
        result = server.run_chat_turn(
            case["messages"],
            "review",
            rolling_user_statements=rolling_user_statements,
            rolling_state_metadata={
                "enabled": True,
                "ephemeral_memory_only": True,
                "disk_persistence": False,
                "retained_user_statements": len(rolling_user_statements),
                "maximum_retained_user_statements": 20,
                "topic_switch_applied": full_capsule["topic_switch_applied"],
                "sha256": full_capsule["sha256"],
            },
        )
        duration_ms = round((time.perf_counter() - started) * 1000)
        answer = result["chat"]["assistant_message"]
        continuity = result["chat"]["state_continuity"]
        public_capsule = result["chat"]["generation"].get("state_capsule") or {}
        rolling_text = "\n".join(rolling_user_statements)
        missing_answer = [marker for marker in case["required_answer_markers"] if marker not in answer]
        forbidden_answer = [marker for marker in case["forbidden_answer_markers"] if marker in answer]
        missing_rolling = [marker for marker in case["required_rolling_markers"] if marker not in rolling_text]
        checks = {
            "required_answer_markers_present": not missing_answer,
            "forbidden_answer_markers_absent": not forbidden_answer,
            "full_input_exceeds_window": len(case["messages"]) > contract["evaluation"]["window_messages"],
            "window_is_bounded_to_120": continuity["history_messages"] == contract["evaluation"]["window_messages"],
            "effective_context_crosses_window": continuity["effective_context_messages"] > continuity["history_messages"],
            "rolling_state_applied": continuity["rolling_state_applied"] is True,
            "rolling_state_within_limit": len(rolling_user_statements) <= contract["evaluation"]["maximum_rolling_user_statements"],
            "required_rolling_markers_retained": not missing_rolling,
            "topic_switch_state_matches": full_capsule["topic_switch_applied"] is case["topic_switch_expected"],
            "public_capsule_contains_no_raw_user_statements": "user_statements" not in public_capsule,
            "ephemeral_memory_only": continuity["rolling_state"].get("ephemeral_memory_only") is True,
            "disk_persistence_disabled": continuity["rolling_state"].get("disk_persistence") is False,
            "generation_completed": result["chat"]["generation"].get("status") == "success",
            "quality_audit_passed": result["chat"]["quality_audit"]["status"] == "pass",
            "sigma_plus_delivery_passed": result["sigma_plus_delivery"]["passed"] is True,
        }
        row = {
            "case_id": case["id"],
            "family": case["family"],
            "passed": all(checks.values()),
            "checks": checks,
            "answer": answer,
            "missing_answer_markers": missing_answer,
            "forbidden_answer_markers": forbidden_answer,
            "missing_rolling_markers": missing_rolling,
            "full_input_messages": len(case["messages"]),
            "window_messages": continuity["history_messages"],
            "effective_context_messages": continuity["effective_context_messages"],
            "rolling_user_statements": len(rolling_user_statements),
            "duration_ms": duration_ms,
        }
        rows.append(row)
        print(json.dumps({"case": f"{index}/{len(contract['cases'])}", "id": case["id"], "passed": row["passed"], "duration_ms": duration_ms}, ensure_ascii=False), flush=True)

    summary = {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "initial_baseline_failures": ledger["failed"],
        "rolling_state_missing": sum(not row["checks"]["rolling_state_applied"] for row in rows),
        "rolling_recovery_failures": sum(bool(row["missing_rolling_markers"]) for row in rows),
        "stale_state_violations": sum(bool(row["forbidden_answer_markers"]) for row in rows),
        "total_duration_ms": sum(row["duration_ms"] for row in rows),
        "maximum_effective_context_messages": max(row["effective_context_messages"] for row in rows),
    }
    report = {
        "schema_version": "psm_v0_280_rolling_state_handoff_report_v1",
        "version": "PSM_V0.280-candidate",
        "contract_sha256": digest(contract),
        "passed": summary["failed"] == 0,
        "summary": summary,
        "rows": rows,
    }
    write(REPORT, report)
    checks = {
        "case_count_matches": summary["cases"] == contract["evaluation"]["frozen_case_count"],
        "all_cases_pass": summary["failed"] == 0,
        "initial_baseline_failures_retained": (
            ledger.get("append_only") is True
            and ledger.get("captured_before_rolling_state_handoff_implementation") is True
            and ledger.get("failed", 0) >= contract["evaluation"]["minimum_initial_baseline_failures"]
        ),
        "rolling_state_applied_for_all": summary["rolling_state_missing"] == 0,
        "rolling_recovery_failures_zero": summary["rolling_recovery_failures"] == 0,
        "stale_state_violations_zero": summary["stale_state_violations"] == 0,
        "retained_v0_279_promotion": retained.get("promoted") is True,
        "disk_persistence_disabled": contract["privacy"]["disk_persistence_of_user_statements_allowed"] is False,
        "ephemeral_memory_bounded": (
            contract["privacy"]["ephemeral_memory_only"] is True
            and contract["privacy"]["maximum_session_idle_seconds"] == server.ROLLING_STATE_IDLE_SECONDS
            and contract["privacy"]["maximum_sessions"] == server.ROLLING_STATE_MAX_SESSIONS
        ),
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_280_rolling_state_handoff_gate_v1",
        "version": "PSM_V0.280-candidate",
        "passed": all(checks.values()),
        "decision": "rolling_state_handoff_gate_passed" if all(checks.values()) else "rolling_state_handoff_gate_failed",
        "checks": checks,
        "metrics": summary,
        "privacy": contract["privacy"],
        "release_boundary": contract["release_boundary"],
    }
    write(GATE, gate)
    write(CHECKPOINT, {
        "schema_version": "psm_v0_280_rolling_state_handoff_checkpoint_v1",
        "current_promoted_version": "PSM_V0.279",
        "target_version": "PSM_V0.280",
        "target_promoted": False,
        "passed": gate["passed"],
        "status": gate["decision"],
        "requires_user_input": False,
        "next_action": "verify_v0_280_host_docker_boundary" if gate["passed"] else "repair_recorded_rolling_state_failures",
    })
    print(json.dumps({"passed": gate["passed"], **summary}, ensure_ascii=False))
    if not gate["passed"]:
        raise SystemExit(f"V0.280 rolling-state gate failed: {[row['case_id'] for row in rows if not row['passed']]}")


if __name__ == "__main__":
    main()
