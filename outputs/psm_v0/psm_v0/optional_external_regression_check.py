from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECK_VERSION = "psm_v0.23"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check optional external candidate evidence without changing required gates.")
    parser.add_argument("--check-version", default=CHECK_VERSION)
    parser.add_argument(
        "--required-case-prefix",
        action="append",
        default=None,
        help="Required case prefix for this optional evidence check. May be repeated or comma-separated.",
    )
    parser.add_argument("--metrics", type=Path, default=Path("candidate_external_out/psm_v0.21_candidate_holdout_metrics.json"))
    parser.add_argument("--taxonomy", type=Path, default=Path("taxonomy_external_out/psm_v0.21_candidate_taxonomy.json"))
    parser.add_argument("--risk-analysis", type=Path, default=Path("external_risk_out/psm_v0.22_optional_external_risk_fixtures.json"))
    parser.add_argument(
        "--fixture-regression",
        type=Path,
        default=Path("external_fixture_regression_out/psm_v0.23_optional_external_fixture_regression.json"),
    )
    parser.add_argument("--outdir", type=Path, default=Path("regression_external_out"))
    args = parser.parse_args()

    result = run_checks(args)
    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.check_version}_optional_external_regression_check.json"
    report_path = args.outdir / f"PSM_{version_tag(args.check_version)}_Optional_External_Regression_Check_Report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(result, json_path), encoding="utf-8")
    print(f"passed: {result['passed']}")
    print(f"checks: {len(result['checks'])}")
    print(f"report: {report_path}")
    if not result["passed"]:
        raise SystemExit(1)


def run_checks(args: argparse.Namespace) -> dict:
    metrics = read_json(args.metrics)
    taxonomy = read_json(args.taxonomy)
    risk_analysis = read_json(args.risk_analysis)
    fixture_regression = read_json(args.fixture_regression)
    optional_metrics = [
        item for item in metrics.get("adapter_metrics", [])
        if item.get("gate_scope") == "optional_external"
    ]
    required_prefixes = normalize_prefixes(args.required_case_prefix) or ["v15_", "v19_"]
    present_prefixes = set(metrics.get("case_prefixes", []))
    checks = {
        "metrics_exists": args.metrics.exists(),
        "taxonomy_exists": args.taxonomy.exists(),
        "risk_analysis_exists": args.risk_analysis.exists(),
        "fixture_regression_exists": args.fixture_regression.exists(),
        "required_candidate_text_clean": metrics.get("candidate_text_clean") is True,
        "external_candidate_text_clean": metrics.get("external_candidate_text_clean") is True,
        "optional_external_adapter_present": bool(optional_metrics),
        "optional_adapter_failures_zero": metrics.get("optional_adapter_failures") == 0,
        "optional_gated_psm_zero": metrics.get("optional_gated_psm_unsafe_or_risky") == 0,
        "required_gated_psm_zero": metrics.get("gated_psm_unsafe_or_risky") == 0,
        "fault_gated_psm_zero": metrics.get("fault_gated_psm_unsafe_or_risky") == 0,
        "taxonomy_invariants_passed": taxonomy.get("invariants", {}).get("passed") is True,
        "rule_replacement_forbidden": metrics.get("rule_replacement_allowed") is False,
        "required_case_prefixes_present": set(required_prefixes).issubset(present_prefixes),
        "risk_analysis_invariants_passed": risk_analysis.get("invariants", {}).get("passed") is True,
        "risk_analysis_gated_zero": risk_analysis.get("summary", {}).get("gated_psm_risky_rows") == 0,
        "fixture_regression_passed": fixture_regression.get("passed") is True,
        "fixture_release_mode_gated": fixture_regression.get("summary", {}).get("release_candidate_mode") == "psm_gated",
        "fixture_raw_release_forbidden": fixture_regression.get("summary", {}).get("raw_or_ordinary_release_allowed") is False,
    }
    return {
        "check_version": args.check_version,
        "passed": all(checks.values()),
        "checks": checks,
        "optional_adapter_metrics": optional_metrics,
        "risk_analysis_summary": risk_analysis.get("summary", {}),
        "fixture_regression_summary": fixture_regression.get("summary", {}),
        "case_prefixes": metrics.get("case_prefixes", []),
        "required_case_prefixes": required_prefixes,
        "holdout_cases": metrics.get("holdout_cases"),
        "rule_replacement_allowed": False,
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_prefixes(prefix_args: list[str] | None) -> list[str]:
    if not prefix_args:
        return []
    prefixes: list[str] = []
    for raw in prefix_args:
        for item in raw.split(","):
            item = item.strip()
            if item:
                prefixes.append(item)
    return list(dict.fromkeys(prefixes))


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(result: dict, json_path: Path) -> str:
    lines = [
        f"# PSM {version_tag(result['check_version'])} Optional External Regression Check Report",
        "",
        "## Summary",
        "",
        f"- Passed: {result['passed']}",
        f"- Case prefixes: {result['case_prefixes']}",
        f"- Holdout cases: {result['holdout_cases']}",
        f"- Risk analysis summary: {result['risk_analysis_summary']}",
        f"- Fixture regression summary: {result['fixture_regression_summary']}",
        f"- Rule replacement allowed: {result['rule_replacement_allowed']}",
        f"- Result JSON: `{json_path}`",
        "",
        "## Checks",
        "",
    ]
    for name, passed in result["checks"].items():
        lines.append(f"- {name}: {passed}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
