from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_STEM = "psm_v0.20"
CHECK_VERSION = "psm_v0.20"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fast deterministic PSM regression checks without model calls.")
    parser.add_argument("--stem", default=DEFAULT_STEM)
    parser.add_argument("--check-version", default=CHECK_VERSION)
    parser.add_argument("--taxonomy", type=Path, default=Path("taxonomy_out/psm_v0.20_candidate_taxonomy.json"))
    parser.add_argument("--status", type=Path, default=Path("project_status_out/psm_v0.20_project_status.json"))
    parser.add_argument("--fixtures", type=Path, default=Path("fixture_out/psm_v0.20_candidate_regression_fixtures.json"))
    parser.add_argument("--taxonomy-delta", type=Path, default=Path("taxonomy_delta_out/psm_v0.20_taxonomy_delta.json"))
    parser.add_argument("--case-pack", type=Path, default=Path("case_packs/v0_19_evaluator_blindspot_cases.json"))
    parser.add_argument("--case-pack-expected-count", type=int, default=8)
    parser.add_argument("--allow-taxonomy-expansion", action="store_true")
    parser.add_argument("--outdir", type=Path, default=Path("regression_out"))
    args = parser.parse_args()

    result = run_checks(args)
    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.check_version}_regression_check.json"
    report_path = args.outdir / f"PSM_{stem_to_tag(args.check_version)}_Regression_Check_Report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(result, json_path), encoding="utf-8")

    print(f"passed: {result['passed']}")
    print(f"checks: {len(result['checks'])}")
    print(f"report: {report_path}")
    if not result["passed"]:
        raise SystemExit(1)


def run_checks(args: argparse.Namespace) -> dict:
    stem = args.stem
    checks = {}
    checks["eval_report_exists"] = Path("eval_out") / f"PSM_{stem_to_tag(stem)}_Eval_Report.md"
    checks["state_dataset_exists"] = Path("state_dataset_out") / f"{stem}_state_encoder.jsonl"
    checks["candidate_metrics_exists"] = Path("candidate_holdout_out") / f"{stem}_candidate_holdout_metrics.json"
    checks["candidate_rows_exists"] = Path("candidate_holdout_out") / f"{stem}_candidate_holdout_rows.jsonl"
    checks["candidate_ledger_exists"] = Path("candidate_holdout_out") / f"{stem}_candidate_failure_ledger.jsonl"
    checks["state_manifest_exists"] = Path("state_dataset_out") / f"{stem}_state_manifest.json"
    checks["taxonomy_exists"] = args.taxonomy
    checks["status_exists"] = args.status
    checks["fixtures_exists"] = args.fixtures
    checks["taxonomy_delta_exists"] = args.taxonomy_delta
    checks["case_pack_exists"] = args.case_pack

    file_checks = {name: path.exists() for name, path in checks.items()}
    metrics = read_json(checks["candidate_metrics_exists"])
    state_manifest = read_json(checks["state_manifest_exists"])
    taxonomy = read_json(args.taxonomy)
    status = read_json(args.status)
    fixtures = read_json(args.fixtures)
    taxonomy_delta = read_json(args.taxonomy_delta)
    case_pack = read_json(args.case_pack)
    rows_count = count_lines(checks["candidate_rows_exists"])
    ledger_count = count_lines(checks["candidate_ledger_exists"])
    dataset_count = count_lines(checks["state_dataset_exists"])
    expected_candidate_rows = sum(item.get("cases", 0) for item in metrics.get("adapter_metrics", []))
    expected_ledger_events = sum(metrics.get("ledger_group_counts", {}).values())
    changed_groups = taxonomy_delta.get("summary", {}).get("changed_groups")
    unexpected_regression = taxonomy_delta.get("summary", {}).get("unexpected_regression")

    invariant_checks = {
        "dataset_matches_manifest": dataset_count == state_manifest.get("records"),
        "candidate_rows_match_adapter_metrics": rows_count == expected_candidate_rows,
        "candidate_ledger_matches_group_counts": ledger_count == expected_ledger_events,
        "required_candidate_text_clean": metrics.get("candidate_text_clean") is True,
        "external_candidate_text_clean": metrics.get("external_candidate_text_clean") in {True, None},
        "required_gated_psm_zero": metrics.get("gated_psm_unsafe_or_risky") == 0,
        "optional_gated_psm_zero": metrics.get("optional_gated_psm_unsafe_or_risky") == 0,
        "fault_gated_psm_zero": metrics.get("fault_gated_psm_unsafe_or_risky") == 0,
        "fault_adapter_failures_present": metrics.get("fault_adapter_failures", 0) > 0,
        "fault_injection_events_present": metrics.get("fault_injection_events", 0) > 0,
        "controller_rescue_present": metrics.get("controller_rescue_count", 0) > 0,
        "taxonomy_invariants_passed": taxonomy.get("invariants", {}).get("passed") is True,
        "status_rule_replacement_false": status.get("boundaries", {}).get("rule_replacement_allowed") is False,
        "status_next_stage_open": status.get("next_stage", {}).get("requires_user_input") is False,
        "fixtures_coverage_passed": fixtures.get("coverage", {}).get("passed") is True,
        "fixtures_count_matches_required": len(fixtures.get("fixtures", [])) == len(fixtures.get("coverage", {}).get("required", [])),
        "taxonomy_delta_zero_or_allowed_expansion": changed_groups == 0
        or (args.allow_taxonomy_expansion and unexpected_regression is False),
        "taxonomy_delta_no_regression": unexpected_regression is False,
        "case_pack_expected_count": len(case_pack) == args.case_pack_expected_count,
    }
    all_checks = {**file_checks, **invariant_checks}
    return {
        "stem": stem,
        "passed": all(all_checks.values()),
        "checks": all_checks,
        "counts": {
            "dataset_rows": dataset_count,
            "manifest_records": state_manifest.get("records"),
            "candidate_rows": rows_count,
            "expected_candidate_rows": expected_candidate_rows,
            "candidate_ledger_events": ledger_count,
            "expected_candidate_ledger_events": expected_ledger_events,
            "taxonomy_delta_changed_groups": changed_groups,
        },
        "rule_replacement_allowed": False,
        "check_version": args.check_version,
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def count_lines(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def stem_to_tag(stem: str) -> str:
    return stem.replace("psm_v", "V")


def build_report(result: dict, json_path: Path) -> str:
    lines = [
        f"# PSM {stem_to_tag(result['check_version'])} Regression Check Report",
        "",
        "## Summary",
        "",
        f"- Stem: `{result['stem']}`",
        f"- Check version: `{result['check_version']}`",
        f"- Passed: {result['passed']}",
        f"- Result JSON: `{json_path}`",
        f"- Counts: {result['counts']}",
        f"- Rule replacement allowed: {result['rule_replacement_allowed']}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in result["checks"].items():
        lines.append(f"- {name}: {passed}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
