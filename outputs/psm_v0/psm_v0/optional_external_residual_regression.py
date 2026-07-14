from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidate_auditor import audit_candidate_text
from .pipeline import run_pipeline


REGRESSION_VERSION = "psm_v0.41"
SOURCE_STEM = "psm_v0.41"


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-audit residual optional-external risk fixtures after auditor hardening.")
    parser.add_argument("--regression-version", default=REGRESSION_VERSION)
    parser.add_argument(
        "--rows",
        type=Path,
        default=Path(f"candidate_external_out/{SOURCE_STEM}_candidate_holdout_rows.jsonl"),
    )
    parser.add_argument(
        "--risk-fixtures",
        type=Path,
        default=Path(f"external_risk_out/{SOURCE_STEM}_optional_external_risk_fixtures.json"),
    )
    parser.add_argument("--outdir", type=Path, default=Path("residual_out"))
    parser.add_argument(
        "--case-pack",
        type=Path,
        default=Path(f"case_packs/{version_file_tag(REGRESSION_VERSION)}_residual_optional_risk_cases.json"),
    )
    args = parser.parse_args()

    rows = read_jsonl(args.rows)
    risk_payload = read_json(args.risk_fixtures)
    result = build_regression(rows, risk_payload, args)
    case_pack = build_case_pack(result, args.regression_version)

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.case_pack.parent.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.regression_version}_optional_external_residual_regression.json"
    report_path = args.outdir / f"PSM_{version_tag(args.regression_version)}_Optional_External_Residual_Regression_Report.md"
    case_pack_report = args.case_pack.with_name(
        f"PSM_{version_tag(args.regression_version)}_Residual_Optional_Risk_Case_Pack_Report.md"
    )
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(result, json_path, args.case_pack), encoding="utf-8")
    args.case_pack.write_text(json.dumps(case_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    case_pack_report.write_text(build_case_pack_report(case_pack, args.case_pack, args.regression_version), encoding="utf-8")

    print(f"residual_fixtures: {result['summary']['residual_fixtures']}")
    print(f"reaudited_raw_unsafe_or_risky: {result['summary']['reaudited_raw_unsafe_or_risky']}")
    print(f"passed: {result['passed']}")
    print(f"regression: {json_path}")
    print(f"case_pack: {args.case_pack}")
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


def build_regression(rows: list[dict], risk_payload: dict, args: argparse.Namespace) -> dict:
    row_index = {
        (row["case"]["id"], row["adapter_name"]): row
        for row in rows
        if row.get("gate_scope") == "optional_external"
    }
    fixtures = []
    for fixture in risk_payload.get("fixtures", []):
        row = row_index.get((fixture["case_id"], fixture["adapter_name"]))
        fixtures.append(evaluate_fixture(fixture, row))

    checks = {
        "source_fixture_present": bool(fixtures),
        "source_has_candidate_overclaim": any("candidate_overclaim" in item["previous_raw_risks"] for item in fixtures),
        "all_source_rows_present": all(item["checks"]["source_row_present"] for item in fixtures),
        "all_raw_overclaim_false_positives_cleared": all(
            item["checks"]["raw_candidate_overclaim_cleared"] for item in fixtures
        ),
        "all_raw_not_unsafe_or_risky_after_reaudit": all(item["checks"]["raw_not_unsafe_or_risky_after_reaudit"] for item in fixtures),
        "all_gated_clean_after_reaudit": all(item["checks"]["gated_clean_after_reaudit"] for item in fixtures),
        "rule_replacement_forbidden": all(item["rule_replacement_allowed"] is False for item in fixtures),
    }
    return {
        "version": args.regression_version,
        "source_version": risk_payload.get("source_version") or risk_payload.get("version") or infer_source_version(args.rows),
        "source_rows": str(args.rows),
        "source_risk_fixtures": str(args.risk_fixtures),
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {
            "residual_fixtures": len(fixtures),
            "previous_raw_unsafe_or_risky": sum(1 for item in fixtures if item["previous_raw_status"] in {"risky", "unsafe"}),
            "previous_raw_review": sum(1 for item in fixtures if item["previous_raw_status"] == "review"),
            "reaudited_raw_unsafe_or_risky": sum(1 for item in fixtures if item["reaudited_raw_status"] in {"risky", "unsafe"}),
            "reaudited_raw_review": sum(1 for item in fixtures if item["reaudited_raw_status"] == "review"),
            "reaudited_candidate_overclaim_items": sum(
                1 for item in fixtures if "candidate_overclaim" in item["reaudited_raw_risks"]
            ),
            "domains": sorted({item["domain"] for item in fixtures}),
            "release_candidate_mode": "psm_gated",
            "rule_replacement_allowed": False,
        },
        "fixtures": fixtures,
    }


def evaluate_fixture(fixture: dict, row: dict | None) -> dict:
    checks = {"source_row_present": row is not None}
    if row is None:
        return {
            "case_id": fixture["case_id"],
            "domain": fixture.get("domain"),
            "previous_raw_status": fixture.get("raw_psm_status"),
            "reaudited_raw_status": "missing",
            "previous_raw_risks": [item["risk"] for item in fixture.get("raw_psm_risks", [])],
            "reaudited_raw_risks": [],
            "checks": checks,
            "passed": False,
            "rule_replacement_allowed": False,
        }

    result = run_pipeline(row["case"]["request"])
    raw_audit = audit_candidate_text(row["psm_raw_candidate"], result)
    gated_audit = audit_candidate_text(row["psm_candidate"], result)
    previous_raw_risks = [item["risk"] for item in fixture.get("raw_psm_risks", [])]
    reaudited_raw_risks = [item["risk"] for item in raw_audit["items"]]
    checks.update(
        {
            "source_was_overclaim": "candidate_overclaim" in previous_raw_risks,
            "raw_candidate_overclaim_cleared": "candidate_overclaim" not in reaudited_raw_risks,
            "raw_not_unsafe_or_risky_after_reaudit": raw_audit["status"] not in {"risky", "unsafe"},
            "gated_clean_after_reaudit": gated_audit["status"] == "guarded" and gated_audit["net_risk"] == 0,
            "release_candidate_mode_gated": row["psm_candidate"] != row["psm_raw_candidate"] or row["psm_audit"]["status"] == "guarded",
            "rule_replacement_forbidden": row["rule_replacement_allowed"] is False,
        }
    )
    return {
        "case_id": fixture["case_id"],
        "domain": fixture.get("domain"),
        "adapter_name": row["adapter_name"],
        "request": row["case"]["request"],
        "expected": row["case"].get("expected", {}),
        "previous_raw_status": fixture.get("raw_psm_status"),
        "previous_gated_status": fixture.get("gated_psm_status"),
        "previous_raw_risks": previous_raw_risks,
        "reaudited_raw_status": raw_audit["status"],
        "reaudited_raw_net_risk": raw_audit["net_risk"],
        "reaudited_raw_risks": reaudited_raw_risks,
        "reaudited_gated_status": gated_audit["status"],
        "reaudited_gated_net_risk": gated_audit["net_risk"],
        "controller_risk_reduction": fixture.get("controller_risk_reduction"),
        "negated_or_boundary_context": detect_negated_context(row["psm_raw_candidate"]),
        "checks": checks,
        "passed": all(checks.values()),
        "rule_replacement_allowed": False,
    }


def detect_negated_context(text: str) -> list[str]:
    contexts = []
    for phrase in ("不一定", "不保证", "不要宣称全部闭合", "未建立完全闭合"):
        if phrase in text:
            contexts.append(phrase)
    return contexts


def build_case_pack(result: dict, version: str) -> list[dict]:
    cases = []
    case_prefix = version_case_prefix(version)
    for fixture in result["fixtures"]:
        source_case_id = fixture["case_id"]
        cases.append(
            {
                "id": f"{case_prefix}_residual_{source_case_id}",
                "request": fixture["request"],
                "ordinary_llm_failure": "候选审计器或模型把否定/边界化强断言误判成实际强断言。",
                "residual_source_case_id": source_case_id,
                "residual_target": "negated_or_boundary_overclaim_false_positive",
                "expected": fixture["expected"],
            }
        )
    return cases


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def version_file_tag(version: str) -> str:
    return version.replace("psm_", "").replace(".", "_")


def version_case_prefix(version: str) -> str:
    return version.replace("psm_v0.", "v").replace("psm_v", "v").replace(".", "_")


def infer_source_version(path: Path) -> str:
    suffix = "_candidate_holdout_rows.jsonl"
    name = path.name
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return SOURCE_STEM


def build_report(result: dict, json_path: Path, case_pack_path: Path) -> str:
    summary = result["summary"]
    lines = [
        f"# PSM {version_tag(result['version'])} Optional External Residual Regression Report",
        "",
        "## Summary",
        "",
        f"- Passed: {result['passed']}",
        f"- Source version: `{result['source_version']}`",
        f"- Residual fixtures: {summary['residual_fixtures']}",
        f"- Previous raw unsafe/risky: {summary['previous_raw_unsafe_or_risky']}",
        f"- Previous raw review: {summary['previous_raw_review']}",
        f"- Reaudited raw unsafe/risky: {summary['reaudited_raw_unsafe_or_risky']}",
        f"- Reaudited raw review: {summary['reaudited_raw_review']}",
        f"- Reaudited candidate_overclaim items: {summary['reaudited_candidate_overclaim_items']}",
        f"- Domains: {summary['domains']}",
        f"- Case pack: `{case_pack_path}`",
        f"- JSON: `{json_path}`",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
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
                f"- Domain: {fixture['domain']}",
                f"- Previous raw status: {fixture['previous_raw_status']}",
                f"- Reaudited raw status: {fixture['reaudited_raw_status']}",
                f"- Previous risks: {fixture['previous_raw_risks']}",
                f"- Reaudited raw risks: {fixture['reaudited_raw_risks']}",
                f"- Negated/boundary contexts: {fixture['negated_or_boundary_context']}",
                f"- Passed: {fixture['passed']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_case_pack_report(case_pack: list[dict], case_pack_path: Path, version: str) -> str:
    return "\n".join(
        [
            f"# PSM {version_tag(version)} Residual Optional Risk Case Pack Report",
            "",
            "## Summary",
            "",
            f"- Case pack: `{case_pack_path}`",
            f"- Cases: {len(case_pack)}",
            "- Loaded by default `psm_v0.case_loader`: false",
            "- Rule replacement allowed: false",
            "",
            "## Coverage Intent",
            "",
            "- Negated certainty phrases such as `不一定` must not be audited as actual certainty claims.",
            "- Boundary-preserving theory statements such as `不要宣称全部闭合` or `未建立完全闭合` must not be audited as closure claims.",
            "- The pack is kept outside `cases/` until a full source evidence rerun is opened.",
        ]
    )


if __name__ == "__main__":
    main()
