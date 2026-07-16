#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_269_task_stability_contract.json"
SOURCE_CONTRACT_PATH = PSM_ROOT / "benchmarks" / "v0_268_task_completion_contract.json"
ERRATA_PATHS = [
    PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata.json",
    PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata_2.json",
    PSM_ROOT / "benchmarks" / "v0_268_task_completion_errata_3.json",
]
REPORT_PATH = PSM_ROOT / "runtime" / "v0_269_task_stability_report.json"
GATE_PATH = PSM_ROOT / "runtime" / "v0_269_task_stability_gate.json"
RECOVERY_PATH = PSM_ROOT / "runtime" / "v0_269_recovery_report.json"
LEDGER_PATH = PSM_ROOT / "runtime" / "v0_269_task_stability_initial_failure_ledger.json"
CHECKPOINT_PATH = PSM_ROOT / "runtime" / "v0_269_task_stability_checkpoint.json"
RETAINED_MANIFEST = PSM_ROOT / "runtime" / "v0_268_task_completion_promotion_manifest.json"
APP_JS = PSM_ROOT / "product_alpha_app" / "static" / "app.js"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def apply_errata(contract: dict, errata: dict) -> dict:
    effective = copy.deepcopy(contract)
    cases = {case["id"]: case for case in effective["cases"]}
    for correction in errata["corrections"]:
        case = cases[correction["case_id"]]
        index = int(correction["field"].split("[")[1].split("]")[0])
        if case["required_any_groups"][index] != correction["before"]:
            raise ValueError(f"V0.269 inherited errata source mismatch: {correction['case_id']}")
        case["required_any_groups"][index] = correction["after"]
    return effective


def percentile(values: list[int], quantile: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * quantile) - 1)]


def evaluate_answer(case: dict, result: dict) -> tuple[dict, list[str], list[list[str]], list[str]]:
    answer = result["chat"]["assistant_message"]
    missing_all = [marker for marker in case.get("required_all", []) if marker not in answer]
    missing_groups = [group for group in case.get("required_any_groups", []) if not any(marker in answer for marker in group)]
    forbidden = [marker for marker in case.get("forbidden", []) if marker in answer]
    generation = result["chat"]["generation"]
    boundaries = result["task_state_graph"]["boundaries"]
    checks = {
        "required_markers_present": not missing_all and not missing_groups,
        "forbidden_outputs_absent": not forbidden,
        "length_constraint_met": len(answer) <= case.get("max_chars", 100000),
        "provider_or_kernel_completed": generation.get("status") == "success" and generation.get("provider") in {"ollama", "deterministic"},
        "quality_audit_passed": result["chat"]["quality_audit"]["status"] == "pass",
        "sigma_plus_delivery_passed": result["sigma_plus_delivery"]["passed"] is True,
        "release_boundary_closed": all(boundaries.get(key) is False for key in ("automatic_blind_set_backflow", "automatic_training_truth_backflow", "external_release_authority", "rule_replacement_allowed")),
    }
    return checks, missing_all, missing_groups, forbidden


def run_recovery_checks() -> dict:
    unavailable = {
        "status": "error",
        "answer": "",
        "provider": "ollama",
        "model": "offline-probe",
        "duration_ms": 1,
        "error": "synthetic provider unavailable",
        "reasoning_leak_removed": False,
    }
    empty = {**unavailable, "status": "empty", "error": "synthetic empty answer"}
    generic_prompt = [{"role": "user", "content": "用两点说明纸质书和电子书的区别。"}]
    kernel_prompt = [{"role": "user", "content": "这不是医疗诊断，只做词汇翻译：把“胸痛”翻译成英文。"}]
    with patch.object(server, "try_ollama_chat_generation", return_value=unavailable):
        unavailable_result = server.run_chat_turn(generic_prompt, "review")
        kernel_result = server.run_chat_turn(kernel_prompt, "review")
    with patch.object(server, "try_ollama_chat_generation", return_value=empty):
        empty_result = server.run_chat_turn(generic_prompt, "review")

    unavailable_answer = unavailable_result["chat"]["assistant_message"]
    empty_answer = empty_result["chat"]["assistant_message"]
    app_js = APP_JS.read_text(encoding="utf-8")
    checks = {
        "provider_unavailable_visible": unavailable_result["chat"]["generation"]["status"] == "degraded" and "没有返回有效内容" in unavailable_answer,
        "empty_provider_answer_visible": empty_result["chat"]["generation"]["status"] == "degraded" and "没有返回有效内容" in empty_answer,
        "deterministic_kernel_bypasses_failure": kernel_result["chat"]["generation"]["status"] == "success" and "chest pain" in kernel_result["chat"]["assistant_message"] and "没有返回有效内容" not in kernel_result["chat"]["assistant_message"],
        "cancel_uses_abort_controller": "new AbortController()" in app_js and 'controller.abort()' in app_js and 'request.reason = reason' in app_js,
        "timeout_aborts_delivery": "REQUEST_TIMEOUT_MS" in app_js and 'request.reason = "timeout"' in app_js and 'controller.abort()' in app_js,
        "retry_preserves_original_input": "state.lastFailed = { text, userMessageId, reason }" in app_js and "state.lastFailed?.text" in app_js and "retryLastTurn" in app_js,
        "external_release_closed_after_recovery": unavailable_result["task_state_graph"]["boundaries"]["external_release_authority"] is False and empty_result["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_269_recovery_report_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "provider_unavailable_generation": unavailable_result["chat"]["generation"],
        "empty_provider_generation": empty_result["chat"]["generation"],
        "kernel_generation": kernel_result["chat"]["generation"],
        "human_actions_executed": False,
        "human_feedback_collected": False,
    }
    write(RECOVERY_PATH, report)
    return report


def main() -> None:
    contract = read(CONTRACT_PATH)
    source = read(SOURCE_CONTRACT_PATH)
    for path in ERRATA_PATHS:
        source = apply_errata(source, read(path))
    cases_by_id = {case["id"]: case for case in source["cases"]}
    selected_ids = contract["replay"]["selected_case_ids"]
    repetitions = contract["replay"]["repetitions_per_case"]
    deterministic_ids = set(contract["replay"]["deterministic_case_ids"])
    rows = []
    for case_id in selected_ids:
        case = cases_by_id[case_id]
        for repetition in range(1, repetitions + 1):
            started = time.perf_counter()
            result = server.run_chat_turn(case["messages"], "review")
            duration_ms = round((time.perf_counter() - started) * 1000)
            checks, missing_all, missing_groups, forbidden = evaluate_answer(case, result)
            generation = result["chat"]["generation"]
            row = {
                "case_id": case_id,
                "family": case["family"],
                "repetition": repetition,
                "passed": all(checks.values()),
                "checks": checks,
                "missing_required_markers": missing_all,
                "missing_required_groups": missing_groups,
                "forbidden_found": forbidden,
                "answer": result["chat"]["assistant_message"],
                "generation": {key: generation.get(key) for key in ("status", "provider", "model", "error")},
                "duration_ms": duration_ms,
            }
            rows.append(row)
            print(json.dumps({"case": case_id, "repetition": repetition, "passed": row["passed"], "provider": row["generation"]["provider"], "duration_ms": duration_ms}, ensure_ascii=False), flush=True)

    provider_drift = []
    deterministic_drift = []
    for case_id in selected_ids:
        case_rows = [row for row in rows if row["case_id"] == case_id]
        providers = {row["generation"]["provider"] for row in case_rows}
        if len(providers) != 1:
            provider_drift.append({"case_id": case_id, "providers": sorted(providers)})
        answers = {row["answer"] for row in case_rows}
        if case_id in deterministic_ids and len(answers) != 1:
            deterministic_drift.append({"case_id": case_id, "distinct_answers": len(answers)})

    durations = [row["duration_ms"] for row in rows]
    recovery = run_recovery_checks()
    performance = {
        "p50_ms": percentile(durations, 0.50),
        "p95_ms": percentile(durations, 0.95),
        "max_ms": max(durations),
        "total_ms": sum(durations),
    }
    summary = {
        "selected_cases": len(selected_ids),
        "families": len({row["family"] for row in rows}),
        "runs": len(rows),
        "passed_runs": sum(row["passed"] for row in rows),
        "failed_runs": sum(not row["passed"] for row in rows),
        "provider_drift_events": len(provider_drift),
        "deterministic_drift_events": len(deterministic_drift),
        "recovery_failures": sum(not value for value in recovery["checks"].values()),
        **performance,
    }
    report = {
        "schema_version": "psm_v0_269_task_stability_report_v1",
        "version": "PSM_V0.269-candidate",
        "contract_sha256": digest(contract),
        "source_contract_sha256": digest(source),
        "provenance": contract["provenance"],
        "summary": summary,
        "provider_drift": provider_drift,
        "deterministic_drift": deterministic_drift,
        "rows": rows,
    }
    write(REPORT_PATH, report)

    if not LEDGER_PATH.exists():
        failures = [
            {
                "case_id": row["case_id"],
                "repetition": row["repetition"],
                "failed_checks": [key for key, value in row["checks"].items() if not value],
                "answer": row["answer"],
                "generation": row["generation"],
                "duration_ms": row["duration_ms"],
            }
            for row in rows if not row["passed"]
        ]
        write(LEDGER_PATH, {
            "schema_version": "psm_v0_269_task_stability_initial_failure_ledger_v1",
            "version": "PSM_V0.269-candidate",
            "frozen_at": contract["frozen_at"],
            "contract_sha256": digest(contract),
            "first_run_completed_before_candidate_changes": True,
            "append_only": True,
            "initial_failure_count": len(failures),
            "initial_failures": failures,
        })
    ledger = read(LEDGER_PATH)
    budget = contract["performance_budget"]
    retained = read(RETAINED_MANIFEST)
    checks = {
        "selected_case_count_matches": summary["selected_cases"] == contract["replay"]["expected_families"],
        "family_count_matches": summary["families"] == contract["replay"]["expected_families"],
        "run_count_matches": summary["runs"] == contract["replay"]["expected_runs"],
        "all_semantic_runs_pass": summary["failed_runs"] == contract["replay"]["maximum_semantic_failures"],
        "provider_stable": summary["provider_drift_events"] == contract["replay"]["maximum_provider_drift_events"],
        "deterministic_answers_exactly_stable": summary["deterministic_drift_events"] == 0,
        "p50_within_budget": summary["p50_ms"] <= budget["p50_max_ms"],
        "p95_within_budget": summary["p95_ms"] <= budget["p95_max_ms"],
        "single_run_within_budget": summary["max_ms"] <= budget["single_run_max_ms"],
        "recovery_contract_passed": recovery["passed"] is True,
        "initial_failure_ledger_retained": ledger["contract_sha256"] == digest(contract) and ledger["append_only"] is True,
        "retained_v0_268_promotion": retained.get("promoted") is True,
        "evaluation_backflow_zero": not any(contract["source_isolation"].values()),
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    gate = {
        "schema_version": "psm_v0_269_task_stability_gate_v1",
        "version": "PSM_V0.269-candidate",
        "passed": all(checks.values()),
        "decision": "task_stability_gate_passed" if all(checks.values()) else "task_stability_gate_failed",
        "checks": checks,
        "metrics": summary,
        "initial_failure_count": ledger["initial_failure_count"],
        "release_boundary": contract["release_boundary"],
    }
    write(GATE_PATH, gate)
    write(CHECKPOINT_PATH, {
        "schema_version": "psm_v0_269_task_stability_checkpoint_v1",
        "current_promoted_version": "PSM_V0.268",
        "target_version": "PSM_V0.269",
        "target_promoted": False,
        "passed": gate["passed"],
        "status": gate["decision"],
        "requires_user_input": False,
        "next_action": "run_v0_269_browser_and_docker_boundaries" if gate["passed"] else "repair_recorded_stability_failures",
    })
    print(json.dumps({"passed": gate["passed"], "initial_failures": ledger["initial_failure_count"], **summary}, ensure_ascii=False))
    if not gate["passed"]:
        raise SystemExit(f"V0.269 stability gate failed: {[key for key, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
