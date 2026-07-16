#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_280_rolling_state_handoff_contract.json"
OUT = PSM_ROOT / "runtime" / "v0_280_window_truncation_initial_failure_ledger.json"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit("V0.280 initial baseline ledger already exists; refusing to overwrite append-only evidence.")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = []
    for case in contract["cases"]:
        result = server.run_chat_turn(case["messages"], "review")
        answer = result["chat"]["assistant_message"]
        missing = [marker for marker in case["required_answer_markers"] if marker not in answer]
        forbidden = [marker for marker in case["forbidden_answer_markers"] if marker in answer]
        rows.append({
            "case_id": case["id"],
            "family": case["family"],
            "passed": not missing and not forbidden,
            "answer": answer,
            "missing_answer_markers": missing,
            "forbidden_answer_markers": forbidden,
            "full_input_messages": len(case["messages"]),
            "retained_history_messages": result["chat"]["state_continuity"]["history_messages"],
        })
    failed = [row for row in rows if not row["passed"]]
    ledger = {
        "schema_version": "psm_v0_280_window_truncation_initial_failure_ledger_v1",
        "version": "PSM_V0.280-candidate",
        "contract_sha256": digest(contract),
        "captured_before_rolling_state_handoff_implementation": True,
        "append_only": True,
        "window_messages": contract["evaluation"]["window_messages"],
        "cases": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(rows), "passed": ledger["passed"], "failed": ledger["failed"], "failed_ids": [row["case_id"] for row in failed]}, ensure_ascii=False))
    if ledger["failed"] < contract["evaluation"]["minimum_initial_baseline_failures"]:
        raise SystemExit("V0.280 baseline did not reproduce enough truncation failures.")


if __name__ == "__main__":
    main()
