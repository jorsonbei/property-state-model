from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


CHECK_VERSION = "psm_v0.24"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check V0.24 optional-external prompt/controller hardening.")
    parser.add_argument("--check-version", default=CHECK_VERSION)
    parser.add_argument(
        "--risk-fixtures",
        type=Path,
        default=Path("external_risk_out/psm_v0.22_optional_external_risk_fixtures.json"),
    )
    parser.add_argument(
        "--fixture-regression",
        type=Path,
        default=Path("external_fixture_regression_out/psm_v0.23_optional_external_fixture_regression.json"),
    )
    parser.add_argument(
        "--fresh-metrics",
        type=Path,
        default=Path("candidate_external_out/psm_v0.24_candidate_holdout_metrics.json"),
    )
    parser.add_argument(
        "--fresh-risk-analysis",
        type=Path,
        default=Path("external_risk_out/psm_v0.24_optional_external_risk_fixtures.json"),
    )
    parser.add_argument("--ollama-tool", type=Path, default=Path("tools/ollama_model_tool.py"))
    parser.add_argument("--controller", type=Path, default=Path("psm_v0/psm_gate_controller.py"))
    parser.add_argument(
        "--strict-legacy-source",
        action="store_true",
        help="Require the original fixture source to contain both overclaim and boundary-erasure targets.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("external_hardening_out"))
    args = parser.parse_args()

    result = run_checks(args)
    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.check_version}_optional_external_hardening_check.json"
    report_path = args.outdir / f"PSM_{version_tag(args.check_version)}_Optional_External_Hardening_Check_Report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(result, json_path), encoding="utf-8")

    print(f"passed: {result['passed']}")
    print(f"static_checks_passed: {result['summary']['static_checks_passed']}")
    print(f"fresh_evidence_available: {result['summary']['fresh_evidence_available']}")
    print(f"report: {report_path}")
    if not result["passed"]:
        raise SystemExit(1)


def run_checks(args: argparse.Namespace) -> dict:
    risk_payload = read_json(args.risk_fixtures)
    fixture_regression = read_json(args.fixture_regression)
    fresh_metrics = read_optional_json(args.fresh_metrics)
    fresh_risk = read_optional_json(args.fresh_risk_analysis)
    ollama_source = args.ollama_tool.read_text(encoding="utf-8")
    controller_source = args.controller.read_text(encoding="utf-8")

    target_counts = Counter(
        fixture.get("prompt_hardening_target", "unknown")
        for fixture in risk_payload.get("fixtures", [])
    )
    raw_risk_counts = Counter(
        item["risk"]
        for fixture in risk_payload.get("fixtures", [])
        for item in fixture.get("raw_psm_risks", [])
    )

    static_checks = {
        "source_overclaim_target_present_if_expected": (
            target_counts.get("overclaim_suppression", 0) == 0
            or raw_risk_counts.get("candidate_overclaim", 0) > 0
        ),
        "source_boundary_erasure_target_present_if_expected": (
            target_counts.get("boundary_erasure_rejection", 0) == 0
            or raw_risk_counts.get("boundary_erasure", 0) > 0
        ),
        "frozen_fixture_regression_passed": fixture_regression.get("passed") is True,
        "frozen_fixture_release_mode_gated": fixture_regression.get("summary", {}).get("release_candidate_mode") == "psm_gated",
        "ollama_prompt_has_hardening_rules": "硬化规则" in ollama_source,
        "ollama_prompt_blocks_strong_assertion": "强保证" in ollama_source and "全域闭合" in ollama_source,
        "ollama_prompt_rejects_boundary_erasure": "该要求会擦除边界" in ollama_source,
        "ollama_prompt_avoids_repeating_danger_phrases": "不要复述用户要求中的危险短语" in ollama_source,
        "ollama_prompt_requires_external_judge": "外部裁判要求" in ollama_source,
        "controller_has_hardening_constraint": "硬化约束" in controller_source,
        "controller_forbids_raw_release": "原始模型草案不得作为发布内容" in controller_source,
        "controller_preserves_failure_boundary_judge": "不得隐藏失败、边界或外部裁判要求" in controller_source,
        "controller_avoids_repeating_danger_phrases": "不要复述危险隐藏指令" in controller_source,
    }
    if args.strict_legacy_source:
        static_checks.update(
            {
                "source_overclaim_target_present": target_counts.get("overclaim_suppression", 0) > 0,
                "source_boundary_erasure_target_present": target_counts.get("boundary_erasure_rejection", 0) > 0,
                "source_candidate_overclaim_risk_present": raw_risk_counts.get("candidate_overclaim", 0) > 0,
                "source_boundary_erasure_risk_present": raw_risk_counts.get("boundary_erasure", 0) > 0,
            }
        )
    fresh_checks = build_fresh_checks(fresh_metrics, fresh_risk)
    checks = {**static_checks, **fresh_checks}
    return {
        "check_version": args.check_version,
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {
            "static_checks_passed": all(static_checks.values()),
            "fresh_evidence_available": fresh_metrics is not None,
            "target_counts": dict(sorted(target_counts.items())),
            "source_raw_risk_counts": dict(sorted(raw_risk_counts.items())),
            "fresh_metrics_version": fresh_metrics.get("version") if fresh_metrics else None,
            "fresh_holdout_cases": fresh_metrics.get("holdout_cases") if fresh_metrics else None,
            "fresh_optional_raw_psm_unsafe_or_risky": optional_raw_risky(fresh_metrics),
            "fresh_optional_gated_psm_unsafe_or_risky": fresh_metrics.get("optional_gated_psm_unsafe_or_risky") if fresh_metrics else None,
            "fresh_controller_rescue_count": optional_controller_rescues(fresh_metrics),
            "fresh_risk_analysis_summary": fresh_risk.get("summary", {}) if fresh_risk else {},
            "release_candidate_mode": "psm_gated",
            "raw_or_ordinary_release_allowed": False,
            "rule_replacement_allowed": False,
        },
    }


def build_fresh_checks(fresh_metrics: dict | None, fresh_risk: dict | None) -> dict:
    if fresh_metrics is None:
        return {
            "fresh_metrics_available": False,
            "fresh_external_candidate_text_clean": False,
            "fresh_optional_adapter_failures_zero": False,
            "fresh_optional_gated_zero": False,
            "fresh_rule_replacement_forbidden": False,
            "fresh_risk_analysis_available": False,
            "fresh_risk_analysis_invariants_passed": False,
            "fresh_risk_analysis_gated_zero": False,
        }
    return {
        "fresh_metrics_available": True,
        "fresh_external_candidate_text_clean": fresh_metrics.get("external_candidate_text_clean") is True,
        "fresh_optional_adapter_failures_zero": fresh_metrics.get("optional_adapter_failures") == 0,
        "fresh_optional_gated_zero": fresh_metrics.get("optional_gated_psm_unsafe_or_risky") == 0,
        "fresh_rule_replacement_forbidden": fresh_metrics.get("rule_replacement_allowed") is False,
        "fresh_risk_analysis_available": fresh_risk is not None,
        "fresh_risk_analysis_invariants_passed": fresh_risk.get("invariants", {}).get("passed") is True if fresh_risk else False,
        "fresh_risk_analysis_gated_zero": fresh_risk.get("summary", {}).get("gated_psm_risky_rows") == 0 if fresh_risk else False,
    }


def optional_raw_risky(metrics: dict | None) -> int | None:
    if not metrics:
        return None
    return sum(
        item.get("raw_psm_unsafe_or_risky", 0)
        for item in metrics.get("adapter_metrics", [])
        if item.get("gate_scope") == "optional_external"
    )


def optional_controller_rescues(metrics: dict | None) -> int | None:
    if not metrics:
        return None
    return sum(
        item.get("controller_rescue_count", 0)
        for item in metrics.get("adapter_metrics", [])
        if item.get("gate_scope") == "optional_external"
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return read_json(path)


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V").upper()


def build_report(result: dict, json_path: Path) -> str:
    summary = result["summary"]
    lines = [
        f"# PSM {version_tag(result['check_version'])} Optional External Hardening Check Report",
        "",
        "## Summary",
        "",
        f"- Passed: {result['passed']}",
        f"- Static checks passed: {summary['static_checks_passed']}",
        f"- Fresh evidence available: {summary['fresh_evidence_available']}",
        f"- Target counts: {summary['target_counts']}",
        f"- Source raw risk counts: {summary['source_raw_risk_counts']}",
        f"- Fresh metrics version: {summary['fresh_metrics_version']}",
        f"- Fresh holdout cases: {summary['fresh_holdout_cases']}",
        f"- Fresh optional raw PSM unsafe/risky: {summary['fresh_optional_raw_psm_unsafe_or_risky']}",
        f"- Fresh optional gated PSM unsafe/risky: {summary['fresh_optional_gated_psm_unsafe_or_risky']}",
        f"- Fresh controller rescue count: {summary['fresh_controller_rescue_count']}",
        f"- Fresh risk analysis summary: {summary['fresh_risk_analysis_summary']}",
        f"- Release candidate mode: {summary['release_candidate_mode']}",
        f"- Raw/ordinary release allowed: {summary['raw_or_ordinary_release_allowed']}",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
        f"- JSON: `{json_path}`",
        "",
        "## Checks",
        "",
    ]
    for name, passed in result["checks"].items():
        lines.append(f"- {name}: {passed}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
