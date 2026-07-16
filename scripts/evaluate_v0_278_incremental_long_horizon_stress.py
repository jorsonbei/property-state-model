#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_278_incremental_long_horizon_stress_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_278_incremental_long_horizon_stress_report.json"
GATE = PSM_ROOT / "runtime" / "v0_278_incremental_long_horizon_stress_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_278_incremental_long_horizon_stress_checkpoint.json"
RETAINED = PSM_ROOT / "runtime" / "v0_277_external_state_compression_promotion_manifest.json"
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


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


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
        public_capsule = generation.get("state_capsule") or {}
        normalized_messages = server.normalize_chat_messages(case["messages"])
        capsule = build_conversation_state_capsule(normalized_messages)
        continuity = result["chat"]["state_continuity"]
        boundaries = result["task_state_graph"]["boundaries"]
        capsule_text = "\n".join(capsule.get("user_statements") or [])
        baseline_capsule = build_conversation_state_capsule(case["messages"][-24:])
        baseline_text = "\n".join(baseline_capsule.get("user_statements") or [])
        missing_answer = [marker for marker in case["required_answer_markers"] if marker not in answer]
        forbidden_answer = [marker for marker in case["forbidden_answer_markers"] if marker in answer]
        missing_capsule = [marker for marker in case["required_capsule_markers"] if marker not in capsule_text]
        baseline_missing = [marker for marker in case["required_capsule_markers"] if marker not in baseline_text]
        checks = {
            "required_answer_markers_present": not missing_answer,
            "forbidden_answer_markers_absent": not forbidden_answer,
            "input_within_stress_band": case["minimum_input_messages"] <= len(case["messages"]) <= case["maximum_input_messages"],
            "full_history_retained": continuity["history_messages"] == len(case["messages"]),
            "compression_applied": capsule.get("compression_applied") is True,
            "capsule_source_count_is_long": capsule.get("source_user_statements", 0) > 20,
            "capsule_within_retained_limit": capsule.get("retained_user_statements", 1000) <= case["maximum_retained_user_statements"],
            "required_capsule_markers_retained": not missing_capsule,
            "public_capsule_contains_no_raw_user_statements": "user_statements" not in public_capsule,
            "window_only_baseline_misses_remote_state": bool(baseline_missing),
            "topic_switch_state_matches": capsule.get("topic_switch_applied") is case["topic_switch_expected"],
            "generation_completed": generation.get("status") == "success",
            "quality_audit_passed": result["chat"]["quality_audit"]["status"] == "pass",
            "sigma_plus_delivery_passed": result["sigma_plus_delivery"]["passed"] is True,
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
            "missing_answer_markers": missing_answer,
            "forbidden_answer_markers": forbidden_answer,
            "missing_capsule_markers": missing_capsule,
            "window_baseline_missing_capsule_markers": baseline_missing,
            "generation": {key: generation.get(key) for key in ("status", "provider", "model", "error", "state_capsule")},
            "input_messages": len(case["messages"]),
            "history_messages": continuity["history_messages"],
            "duration_ms": duration_ms,
        }
        rows.append(row)
        print(json.dumps({"case": f"{index}/{len(contract['cases'])}", "id": case["id"], "passed": row["passed"], "messages": len(case["messages"]), "duration_ms": duration_ms}, ensure_ascii=False), flush=True)

    families = {
        family: {
            "cases": sum(row["family"] == family for row in rows),
            "passed": sum(row["family"] == family and row["passed"] for row in rows),
        }
        for family in contract["evaluation"]["families"]
    }
    durations = [row["duration_ms"] for row in rows]
    summary = {
        "cases": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "message_levels": sorted({row["input_messages"] for row in rows}),
        "minimum_messages": min(row["input_messages"] for row in rows),
        "maximum_messages": max(row["input_messages"] for row in rows),
        "stale_state_violations": sum(bool(row["forbidden_answer_markers"]) for row in rows),
        "compression_missing": sum(not row["checks"]["compression_applied"] for row in rows),
        "capsule_recovery_failures": sum(bool(row["missing_capsule_markers"]) for row in rows),
        "window_baseline_failures": sum(bool(row["window_baseline_missing_capsule_markers"]) for row in rows),
        "total_duration_ms": sum(durations),
        "p50_duration_ms": percentile(durations, 0.5),
        "p95_duration_ms": percentile(durations, 0.95),
        "maximum_duration_ms": max(durations),
        "families": families,
    }
    report = {
        "schema_version": "psm_v0_278_incremental_long_horizon_stress_report_v1",
        "version": "PSM_V0.278-candidate",
        "contract_sha256": digest(contract),
        "passed": summary["failed"] == 0,
        "summary": summary,
        "rows": rows,
    }
    write(REPORT, report)
    checks = {
        "case_count_matches": summary["cases"] == contract["evaluation"]["frozen_case_count"],
        "all_cases_pass": summary["failed"] == 0,
        "all_families_pass": all(
            item["cases"] == item["passed"] == contract["evaluation"]["cases_per_family"]
            for item in families.values()
        ),
        "both_stress_levels_present": summary["message_levels"] == contract["evaluation"]["message_levels"] == [81, 119],
        "history_stays_within_product_limit": summary["maximum_messages"] <= contract["evaluation"]["maximum_input_messages"],
        "compression_applied_for_all": summary["compression_missing"] == 0,
        "capsule_recovery_failures_zero": summary["capsule_recovery_failures"] == 0,
        "historical_window_baseline_fails_all": summary["window_baseline_failures"] == summary["cases"],
        "stale_state_violations_zero": summary["stale_state_violations"] == 0,
        "total_duration_within_limit": summary["total_duration_ms"] <= contract["evaluation"]["maximum_total_duration_ms"],
        "p95_duration_within_limit": summary["p95_duration_ms"] <= contract["evaluation"]["maximum_p95_duration_ms"],
        "retained_v0_277_promotion": retained.get("promoted") is True,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_278_incremental_long_horizon_stress_gate_v1",
        "version": "PSM_V0.278-candidate",
        "passed": all(checks.values()),
        "decision": "incremental_long_horizon_stress_gate_passed" if all(checks.values()) else "incremental_long_horizon_stress_gate_failed",
        "checks": checks,
        "metrics": summary,
        "release_boundary": contract["release_boundary"],
    }
    write(GATE, gate)
    write(CHECKPOINT, {
        "schema_version": "psm_v0_278_incremental_long_horizon_stress_checkpoint_v1",
        "current_promoted_version": "PSM_V0.277",
        "target_version": "PSM_V0.278",
        "target_promoted": False,
        "passed": gate["passed"],
        "status": gate["decision"],
        "requires_user_input": False,
        "next_action": "verify_v0_278_host_docker_boundary" if gate["passed"] else "repair_recorded_stress_failures",
    })
    print(json.dumps({"passed": gate["passed"], **{key: summary[key] for key in ("cases", "passed", "failed", "message_levels", "compression_missing", "capsule_recovery_failures", "window_baseline_failures", "total_duration_ms", "p95_duration_ms")}}, ensure_ascii=False))
    if not gate["passed"]:
        raise SystemExit(f"V0.278 stress gate failed: {[row['case_id'] for row in rows if not row['passed']]}")


if __name__ == "__main__":
    main()
