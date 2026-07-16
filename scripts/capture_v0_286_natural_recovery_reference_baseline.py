#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from product_alpha_app import server


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_286_natural_recovery_reference_contract.json"
OUT = PSM_ROOT / "runtime" / "v0_286_natural_recovery_reference_initial_failure_ledger.json"


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = []
    for case in contract["cases"]:
        observed = server.asks_unavailable_prior_state(case["text"])
        rows.append({
            "case_id": case["case_id"],
            "should_trigger_recovery": case["should_trigger_recovery"],
            "observed_trigger": observed,
            "passed": observed is case["should_trigger_recovery"],
        })
    report = {
        "schema_version": "psm_v0_286_natural_recovery_reference_initial_failure_ledger_v1",
        "source_version": "PSM_V0.285",
        "captured_before_v0_286_repair": True,
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "positive_true": sum(row["observed_trigger"] for row in rows if row["should_trigger_recovery"]),
        "negative_false": sum(not row["observed_trigger"] for row in rows if not row["should_trigger_recovery"]),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"baseline: {OUT.relative_to(ROOT)}")
    print(f"passed: {report['passed']}/{report['cases']}")
    print(f"positive_recall: {report['positive_true']}/{contract['positive_cases']}")
    print(f"negative_specificity: {report['negative_false']}/{contract['negative_cases']}")


if __name__ == "__main__":
    main()
