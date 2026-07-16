#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from product_alpha_app import server


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_283_restart_recovery_contract.json"
OUT = PSM_ROOT / "runtime" / "v0_283_restart_recovery_initial_failure_ledger.json"


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = []
    for index, case in enumerate(contract["cases"], start=1):
        server.ROLLING_STATE_SESSIONS.clear()
        session_id = f"baseline_session_{index:02d}_abcdef"
        server.update_rolling_session_state(
            session_id,
            [{"id": 1, "role": "user", "content": "项目代号定为白砾。"}],
            now=100.0,
        )
        now = 1901.0 if case["event"] == "expired" else 101.0
        _, metadata = server.update_rolling_session_state(
            session_id,
            [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
            now=now,
        )
        observed = (metadata.get("continuity_status") or {}).get("state")
        rows.append({
            "case_id": case["case_id"],
            "expected_state": case["expected_state"],
            "observed_state": observed,
            "passed": observed == case["expected_state"],
        })
    report = {
        "schema_version": "psm_v0_283_restart_recovery_initial_failure_ledger_v1",
        "source_version": "PSM_V0.282",
        "captured_before_v0_283_implementation": True,
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"baseline: {OUT.relative_to(ROOT)}")
    print(f"passed: {report['passed']}/{report['cases']}")


if __name__ == "__main__":
    main()
