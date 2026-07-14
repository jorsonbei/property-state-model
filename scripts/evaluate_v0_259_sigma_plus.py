from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
BENCHMARK = PSM_ROOT / "benchmarks" / "v0_259_sigma_plus_delivery_cases.json"
EVALUATION = PSM_ROOT / "runtime" / "v0_259_sigma_plus_evaluation.jsonl"
METRICS = PSM_ROOT / "runtime" / "v0_259_sigma_plus_metrics.json"
GATE = PSM_ROOT / "runtime" / "v0_259_sigma_plus_gate.json"
RISKS = PSM_ROOT / "runtime" / "v0_259_sigma_plus_residual_risks.json"
sys.path.insert(0, str(PSM_ROOT))

from product_alpha_app import server  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def offline_provider(*args, **kwargs) -> dict:
    return {
        "status": "error",
        "answer": "",
        "provider": "ollama",
        "model": "v0.259-offline-evaluation",
        "duration_ms": 1,
        "error": "frozen deterministic evaluation",
        "reasoning_leak_removed": False,
    }


def evaluate_case(case: dict) -> dict:
    result = server.run_chat_turn([{"role": "user", "content": case["prompt"]}], "review")
    delivery = result["sigma_plus_delivery"]
    statements = delivery["developer_view"]["statement_audit"]
    claims = statements["claims"]
    supported = [item for item in claims if item["disposition"] == "supported"]
    downgraded = [item for item in claims if item["disposition"] == "downgraded"]
    shadow = delivery["developer_view"]["calibrated_shadow_observation"]
    return {
        "id": case["id"],
        "family": case["family"],
        "prompt": case["prompt"],
        "intent": result["chat"]["intent"],
        "answer": result["chat"]["assistant_message"],
        "delivery_decision": delivery["decision"],
        "delivery_passed": delivery["passed"],
        "user_view_matches": delivery["user_view"]["assistant_message"] == result["chat"]["assistant_message"],
        "strong_claims": statements["strong_claims"],
        "strong_claim_coverage": statements["strong_claim_coverage"],
        "supported_claims_have_provenance": all(item["provenance_refs"] for item in supported),
        "downgraded_claims_have_markers": all(item["downgrade_markers"] for item in downgraded),
        "internal_debug_terms_in_user_view": delivery["internal_debug_terms_in_user_view"],
        "provenance_count": len(delivery["developer_view"]["provenance"]),
        "failure_count": len(delivery["developer_view"]["failures"]),
        "unresolved_judge_count": len(delivery["developer_view"]["required_judges"]),
        "shadow_fallback_targets": shadow["fallback_targets"],
        "controller_used": shadow["controller_used"],
        "candidate_controlled_output": shadow["candidate_controlled_output"],
        "repair_applied": delivery["repair"]["applied"],
        "external_release_authority": delivery["release_boundary"]["external_release_authority"],
    }


def main() -> None:
    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    if benchmark.get("contains_private_data") is not False or benchmark.get("frozen") is not True:
        raise SystemExit("V0.259 benchmark is not frozen synthetic non-private data.")
    original_provider = server.try_ollama_chat_generation
    server.try_ollama_chat_generation = offline_provider
    try:
        rows = [evaluate_case(case) for case in benchmark["cases"]]
    finally:
        server.try_ollama_chat_generation = original_provider

    ordinary_rows = [row for row in rows if row["family"] not in {"project", "theory"}]
    summary = {
        "cases": len(rows),
        "delivery_passed": sum(row["delivery_passed"] for row in rows),
        "strong_claims": sum(row["strong_claims"] for row in rows),
        "minimum_strong_claim_coverage": min(row["strong_claim_coverage"] for row in rows),
        "supported_provenance_failures": sum(not row["supported_claims_have_provenance"] for row in rows),
        "downgrade_marker_failures": sum(not row["downgraded_claims_have_markers"] for row in rows),
        "ordinary_internal_debug_leaks": sum(bool(row["internal_debug_terms_in_user_view"]) for row in ordinary_rows),
        "user_view_mismatches": sum(not row["user_view_matches"] for row in rows),
        "provenance_records": sum(row["provenance_count"] > 0 for row in rows),
        "retained_failure_events": sum(row["failure_count"] for row in rows),
        "retained_unresolved_judges": sum(row["unresolved_judge_count"] for row in rows),
        "shadow_fallback_target_events": sum(len(row["shadow_fallback_targets"]) for row in rows),
        "candidate_controlled_outputs": sum(row["candidate_controlled_output"] for row in rows),
        "deterministic_controller_rows": sum(row["controller_used"] == "deterministic_rule" for row in rows),
        "external_release_authority_rows": sum(row["external_release_authority"] for row in rows),
        "fail_closed_repairs": sum(row["repair_applied"] for row in rows),
    }
    checks = {
        "frozen_synthetic_non_private_cases": len(rows) == 15,
        "all_deliveries_pass": summary["delivery_passed"] == len(rows),
        "all_strong_claims_supported_or_downgraded": summary["minimum_strong_claim_coverage"] == 1.0,
        "supported_claims_have_provenance": summary["supported_provenance_failures"] == 0,
        "downgraded_claims_have_markers": summary["downgrade_marker_failures"] == 0,
        "ordinary_user_view_has_no_internal_debug_terms": summary["ordinary_internal_debug_leaks"] == 0,
        "user_and_developer_views_separated": summary["user_view_mismatches"] == 0,
        "provenance_path_exercised": summary["provenance_records"] >= 4,
        "tool_failure_retained": summary["retained_failure_events"] > 0,
        "unresolved_judges_retained": summary["retained_unresolved_judges"] > 0,
        "calibrated_shadow_fallback_exercised": summary["shadow_fallback_target_events"] > 0,
        "candidate_output_authority_zero": summary["candidate_controlled_outputs"] == 0,
        "deterministic_controller_retained": summary["deterministic_controller_rows"] == len(rows),
        "external_release_authority_zero": summary["external_release_authority_rows"] == 0,
    }
    passed = all(checks.values())
    EVALUATION.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    metrics = {
        "schema_version": "psm_v0_259_sigma_plus_metrics_v1",
        "version": "PSM_V0.259-candidate",
        "summary": summary,
        "families": sorted({row["family"] for row in rows}),
        "boundary": {
            "base_model_weights_changed": False,
            "shadow_training_feedback_written": False,
            "normal_chat_reads_developer_view": False,
            "external_release_authority": False,
        },
    }
    write_json(METRICS, metrics)
    gate = {
        "schema_version": "psm_v0_259_sigma_plus_gate_v1",
        "version": "PSM_V0.259-candidate",
        "passed": passed,
        "decision": "sigma_plus_delivery_ready" if passed else "sigma_plus_delivery_rejected",
        "checks": checks,
        "summary": summary,
        "artifacts": {
            "benchmark": str(BENCHMARK.relative_to(PSM_ROOT)),
            "evaluation": str(EVALUATION.relative_to(PSM_ROOT)),
            "metrics": str(METRICS.relative_to(PSM_ROOT)),
        },
        "release_boundary": {
            "candidate_only": True,
            "shadow_output_authority": False,
            "deterministic_rule_controller_retained": True,
            "rule_replacement_allowed": False,
            "external_user_trial_allowed": False,
            "external_release_authority": False,
        },
    }
    write_json(GATE, gate)
    risks = {
        "schema_version": "psm_v0_259_sigma_plus_residual_risks_v1",
        "version": "PSM_V0.259-candidate",
        "decision": gate["decision"],
        "risks": [
            {"id": "claim_segmentation", "status": "open", "boundary": "Rule-based sentence claim segmentation is not semantic entailment."},
            {"id": "source_entailment", "status": "open", "boundary": "A provenance link does not by itself prove that every phrasing is entailed by the source."},
            {"id": "shadow_generalization", "status": "open", "boundary": "The calibrated shadow encoder remains synthetic-small and has no output authority."},
            {"id": "external_trial", "status": "closed_by_boundary", "boundary": "V0.259 does not authorize external users or professional action."}
        ],
    }
    write_json(RISKS, risks)
    print(json.dumps({"decision": gate["decision"], **summary}, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(f"V0.259 Sigma+ gate failed: {[name for name, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
