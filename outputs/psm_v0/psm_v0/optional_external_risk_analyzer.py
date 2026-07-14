from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


ANALYSIS_VERSION = "psm_v0.22"
SOURCE_STEM = "psm_v0.21"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract optional external raw PSM risk fixtures.")
    parser.add_argument("--analysis-version", default=ANALYSIS_VERSION)
    parser.add_argument("--source-stem", default=SOURCE_STEM)
    parser.add_argument("--rows", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("external_risk_out"))
    parser.add_argument("--require-rescues", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if args.rows is None:
        args.rows = Path(f"candidate_external_out/{args.source_stem}_candidate_holdout_rows.jsonl")

    rows = read_jsonl(args.rows)
    analysis = build_analysis(rows, args.rows, args.analysis_version, args.source_stem, args.require_rescues)
    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.analysis_version}_optional_external_risk_fixtures.json"
    report_path = args.outdir / f"PSM_{version_tag(args.analysis_version)}_Optional_External_Risk_Fixtures_Report.md"
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(analysis, json_path), encoding="utf-8")

    print(f"optional_rows: {analysis['summary']['optional_rows']}")
    print(f"raw_psm_risky_rows: {analysis['summary']['raw_psm_risky_rows']}")
    print(f"controller_rescued_rows: {analysis['summary']['controller_rescued_rows']}")
    print(f"gated_psm_risky_rows: {analysis['summary']['gated_psm_risky_rows']}")
    print(f"analysis: {json_path}")
    print(f"report: {report_path}")
    if not analysis["invariants"]["passed"]:
        raise SystemExit(1)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_analysis(
    rows: list[dict],
    rows_path: Path,
    analysis_version: str,
    source_stem: str,
    require_rescues: bool,
) -> dict:
    optional_rows = [row for row in rows if row.get("gate_scope") == "optional_external"]
    risky_raw_rows = [
        row for row in optional_rows
        if row["psm_raw_audit"]["status"] in {"risky", "unsafe"}
    ]
    rescued_rows = [row for row in optional_rows if row["controller_rescued"]]
    gated_risky_rows = [
        row for row in optional_rows
        if row["psm_audit"]["status"] in {"risky", "unsafe"}
    ]
    fixtures = [build_fixture(row) for row in rescued_rows]
    risk_counts = Counter()
    domain_counts = Counter()
    for row in risky_raw_rows:
        domain = row["case"].get("expected", {}).get("domain", "unknown")
        domain_counts[domain] += 1
        for item in row["psm_raw_audit"]["items"]:
            risk_counts[item["risk"]] += 1

    raw_risk_requirement_met = bool(risky_raw_rows) or not require_rescues
    controller_rescue_requirement_met = bool(rescued_rows) or not require_rescues
    invariants = {
        "passed": bool(optional_rows)
        and raw_risk_requirement_met
        and controller_rescue_requirement_met
        and not gated_risky_rows
        and all(row.get("rule_replacement_allowed") is False for row in optional_rows),
        "checks": {
            "optional_rows_present": bool(optional_rows),
            "raw_psm_risk_requirement": raw_risk_requirement_met,
            "controller_rescue_requirement": controller_rescue_requirement_met,
            "gated_psm_risk_zero": not gated_risky_rows,
            "rule_replacement_forbidden": all(row.get("rule_replacement_allowed") is False for row in optional_rows),
        },
    }
    return {
        "version": analysis_version,
        "source_version": source_stem,
        "source_rows": str(rows_path),
        "summary": {
            "optional_rows": len(optional_rows),
            "raw_psm_risky_rows": len(risky_raw_rows),
            "controller_rescued_rows": len(rescued_rows),
            "gated_psm_risky_rows": len(gated_risky_rows),
            "risk_counts": dict(sorted(risk_counts.items())),
            "domain_counts": dict(sorted(domain_counts.items())),
            "require_rescues": require_rescues,
            "rule_replacement_allowed": False,
        },
        "fixtures": fixtures,
        "invariants": invariants,
    }


def build_fixture(row: dict) -> dict:
    return {
        "case_id": row["case"]["id"],
        "domain": row["case"].get("expected", {}).get("domain", "unknown"),
        "adapter_name": row["adapter_name"],
        "raw_psm_status": row["psm_raw_audit"]["status"],
        "gated_psm_status": row["psm_audit"]["status"],
        "raw_psm_risks": [
            {
                "risk": item["risk"],
                "severity": item["severity"],
                "finding": item["finding"],
            }
            for item in row["psm_raw_audit"]["items"]
        ],
        "controller_risk_reduction": row["controller_risk_reduction"],
        "prompt_hardening_target": classify_prompt_hardening_target(row),
        "rule_replacement_allowed": False,
    }


def classify_prompt_hardening_target(row: dict) -> str:
    risks = {item["risk"] for item in row["psm_raw_audit"]["items"]}
    if "missing_external_judge" in risks:
        return "external_judge_explicitness"
    if "missing_boundary" in risks:
        return "boundary_explicitness"
    if "candidate_overclaim" in risks:
        return "overclaim_suppression"
    if "boundary_erasure" in risks:
        return "boundary_erasure_rejection"
    return "general_controller_rescue"


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(analysis: dict, json_path: Path) -> str:
    summary = analysis["summary"]
    lines = [
        f"# PSM {version_tag(analysis['version'])} Optional External Risk Fixtures Report",
        "",
        "## Summary",
        "",
        f"- Source version: `{analysis['source_version']}`",
        f"- Optional rows: {summary['optional_rows']}",
        f"- Raw PSM risky rows: {summary['raw_psm_risky_rows']}",
        f"- Controller rescued rows: {summary['controller_rescued_rows']}",
        f"- Gated PSM risky rows: {summary['gated_psm_risky_rows']}",
        f"- Risk counts: {summary['risk_counts']}",
        f"- Domain counts: {summary['domain_counts']}",
        f"- Invariants passed: {analysis['invariants']['passed']}",
        f"- JSON: `{json_path}`",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
        "",
        "## Fixtures",
        "",
    ]
    for fixture in analysis["fixtures"]:
        lines.extend(
            [
                f"### {fixture['case_id']}",
                "",
                f"- Domain: {fixture['domain']}",
                f"- Raw PSM status: {fixture['raw_psm_status']}",
                f"- Gated PSM status: {fixture['gated_psm_status']}",
                f"- Controller risk reduction: {fixture['controller_risk_reduction']}",
                f"- Hardening target: {fixture['prompt_hardening_target']}",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
