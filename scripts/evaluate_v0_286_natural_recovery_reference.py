#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from product_alpha_app import server


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_286_natural_recovery_reference_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_286_natural_recovery_reference_initial_failure_ledger.json"
REPORT = PSM_ROOT / "runtime" / "v0_286_natural_recovery_reference_report.json"
GATE = PSM_ROOT / "runtime" / "v0_286_natural_recovery_reference_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_286_natural_recovery_reference_checkpoint.json"


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    rows = []
    memory_loss_states = ("reset", "reload", "expired", "restarted")
    for case in contract["cases"]:
        detected = server.asks_unavailable_prior_state(case["text"])
        state_checks = []
        if case["should_trigger_recovery"]:
            for state in memory_loss_states:
                result = server.run_chat_turn(
                    [{"role": "user", "content": case["text"]}],
                    "review",
                    rolling_state_metadata={
                        "continuity_status": server.continuity_status(state, memory_available=False),
                        "ephemeral_memory_only": True,
                        "disk_persistence": False,
                    },
                )
                answer = result["chat"]["assistant_message"]
                state_checks.append({
                    "state": state,
                    "boundary_visible": "不能确认" in answer,
                    "archived_fact_fabricated": "白砾" in answer,
                })
        passed = detected is case["should_trigger_recovery"] and all(
            item["boundary_visible"] and not item["archived_fact_fabricated"] for item in state_checks
        )
        rows.append({
            "case_id": case["case_id"],
            "should_trigger_recovery": case["should_trigger_recovery"],
            "observed_trigger": detected,
            "state_checks": state_checks,
            "passed": passed,
        })
    positives = [row for row in rows if row["should_trigger_recovery"]]
    negatives = [row for row in rows if not row["should_trigger_recovery"]]
    summary = {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "positive_recall": sum(row["observed_trigger"] for row in positives) / len(positives),
        "negative_specificity": sum(not row["observed_trigger"] for row in negatives) / len(negatives),
        "memory_loss_answer_checks": sum(len(row["state_checks"]) for row in rows),
        "archived_fact_fabrications": sum(
            item["archived_fact_fabricated"] for row in rows for item in row["state_checks"]
        ),
    }
    report = {
        "schema_version": "psm_v0_286_natural_recovery_reference_report_v1",
        "version": "PSM_V0.286-candidate",
        "synthetic_only": True,
        "baseline_passed": baseline["passed"],
        "baseline_failed": baseline["failed"],
        "summary": summary,
        "rows": rows,
    }
    checks = {
        "baseline_retained_at_four_of_sixteen": baseline["passed"] == 4 and baseline["failed"] == 12,
        "all_sixteen_detection_cases_pass": summary["passed"] == 16 and summary["failed"] == 0,
        "positive_recall_exact": summary["positive_recall"] == 1.0,
        "negative_specificity_exact": summary["negative_specificity"] == 1.0,
        "all_forty_eight_loss_answers_checked": summary["memory_loss_answer_checks"] == 48,
        "zero_archived_fact_fabrication": summary["archived_fact_fabrications"] == 0,
        "external_release_closed": contract["requirements"]["external_release_authority"] is False,
    }
    gate = {
        "schema_version": "psm_v0_286_natural_recovery_reference_gate_v1",
        "decision": "natural_recovery_reference_gate_passed" if all(checks.values()) else "natural_recovery_reference_gate_failed",
        "passed": all(checks.values()),
        "checks": checks,
        "summary": summary,
    }
    checkpoint = {
        "schema_version": "psm_v0_286_natural_recovery_reference_checkpoint_v1",
        "source_version": "PSM_V0.285",
        "candidate_version": "PSM_V0.286",
        "status": "natural_reference_gate_passed" if gate["passed"] else "natural_reference_gate_failed",
        "requires_user_input": False,
        "next_action": "promote_v0_286_natural_recovery_reference" if gate["passed"] else "repair_recorded_failures",
    }
    for path, value in ((REPORT, report), (GATE, gate), (CHECKPOINT, checkpoint)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report: {REPORT.relative_to(ROOT)}")
    print(f"passed: {summary['passed']}/{summary['cases']}")
    print(f"loss_answer_checks: {summary['memory_loss_answer_checks']}")
    print(f"gate: {gate['decision']}")
    if not gate["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
