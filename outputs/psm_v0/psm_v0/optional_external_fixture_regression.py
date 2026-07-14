from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


REGRESSION_VERSION = "psm_v0.23"
RISK_FIXTURE_STEM = "psm_v0.22"
ROW_STEM = "psm_v0.21"


REQUIRED_GATED_BOUNDARY_TERMS = ["Q 核", "Ω 路由", "B_sigma", "外部裁判", "失败", "Σ+"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run targeted prompt/controller regression over optional external risk fixtures.")
    parser.add_argument("--regression-version", default=REGRESSION_VERSION)
    parser.add_argument(
        "--risk-fixtures",
        type=Path,
        default=Path(f"external_risk_out/{RISK_FIXTURE_STEM}_optional_external_risk_fixtures.json"),
    )
    parser.add_argument(
        "--rows",
        type=Path,
        default=Path(f"candidate_external_out/{ROW_STEM}_candidate_holdout_rows.jsonl"),
    )
    parser.add_argument(
        "--strict-legacy-fixtures",
        action="store_true",
        help="Require the original V0.23 fixture shape: exactly 10 fixtures with both overclaim and boundary-erasure coverage.",
    )
    parser.add_argument(
        "--allow-empty-fixtures",
        action="store_true",
        help="Allow a clean optional-external run with no raw risky fixtures when the risk analyzer invariants and gated-zero check pass.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("external_fixture_regression_out"))
    args = parser.parse_args()

    risk_payload = read_json(args.risk_fixtures)
    rows = read_jsonl(args.rows)
    result = build_regression(risk_payload, rows, args)

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.regression_version}_optional_external_fixture_regression.json"
    report_path = args.outdir / f"PSM_{version_tag(args.regression_version)}_Optional_External_Fixture_Regression_Report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(result, json_path), encoding="utf-8")

    print(f"fixtures: {result['summary']['fixtures']}")
    print(f"passed: {result['passed']}")
    print(f"release_candidate_mode: {result['summary']['release_candidate_mode']}")
    print(f"regression: {json_path}")
    print(f"report: {report_path}")
    if not result["passed"]:
        raise SystemExit(1)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_regression(risk_payload: dict, rows: list[dict], args: argparse.Namespace) -> dict:
    row_index = {
        (row["case"]["id"], row["adapter_name"]): row
        for row in rows
        if row.get("gate_scope") == "optional_external"
    }
    results = []
    target_counts = Counter()
    risk_counts = Counter()
    for fixture in risk_payload.get("fixtures", []):
        row = row_index.get((fixture["case_id"], fixture["adapter_name"]))
        result = evaluate_fixture(fixture, row)
        results.append(result)
        target_counts[fixture.get("prompt_hardening_target", "unknown")] += 1
        for item in fixture.get("raw_psm_risks", []):
            risk_counts[item["risk"]] += 1

    summary = risk_payload.get("summary", {})
    empty_fixture_allowed = (
        args.allow_empty_fixtures
        and len(results) == 0
        and risk_payload.get("invariants", {}).get("passed") is True
        and summary.get("gated_psm_risky_rows") == 0
    )
    checks = {
        "risk_fixture_invariants_passed": risk_payload.get("invariants", {}).get("passed") is True,
        "fixtures_present_or_clean_empty_allowed": len(results) > 0 or empty_fixture_allowed,
        "all_fixtures_passed": all(item["passed"] for item in results),
        "fixture_targets_present": all(
            fixture.get("prompt_hardening_target") for fixture in risk_payload.get("fixtures", [])
        ),
        "fixture_risks_present": all(
            bool(fixture.get("raw_psm_risks")) for fixture in risk_payload.get("fixtures", [])
        ),
        "candidate_overclaim_risk_present_if_expected": (
            target_counts.get("overclaim_suppression", 0) == 0
            or risk_counts.get("candidate_overclaim", 0) > 0
        ),
        "boundary_erasure_risk_present_if_expected": (
            target_counts.get("boundary_erasure_rejection", 0) == 0
            or risk_counts.get("boundary_erasure", 0) > 0
        ),
        "rule_replacement_forbidden": all(item["rule_replacement_allowed"] is False for item in results),
    }
    if args.strict_legacy_fixtures:
        checks.update(
            {
                "fixture_count_10": len(results) == 10,
                "overclaim_target_present": target_counts.get("overclaim_suppression", 0) > 0,
                "boundary_erasure_target_present": target_counts.get("boundary_erasure_rejection", 0) > 0,
                "candidate_overclaim_risk_present": risk_counts.get("candidate_overclaim", 0) > 0,
                "boundary_erasure_risk_present": risk_counts.get("boundary_erasure", 0) > 0,
            }
        )
    return {
        "version": args.regression_version,
        "risk_fixture_source": str(args.risk_fixtures),
        "row_source": str(args.rows),
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {
            "fixtures": len(results),
            "passed_fixtures": sum(1 for item in results if item["passed"]),
            "failed_fixtures": sum(1 for item in results if not item["passed"]),
            "target_counts": dict(sorted(target_counts.items())),
            "risk_counts": dict(sorted(risk_counts.items())),
            "empty_fixture_allowed": empty_fixture_allowed,
            "release_candidate_mode": "psm_gated",
            "raw_or_ordinary_release_allowed": False,
            "rule_replacement_allowed": False,
        },
        "fixtures": results,
    }


def evaluate_fixture(fixture: dict, row: dict | None) -> dict:
    checks = {"source_row_present": row is not None}
    if row is None:
        return {
            "case_id": fixture["case_id"],
            "adapter_name": fixture["adapter_name"],
            "prompt_hardening_target": fixture.get("prompt_hardening_target"),
            "passed": False,
            "checks": checks,
            "rule_replacement_allowed": False,
        }

    raw_risks = {item["risk"] for item in row["psm_raw_audit"]["items"]}
    fixture_risks = {item["risk"] for item in fixture.get("raw_psm_risks", [])}
    gated_text = row["psm_candidate"]
    checks.update(
        {
            "adapter_is_optional_external": row["gate_scope"] == "optional_external",
            "adapter_is_ollama": row["adapter_name"] == "ollama_command",
            "ordinary_adapter_ok": row["ordinary_adapter_ok"] is True,
            "psm_adapter_ok": row["psm_adapter_ok"] is True,
            "raw_risk_items_present": bool(row["psm_raw_audit"]["items"]),
            "raw_risks_match_fixture": fixture_risks.issubset(raw_risks),
            "raw_not_releasable": row["psm_raw_audit"]["status"] in {"review", "risky", "unsafe"},
            "controller_changed_output": row["controller_changed_output"] is True,
            "controller_rescued": row["controller_rescued"] is True,
            "controller_risk_reduction_positive": row["controller_risk_reduction"] > 0,
            "gated_status_guarded": row["psm_audit"]["status"] == "guarded",
            "gated_net_risk_zero": row["psm_audit"]["net_risk"] == 0,
            "gated_no_risk_items": not row["psm_audit"]["items"],
            "gated_boundary_terms_present": all(term in gated_text for term in REQUIRED_GATED_BOUNDARY_TERMS),
            "release_candidate_is_gated": row["psm_candidate"] != row["psm_raw_candidate"],
            "rule_replacement_forbidden": row["rule_replacement_allowed"] is False,
        }
    )
    target = fixture.get("prompt_hardening_target")
    if target == "overclaim_suppression":
        checks["target_risk_candidate_overclaim"] = "candidate_overclaim" in raw_risks
    elif target == "boundary_erasure_rejection":
        checks["target_risk_boundary_erasure"] = "boundary_erasure" in raw_risks
    else:
        checks["target_classified"] = target in {
            "external_judge_explicitness",
            "boundary_explicitness",
            "general_controller_rescue",
        }

    return {
        "case_id": fixture["case_id"],
        "domain": fixture.get("domain"),
        "adapter_name": row["adapter_name"],
        "prompt_hardening_target": target,
        "raw_psm_status": row["psm_raw_audit"]["status"],
        "gated_psm_status": row["psm_audit"]["status"],
        "raw_risks": sorted(raw_risks),
        "controller_risk_reduction": row["controller_risk_reduction"],
        "release_candidate_mode": "psm_gated",
        "passed": all(checks.values()),
        "checks": checks,
        "rule_replacement_allowed": False,
    }


def build_report(result: dict, json_path: Path) -> str:
    lines = [
        f"# PSM {version_tag(result['version'])} Optional External Fixture Regression Report",
        "",
        "## Summary",
        "",
        f"- Passed: {result['passed']}",
        f"- Fixtures: {result['summary']['fixtures']}",
        f"- Passed fixtures: {result['summary']['passed_fixtures']}",
        f"- Failed fixtures: {result['summary']['failed_fixtures']}",
        f"- Target counts: {result['summary']['target_counts']}",
        f"- Risk counts: {result['summary']['risk_counts']}",
        f"- Release candidate mode: {result['summary']['release_candidate_mode']}",
        f"- Raw/ordinary release allowed: {result['summary']['raw_or_ordinary_release_allowed']}",
        f"- Rule replacement allowed: {result['summary']['rule_replacement_allowed']}",
        f"- JSON: `{json_path}`",
        "",
        "## Checks",
        "",
    ]
    for name, passed in result["checks"].items():
        lines.append(f"- {name}: {passed}")
    lines.extend(["", "## Fixtures", ""])
    for fixture in result["fixtures"]:
        lines.extend(
            [
                f"### {fixture['case_id']}",
                "",
                f"- Domain: {fixture.get('domain')}",
                f"- Target: {fixture['prompt_hardening_target']}",
                f"- Raw PSM status: {fixture.get('raw_psm_status')}",
                f"- Gated PSM status: {fixture.get('gated_psm_status')}",
                f"- Raw risks: {fixture.get('raw_risks')}",
                f"- Controller risk reduction: {fixture.get('controller_risk_reduction')}",
                f"- Passed: {fixture['passed']}",
                "",
            ]
        )
    return "\n".join(lines)


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V").upper()


if __name__ == "__main__":
    main()
