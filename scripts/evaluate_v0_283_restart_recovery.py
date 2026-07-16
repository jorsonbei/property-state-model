#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from product_alpha_app import server


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_283_restart_recovery_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_283_restart_recovery_initial_failure_ledger.json"
REPORT = PSM_ROOT / "runtime" / "v0_283_restart_recovery_report.json"
GATE = PSM_ROOT / "runtime" / "v0_283_restart_recovery_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_283_restart_recovery_checkpoint.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_snapshot() -> dict[str, int]:
    ignored = {REPORT, GATE, CHECKPOINT}
    return {
        str(path.relative_to(PSM_ROOT)): path.stat().st_mtime_ns
        for path in PSM_ROOT.rglob("*")
        if path.is_file() and path not in ignored and "__pycache__" not in path.parts
    }


def run_case(case: dict) -> dict:
    server.ROLLING_STATE_SESSIONS.clear()
    server.ROLLING_STATE_TOMBSTONES.clear()
    event = case["event"]
    session_id = f"v283_{case['case_id'].lower()}_session_abcdef"
    instance_id = server.SERVER_INSTANCE_ID
    if event in {"active", "expired"}:
        server.update_rolling_session_state(
            session_id,
            [{"id": 1, "role": "user", "content": "项目代号定为白砾。"}],
            now=100.0,
            client_server_instance_id=instance_id,
        )
    request_event = event if event in {"reset", "reload"} else "active"
    request_instance = "previous-server-instance" if event == "restarted" else instance_id
    now = 1902.0 if event == "expired" else 101.0
    statements, metadata = server.update_rolling_session_state(
        session_id,
        [{"id": 2, "role": "user", "content": "之前的项目代号是什么？只回答已知事实。"}],
        now=now,
        client_event=request_event,
        client_server_instance_id=request_instance,
    )
    result = server.run_chat_turn(
        [{"id": 2, "role": "user", "content": "之前的项目代号是什么？只回答已知事实。"}],
        "review",
        rolling_user_statements=statements,
        rolling_state_metadata=metadata,
    )
    status = result["chat"]["state_continuity"]["continuity_status"]
    answer = result["chat"]["assistant_message"]
    expects_memory = event == "active"
    checks = {
        "state_exact": status["state"] == case["expected_state"],
        "memory_availability_exact": status["memory_available"] is expects_memory,
        "recovery_flag_exact": status["recovery_required"] is (not expects_memory),
        "recovery_action_exact": status["recovery_action"] == ("none" if expects_memory else "restate_context"),
        "answer_boundary_exact": answer == "白砾" if expects_memory else ("白砾" not in answer and "不能确认" in answer),
        "raw_conversation_not_persisted": status["raw_conversation_persisted"] is False,
        "external_release_closed": result["release_boundary"]["external_user_trial_allowed"] is False,
    }
    return {
        "case_id": case["case_id"],
        "event": event,
        "observed_state": status["state"],
        "answer_class": "archived_fact" if answer == "白砾" else "recovery_boundary",
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    contract = read(CONTRACT)
    baseline = read(BASELINE)
    before = file_snapshot()
    rows = [run_case(case) for case in contract["cases"]]
    after = file_snapshot()
    changed_files = sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )
    summary = {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "states_observed": sorted({row["observed_state"] for row in rows}),
        "fabricated_archived_facts": sum(
            row["event"] != "active" and row["answer_class"] == "archived_fact" for row in rows
        ),
        "project_files_changed_during_evaluation": changed_files,
    }
    report = {
        "schema_version": "psm_v0_283_restart_recovery_report_v1",
        "version": "PSM_V0.283-candidate",
        "synthetic_only": True,
        "baseline_passed": baseline["passed"],
        "baseline_failed": baseline["failed"],
        "summary": summary,
        "rows": rows,
    }
    required_states = set(contract["requirements"]["states_distinguishable"])
    checks = {
        "baseline_retained_at_zero_of_five": baseline["passed"] == 0 and baseline["failed"] == 5,
        "all_five_cases_pass": summary["passed"] == 5 and summary["failed"] == 0,
        "all_states_distinguishable": set(summary["states_observed"]) == required_states,
        "zero_fabricated_archived_facts": summary["fabricated_archived_facts"] == 0,
        "zero_project_file_writes_during_evaluation": not changed_files,
        "raw_conversation_disk_persistence_disabled": all(
            row["checks"]["raw_conversation_not_persisted"] for row in rows
        ),
        "external_release_closed": all(row["checks"]["external_release_closed"] for row in rows),
    }
    gate = {
        "schema_version": "psm_v0_283_restart_recovery_gate_v1",
        "decision": "restart_recovery_gate_passed" if all(checks.values()) else "restart_recovery_gate_failed",
        "passed": all(checks.values()),
        "checks": checks,
        "summary": summary,
    }
    checkpoint = {
        "schema_version": "psm_v0_283_restart_recovery_checkpoint_v1",
        "source_version": "PSM_V0.282",
        "candidate_version": "PSM_V0.283",
        "status": "local_gate_passed_runtime_restart_verification_open" if gate["passed"] else "local_gate_failed",
        "requires_user_input": False,
        "next_action": "verify_v0_283_host_docker_controlled_restart" if gate["passed"] else "repair_recorded_failures",
    }
    write(REPORT, report)
    write(GATE, gate)
    write(CHECKPOINT, checkpoint)
    print(f"report: {REPORT.relative_to(ROOT)}")
    print(f"passed: {summary['passed']}/{summary['cases']}")
    print(f"gate: {gate['decision']}")
    if not gate["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
