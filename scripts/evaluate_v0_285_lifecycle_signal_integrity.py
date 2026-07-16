#!/usr/bin/env python3
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from product_alpha_app import server


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_285_lifecycle_signal_integrity_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_285_lifecycle_signal_integrity_initial_failure_ledger.json"
REPORT = PSM_ROOT / "runtime" / "v0_285_lifecycle_signal_integrity_report.json"
GATE = PSM_ROOT / "runtime" / "v0_285_lifecycle_signal_integrity_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_285_lifecycle_signal_integrity_checkpoint.json"


def clear() -> None:
    server.ROLLING_STATE_SESSIONS.clear()
    server.ROLLING_STATE_TOMBSTONES.clear()


def seed(session_id: str, fact: str = "项目代号定为白砾。", now: float = 100.0) -> None:
    server.update_rolling_session_state(
        session_id,
        [{"id": 1, "role": "user", "content": fact}],
        now=now,
        client_server_instance_id=server.SERVER_INSTANCE_ID,
    )


def no_resurrection(event: str, *, stale_instance: bool = False) -> tuple[bool, dict]:
    clear()
    session_id = f"v285_final_{event}_session"
    seed(session_id)
    _, first = server.update_rolling_session_state(
        session_id,
        [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
        now=101.0,
        client_event="active" if stale_instance else event,
        client_server_instance_id="stale-server-instance" if stale_instance else server.SERVER_INSTANCE_ID,
    )
    statements, second = server.update_rolling_session_state(
        session_id,
        [{"id": 3, "role": "user", "content": "之前的项目代号是什么？"}],
        now=102.0,
        client_event="active",
        client_server_instance_id=server.SERVER_INSTANCE_ID,
    )
    passed = (
        first["continuity_status"]["memory_cleared"] is True
        and "项目代号定为白砾。" not in statements
        and second["continuity_status"]["memory_available"] is True
    )
    return passed, {
        "loss_state": first["continuity_status"]["state"],
        "memory_cleared": first["continuity_status"]["memory_cleared"],
        "old_fact_present_after_next_active": "项目代号定为白砾。" in statements,
    }


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    rows = []
    for case in contract["cases"]:
        family = case["family"]
        if family == "same_session_reset_no_resurrection":
            passed, evidence = no_resurrection("reset")
        elif family == "same_session_reload_no_resurrection":
            passed, evidence = no_resurrection("reload")
        elif family == "stale_instance_no_resurrection":
            passed, evidence = no_resurrection("restarted", stale_instance=True)
        elif family == "unknown_event_ignored":
            clear()
            session_id = "v285_final_unknown_event"
            seed(session_id)
            statements, metadata = server.update_rolling_session_state(
                session_id,
                [{"id": 2, "role": "user", "content": "继续。"}],
                now=101.0,
                client_event="restore_everything",
                client_server_instance_id=server.SERVER_INSTANCE_ID,
            )
            passed = metadata["continuity_status"]["state"] == "active" and "项目代号定为白砾。" in statements
            evidence = {"observed_state": metadata["continuity_status"]["state"]}
        elif family == "message_replay_idempotent":
            clear()
            session_id = "v285_final_replay_session"
            seed(session_id)
            statements, _ = server.update_rolling_session_state(
                session_id,
                [{"id": 1, "role": "user", "content": "项目代号改为红砂。"}],
                now=101.0,
                client_server_instance_id=server.SERVER_INSTANCE_ID,
            )
            passed = statements == ["项目代号定为白砾。"]
            evidence = {"retained_statements": len(statements), "replay_applied": not passed}
        elif family == "hash_tombstones_bounded":
            clear()
            session_ids = [f"v285_final_expiry_{index:03d}" for index in range(140)]
            for session_id in session_ids:
                seed(session_id, now=0.0)
            server.update_rolling_session_state(
                "v285_final_expiry_trigger",
                [{"id": 1, "role": "user", "content": "触发清理。"}],
                now=2000.0,
                client_server_instance_id=server.SERVER_INSTANCE_ID,
            )
            keys = list(server.ROLLING_STATE_TOMBSTONES)
            passed = len(keys) <= 128 and all(len(key) == 64 for key in keys) and not any(value in keys for value in session_ids)
            evidence = {"tombstones": len(keys), "raw_session_ids": sum(value in keys for value in session_ids)}
        elif family == "concurrent_session_isolation":
            clear()
            def write_one(index: int):
                session_id = f"v285_final_concurrent_{index:02d}"
                fact = f"项目代号定为并发{index:02d}。"
                seed(session_id, fact=fact)
                return session_id, fact
            with ThreadPoolExecutor(max_workers=8) as pool:
                pairs = list(pool.map(write_one, range(32)))
            isolated = sum(server.ROLLING_STATE_SESSIONS[session_id]["user_statements"] == [fact] for session_id, fact in pairs)
            passed = isolated == 32
            evidence = {"sessions": 32, "isolated": isolated}
        else:
            clear()
            before = {str(path): path.stat().st_mtime_ns for path in PSM_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
            seed("v285_final_disk_session")
            after = {str(path): path.stat().st_mtime_ns for path in PSM_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
            changed = [path for path in set(before) | set(after) if before.get(path) != after.get(path)]
            passed = not changed
            evidence = {"changed_files": changed}
        rows.append({"case_id": case["case_id"], "family": family, "passed": passed, "evidence": evidence})
    summary = {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "memory_resurrection_events": sum(
            row["family"].endswith("no_resurrection") and row["evidence"].get("old_fact_present_after_next_active") is True
            for row in rows
        ),
        "cross_session_leaks": 32 - next(row["evidence"]["isolated"] for row in rows if row["family"] == "concurrent_session_isolation"),
    }
    report = {
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_report_v1",
        "version": "PSM_V0.285-candidate",
        "synthetic_only": True,
        "baseline_passed": baseline["passed"],
        "baseline_failed": baseline["failed"],
        "summary": summary,
        "rows": rows,
    }
    checks = {
        "baseline_retained_at_five_of_eight": baseline["passed"] == 5 and baseline["failed"] == 3,
        "all_eight_cases_pass": summary["passed"] == 8 and summary["failed"] == 0,
        "zero_memory_resurrection": summary["memory_resurrection_events"] == 0,
        "zero_cross_session_leaks": summary["cross_session_leaks"] == 0,
        "zero_user_statement_disk_writes": next(row for row in rows if row["family"] == "zero_user_statement_disk_writes")["passed"],
        "external_release_closed": contract["requirements"]["external_release_authority"] is False,
    }
    gate = {
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_gate_v1",
        "decision": "lifecycle_signal_integrity_gate_passed" if all(checks.values()) else "lifecycle_signal_integrity_gate_failed",
        "passed": all(checks.values()),
        "checks": checks,
        "summary": summary,
    }
    checkpoint = {
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_checkpoint_v1",
        "source_version": "PSM_V0.284",
        "candidate_version": "PSM_V0.285",
        "status": "local_integrity_gate_passed" if gate["passed"] else "local_integrity_gate_failed",
        "requires_user_input": False,
        "next_action": "verify_v0_285_host_docker_integrity" if gate["passed"] else "repair_recorded_failures",
    }
    for path, value in ((REPORT, report), (GATE, gate), (CHECKPOINT, checkpoint)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report: {REPORT.relative_to(ROOT)}")
    print(f"passed: {summary['passed']}/{summary['cases']}")
    print(f"gate: {gate['decision']}")
    if not gate["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
