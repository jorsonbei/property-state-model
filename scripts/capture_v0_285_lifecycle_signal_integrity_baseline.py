#!/usr/bin/env python3
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from product_alpha_app import server


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_285_lifecycle_signal_integrity_contract.json"
OUT = PSM_ROOT / "runtime" / "v0_285_lifecycle_signal_integrity_initial_failure_ledger.json"


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


def resurrection(event: str, stale_instance: bool = False) -> bool:
    clear()
    session_id = f"v285_{event}_session_abcdef"
    seed(session_id)
    server.update_rolling_session_state(
        session_id,
        [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
        now=101.0,
        client_event="active" if stale_instance else event,
        client_server_instance_id="stale-server-instance" if stale_instance else server.SERVER_INSTANCE_ID,
    )
    statements, metadata = server.update_rolling_session_state(
        session_id,
        [{"id": 3, "role": "user", "content": "之前的项目代号是什么？"}],
        now=102.0,
        client_event="active",
        client_server_instance_id=server.SERVER_INSTANCE_ID,
    )
    return "项目代号定为白砾。" in statements and metadata["continuity_status"]["memory_available"]


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = []
    for case in contract["cases"]:
        family = case["family"]
        if family == "same_session_reset_no_resurrection":
            passed = not resurrection("reset")
            detail = "memory_resurrected" if not passed else "cleared"
        elif family == "same_session_reload_no_resurrection":
            passed = not resurrection("reload")
            detail = "memory_resurrected" if not passed else "cleared"
        elif family == "stale_instance_no_resurrection":
            passed = not resurrection("restarted", stale_instance=True)
            detail = "memory_resurrected" if not passed else "cleared"
        elif family == "unknown_event_ignored":
            clear()
            session_id = "v285_unknown_event_session"
            seed(session_id)
            statements, metadata = server.update_rolling_session_state(
                session_id,
                [{"id": 2, "role": "user", "content": "继续。"}],
                now=101.0,
                client_event="restore_everything",
                client_server_instance_id=server.SERVER_INSTANCE_ID,
            )
            passed = metadata["continuity_status"]["state"] == "active" and "项目代号定为白砾。" in statements
            detail = metadata["continuity_status"]["state"]
        elif family == "message_replay_idempotent":
            clear()
            session_id = "v285_replay_session_abcd"
            seed(session_id)
            statements, _ = server.update_rolling_session_state(
                session_id,
                [{"id": 1, "role": "user", "content": "项目代号改为红砂。"}],
                now=101.0,
                client_server_instance_id=server.SERVER_INSTANCE_ID,
            )
            passed = statements == ["项目代号定为白砾。"]
            detail = "replay_ignored" if passed else "replay_applied"
        elif family == "hash_tombstones_bounded":
            clear()
            session_ids = [f"v285_expiry_session_{index:03d}" for index in range(140)]
            for session_id in session_ids:
                seed(session_id, now=0.0)
            server.update_rolling_session_state(
                "v285_expiry_trigger_session",
                [{"id": 1, "role": "user", "content": "触发清理。"}],
                now=2000.0,
                client_server_instance_id=server.SERVER_INSTANCE_ID,
            )
            keys = list(server.ROLLING_STATE_TOMBSTONES)
            passed = len(keys) <= 128 and not any(session_id in keys for session_id in session_ids) and all(len(key) == 64 for key in keys)
            detail = f"tombstones={len(keys)}"
        elif family == "concurrent_session_isolation":
            clear()
            def write_one(index: int):
                session_id = f"v285_concurrent_session_{index:02d}"
                fact = f"项目代号定为并发{index:02d}。"
                seed(session_id, fact=fact)
                return session_id, fact
            with ThreadPoolExecutor(max_workers=8) as pool:
                pairs = list(pool.map(write_one, range(32)))
            passed = all(server.ROLLING_STATE_SESSIONS[session_id]["user_statements"] == [fact] for session_id, fact in pairs)
            detail = f"isolated={sum(server.ROLLING_STATE_SESSIONS[session_id]['user_statements'] == [fact] for session_id, fact in pairs)}"
        else:
            clear()
            before = {str(path): path.stat().st_mtime_ns for path in PSM_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
            seed("v285_disk_write_session")
            after = {str(path): path.stat().st_mtime_ns for path in PSM_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
            changed = [path for path in set(before) | set(after) if before.get(path) != after.get(path)]
            passed = not changed
            detail = f"changed={len(changed)}"
        rows.append({"case_id": case["case_id"], "family": family, "passed": passed, "detail": detail})
    report = {
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_initial_failure_ledger_v1",
        "source_version": "PSM_V0.284",
        "captured_before_v0_285_repair": True,
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"baseline: {OUT.relative_to(ROOT)}")
    print(f"passed: {report['passed']}/{report['cases']}")
    print(f"failed: {report['failed']}")


if __name__ == "__main__":
    main()
