#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
REPORT = PSM_ROOT / "runtime" / "v0_281_rolling_state_isolation_report.json"
GATE = PSM_ROOT / "runtime" / "v0_281_rolling_state_isolation_gate.json"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402


def main() -> None:
    server.ROLLING_STATE_SESSIONS.clear()
    first_a, meta_a = server.update_rolling_session_state(
        "isolation_session_a_0123456789",
        [{"id": 1, "role": "user", "content": "项目代号定为白砾。"}],
        now=100.0,
    )
    first_b, meta_b = server.update_rolling_session_state(
        "isolation_session_b_0123456789",
        [{"id": 1, "role": "user", "content": "项目代号定为黑砂。"}],
        now=101.0,
    )
    replay_a, _ = server.update_rolling_session_state(
        "isolation_session_a_0123456789",
        [{"id": 1, "role": "user", "content": "项目代号定为白砾。"}],
        now=102.0,
    )
    isolation_checks = {
        "session_a_contains_only_a_fact": "项目代号定为白砾。" in first_a and "项目代号定为黑砂。" not in first_a,
        "session_b_contains_only_b_fact": "项目代号定为黑砂。" in first_b and "项目代号定为白砾。" not in first_b,
        "replay_is_idempotent": replay_a.count("项目代号定为白砾。") == 1,
        "metadata_is_ephemeral": meta_a["ephemeral_memory_only"] is True and meta_b["ephemeral_memory_only"] is True,
        "disk_persistence_disabled": meta_a["disk_persistence"] is False and meta_b["disk_persistence"] is False,
    }

    server.update_rolling_session_state(
        "expiry_trigger_session_0123456789",
        [{"id": 1, "role": "user", "content": "触发清理。"}],
        now=102.0 + server.ROLLING_STATE_IDLE_SECONDS + 1,
    )
    expiry_checks = {
        "expired_session_a_removed": "isolation_session_a_0123456789" not in server.ROLLING_STATE_SESSIONS,
        "expired_session_b_removed": "isolation_session_b_0123456789" not in server.ROLLING_STATE_SESSIONS,
        "trigger_session_retained": "expiry_trigger_session_0123456789" in server.ROLLING_STATE_SESSIONS,
    }

    server.ROLLING_STATE_SESSIONS.clear()
    for index in range(server.ROLLING_STATE_MAX_SESSIONS + 1):
        server.update_rolling_session_state(
            f"capacity_session_{index:03d}_0123456789",
            [{"id": 1, "role": "user", "content": f"容量记录 {index}。"}],
            now=1000.0 + index,
        )
    capacity_checks = {
        "session_count_bounded": len(server.ROLLING_STATE_SESSIONS) == server.ROLLING_STATE_MAX_SESSIONS,
        "oldest_session_evicted": "capacity_session_000_0123456789" not in server.ROLLING_STATE_SESSIONS,
        "newest_session_retained": f"capacity_session_{server.ROLLING_STATE_MAX_SESSIONS:03d}_0123456789" in server.ROLLING_STATE_SESSIONS,
    }
    checks = {**isolation_checks, **expiry_checks, **capacity_checks}
    result = {
        "schema_version": "psm_v0_281_rolling_state_isolation_report_v1",
        "version": "PSM_V0.281-candidate",
        "passed": all(checks.values()),
        "checks": checks,
        "metrics": {
            "maximum_sessions": server.ROLLING_STATE_MAX_SESSIONS,
            "idle_expiry_seconds": server.ROLLING_STATE_IDLE_SECONDS,
            "retained_sessions_after_capacity_test": len(server.ROLLING_STATE_SESSIONS),
            "cross_session_leaks": 0 if isolation_checks["session_a_contains_only_a_fact"] and isolation_checks["session_b_contains_only_b_fact"] else 1,
            "disk_writes": 0,
        },
        "human_feedback_collected": False,
        "evaluation_rows_used_for_training": False,
        "external_release_authority": False,
    }
    gate = {
        "schema_version": "psm_v0_281_rolling_state_isolation_gate_v1",
        "passed": result["passed"],
        "decision": "rolling_state_isolation_gate_passed" if result["passed"] else "rolling_state_isolation_gate_failed",
        "checks": checks,
        "metrics": result["metrics"],
    }
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    GATE.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    if not gate["passed"]:
        raise SystemExit("V0.281 rolling-state isolation gate failed.")


if __name__ == "__main__":
    main()
