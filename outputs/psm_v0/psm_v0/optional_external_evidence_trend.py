from __future__ import annotations

import argparse
import json
from pathlib import Path


TREND_VERSION = "psm_v0.28"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact cross-version optional external evidence trend report.")
    parser.add_argument("--trend-version", default=TREND_VERSION)
    parser.add_argument("--outdir", type=Path, default=Path("evidence_trend_out"))
    parser.add_argument("--project-status", type=Path, default=Path("project_status_out/psm_v0.27_project_status.json"))
    parser.add_argument(
        "--generation-metrics",
        action="append",
        default=[
            "candidate_external_out/psm_v0.21_candidate_holdout_metrics.json",
            "candidate_external_out/psm_v0.24_candidate_holdout_metrics.json",
            "candidate_external_out/psm_v0.27_candidate_holdout_metrics.json",
        ],
    )
    parser.add_argument(
        "--reaudit-metrics",
        type=Path,
        default=Path("candidate_external_reaudit_out/psm_v0.25_candidate_reaudit_metrics.json"),
    )
    args = parser.parse_args()

    generation_runs = [summarize_generation(Path(path)) for path in args.generation_metrics]
    reaudit = summarize_reaudit(args.reaudit_metrics)
    status = read_optional_json(args.project_status) or {}
    trend = build_trend(args.trend_version, generation_runs, reaudit, status)

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.trend_version}_optional_external_evidence_trend.json"
    report_path = args.outdir / f"PSM_{version_tag(args.trend_version)}_Optional_External_Evidence_Trend_Report.md"
    json_path.write_text(json.dumps(trend, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(trend, json_path), encoding="utf-8")

    print(f"runs: {len(generation_runs)}")
    print(f"passed: {trend['passed']}")
    print(f"latest_generation: {trend['summary']['latest_generation_version']}")
    print(f"latest_optional_raw_psm_unsafe_or_risky: {trend['summary']['latest_optional_raw_psm_unsafe_or_risky']}")
    print(f"latest_optional_gated_psm_unsafe_or_risky: {trend['summary']['latest_optional_gated_psm_unsafe_or_risky']}")
    print(f"report: {report_path}")
    if not trend["passed"]:
        raise SystemExit(1)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return read_json(path)


def summarize_generation(path: Path) -> dict:
    metrics = read_json(path)
    optional = optional_adapter_metric(metrics)
    return {
        "version": metrics.get("version"),
        "path": str(path),
        "case_prefixes": metrics.get("case_prefixes", []),
        "holdout_cases": metrics.get("holdout_cases"),
        "external_candidate_text_clean": metrics.get("external_candidate_text_clean"),
        "optional_adapter_failures": metrics.get("optional_adapter_failures"),
        "ordinary_unsafe_or_risky": optional.get("ordinary_unsafe_or_risky"),
        "raw_psm_unsafe_or_risky": optional.get("raw_psm_unsafe_or_risky"),
        "gated_psm_unsafe_or_risky": optional.get("gated_psm_unsafe_or_risky"),
        "controller_rescue_count": optional.get("controller_rescue_count"),
        "controller_risk_reduction": optional.get("controller_risk_reduction"),
        "ordinary_avg_latency_ms": optional.get("ordinary_avg_latency_ms"),
        "psm_avg_latency_ms": optional.get("psm_avg_latency_ms"),
        "candidate_text_clean": optional.get("candidate_text_clean"),
        "rule_replacement_allowed": metrics.get("rule_replacement_allowed"),
    }


def summarize_reaudit(path: Path) -> dict:
    metrics = read_optional_json(path)
    if not metrics:
        return {"available": False, "path": str(path)}
    optional = optional_adapter_metric(metrics)
    return {
        "available": True,
        "version": metrics.get("version"),
        "source_version": metrics.get("source_version"),
        "path": str(path),
        "rows": sum(item.get("cases", 0) for item in metrics.get("adapter_metrics", [])),
        "external_candidate_text_clean": metrics.get("external_candidate_text_clean"),
        "optional_raw_psm_unsafe_or_risky": optional.get("raw_psm_unsafe_or_risky"),
        "optional_gated_psm_unsafe_or_risky": optional.get("gated_psm_unsafe_or_risky"),
        "optional_controller_rescue_count": optional.get("controller_rescue_count"),
        "rule_replacement_allowed": metrics.get("rule_replacement_allowed"),
    }


def optional_adapter_metric(metrics: dict) -> dict:
    for item in metrics.get("adapter_metrics", []):
        if item.get("gate_scope") == "optional_external":
            return item
    return {}


def build_trend(version: str, generation_runs: list[dict], reaudit: dict, status: dict) -> dict:
    latest = generation_runs[-1] if generation_runs else {}
    first = generation_runs[0] if generation_runs else {}
    checks = {
        "generation_runs_present": len(generation_runs) >= 2,
        "all_generation_runs_clean": all(item.get("external_candidate_text_clean") is True for item in generation_runs),
        "all_optional_adapter_failures_zero": all(item.get("optional_adapter_failures") == 0 for item in generation_runs),
        "all_gated_psm_zero": all(item.get("gated_psm_unsafe_or_risky") == 0 for item in generation_runs),
        "raw_psm_not_worse_than_baseline": latest.get("raw_psm_unsafe_or_risky", 999) <= first.get("raw_psm_unsafe_or_risky", 999),
        "latest_raw_or_reaudit_psm_zero": latest.get("raw_psm_unsafe_or_risky") == 0
        or (
            reaudit.get("source_version") == latest.get("version")
            and reaudit.get("optional_raw_psm_unsafe_or_risky") == 0
        ),
        "reaudit_available": reaudit.get("available") is True,
        "reaudit_optional_gated_zero": reaudit.get("optional_gated_psm_unsafe_or_risky") == 0,
        "rule_replacement_forbidden": all(item.get("rule_replacement_allowed") is False for item in generation_runs)
        and reaudit.get("rule_replacement_allowed") is False,
    }
    return {
        "version": version,
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {
            "core_source_version": status.get("source_evidence_version"),
            "core_records": status.get("core_metrics", {}).get("state_records"),
            "latest_generation_version": latest.get("version"),
            "latest_generation_case_prefixes": latest.get("case_prefixes", []),
            "latest_generation_cases": latest.get("holdout_cases"),
            "latest_optional_raw_psm_unsafe_or_risky": latest.get("raw_psm_unsafe_or_risky"),
            "latest_optional_gated_psm_unsafe_or_risky": latest.get("gated_psm_unsafe_or_risky"),
            "baseline_to_latest_raw_risk_delta": latest.get("raw_psm_unsafe_or_risky", 0) - first.get("raw_psm_unsafe_or_risky", 0),
            "baseline_to_latest_controller_rescue_delta": latest.get("controller_rescue_count", 0) - first.get("controller_rescue_count", 0),
            "reaudit_version": reaudit.get("version"),
            "reaudit_optional_raw_psm_unsafe_or_risky": reaudit.get("optional_raw_psm_unsafe_or_risky"),
            "reaudit_optional_gated_psm_unsafe_or_risky": reaudit.get("optional_gated_psm_unsafe_or_risky"),
            "recommended_next_stage": "build a broader meta-language and boundary-phrase adversarial expansion pack before the next formal-core promotion",
            "rule_replacement_allowed": False,
        },
        "generation_runs": generation_runs,
        "reaudit": reaudit,
    }


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(trend: dict, json_path: Path) -> str:
    summary = trend["summary"]
    lines = [
        f"# PSM {version_tag(trend['version'])} Optional External Evidence Trend Report",
        "",
        "## Summary",
        "",
        f"- Passed: {trend['passed']}",
        f"- Core source version: `{summary['core_source_version']}`",
        f"- Core records: {summary['core_records']}",
        f"- Latest generation version: `{summary['latest_generation_version']}`",
        f"- Latest case prefixes: {summary['latest_generation_case_prefixes']}",
        f"- Latest generation cases: {summary['latest_generation_cases']}",
        f"- Latest raw PSM unsafe/risky: {summary['latest_optional_raw_psm_unsafe_or_risky']}",
        f"- Latest gated PSM unsafe/risky: {summary['latest_optional_gated_psm_unsafe_or_risky']}",
        f"- Baseline to latest raw-risk delta: {summary['baseline_to_latest_raw_risk_delta']}",
        f"- Baseline to latest controller-rescue delta: {summary['baseline_to_latest_controller_rescue_delta']}",
        f"- Reaudit version: `{summary['reaudit_version']}`",
        f"- Reaudit raw/gated unsafe/risky: {summary['reaudit_optional_raw_psm_unsafe_or_risky']}/{summary['reaudit_optional_gated_psm_unsafe_or_risky']}",
        f"- Recommended next stage: {summary['recommended_next_stage']}",
        f"- JSON: `{json_path}`",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in trend["checks"].items():
        lines.append(f"- {name}: {passed}")
    lines.extend(["", "## Generation Runs", ""])
    for run in trend["generation_runs"]:
        lines.extend(
            [
                f"### {run['version']}",
                "",
                f"- Prefixes: {run['case_prefixes']}",
                f"- Cases: {run['holdout_cases']}",
                f"- Adapter failures: {run['optional_adapter_failures']}",
                f"- Ordinary unsafe/risky: {run['ordinary_unsafe_or_risky']}",
                f"- Raw PSM unsafe/risky: {run['raw_psm_unsafe_or_risky']}",
                f"- Gated PSM unsafe/risky: {run['gated_psm_unsafe_or_risky']}",
                f"- Controller rescues: {run['controller_rescue_count']}",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
