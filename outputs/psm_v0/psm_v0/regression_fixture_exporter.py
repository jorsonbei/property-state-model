from __future__ import annotations

import argparse
import json
from pathlib import Path


FIXTURE_VERSION = "psm_v0.20"
SOURCE_STEM = "psm_v0.20"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export representative candidate-output regression fixtures.")
    parser.add_argument("--fixture-version", default=FIXTURE_VERSION)
    parser.add_argument("--source-stem", default=SOURCE_STEM)
    parser.add_argument("--rows", type=Path, default=None)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("fixtures_out"))
    args = parser.parse_args()
    if args.rows is None:
        args.rows = Path(f"candidate_holdout_out/{args.source_stem}_candidate_holdout_rows.jsonl")
    if args.ledger is None:
        args.ledger = Path(f"candidate_holdout_out/{args.source_stem}_candidate_failure_ledger.jsonl")

    rows = read_jsonl(args.rows)
    ledger_events = read_jsonl(args.ledger)
    fixtures = build_fixtures(rows, ledger_events, args.fixture_version, args.source_stem)

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.fixture_version}_candidate_regression_fixtures.json"
    report_path = args.outdir / f"PSM_{version_tag(args.fixture_version)}_Candidate_Regression_Fixtures_Report.md"
    json_path.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(fixtures, json_path), encoding="utf-8")

    print(f"fixtures: {len(fixtures['fixtures'])}")
    print(f"coverage_passed: {fixtures['coverage']['passed']}")
    print(f"fixtures_json: {json_path}")
    print(f"report: {report_path}")
    if not fixtures["coverage"]["passed"]:
        raise SystemExit(1)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_fixtures(rows: list[dict], ledger_events: list[dict], fixture_version: str = FIXTURE_VERSION, source_stem: str = SOURCE_STEM) -> dict:
    has_optional_external = any(row["gate_scope"] == "optional_external" for row in rows)
    fixture_specs = [
        ("required_ordinary_risk", lambda row: row["gate_scope"] == "required" and row["ordinary_audit"]["items"]),
        ("fault_boundary_rescue", lambda row: row.get("fault_mode") == "boundary_erasure" and row["controller_rescued"]),
        ("fault_malformed_json", lambda row: row.get("fault_mode") == "malformed_json" and not row["ordinary_adapter_ok"]),
        ("fault_empty_stdout", lambda row: row.get("fault_mode") == "empty_stdout" and not row["ordinary_adapter_ok"]),
        ("fault_timeout", lambda row: row.get("fault_mode") == "timeout" and not row["ordinary_adapter_ok"]),
        ("clean_required_psm", lambda row: row["gate_scope"] == "required" and row["psm_audit"]["status"] == "guarded"),
    ]
    if has_optional_external:
        fixture_specs.insert(
            1,
            ("optional_raw_psm_rescue", lambda row: row["gate_scope"] == "optional_external" and row["controller_rescued"]),
        )
    fixtures = []
    for name, predicate in fixture_specs:
        row = next((item for item in rows if predicate(item)), None)
        if row is None:
            fixtures.append({"fixture": name, "present": False})
            continue
        fixtures.append(build_fixture(name, row, ledger_events))

    coverage = {
        "required": [name for name, _ in fixture_specs],
        "present": [item["fixture"] for item in fixtures if item.get("present")],
    }
    coverage["missing"] = [name for name in coverage["required"] if name not in coverage["present"]]
    coverage["passed"] = not coverage["missing"]
    return {
        "version": fixture_version,
        "source_version": source_stem,
        "coverage": coverage,
        "fixtures": fixtures,
        "rule_replacement_allowed": False,
    }


def build_fixture(name: str, row: dict, ledger_events: list[dict]) -> dict:
    case_id = row["case"]["id"]
    related_events = [
        event
        for event in ledger_events
        if event.get("case_id") == case_id and event.get("adapter_name") == row["adapter_name"]
    ]
    return {
        "fixture": name,
        "present": True,
        "case_id": case_id,
        "adapter_name": row["adapter_name"],
        "gate_scope": row["gate_scope"],
        "fault_mode": row.get("fault_mode"),
        "ordinary_adapter_ok": row["ordinary_adapter_ok"],
        "psm_adapter_ok": row["psm_adapter_ok"],
        "ordinary_status": row["ordinary_audit"]["status"],
        "raw_psm_status": row["psm_raw_audit"]["status"],
        "gated_psm_status": row["psm_audit"]["status"],
        "ordinary_error_type": row.get("ordinary_error_type"),
        "psm_error_type": row.get("psm_error_type"),
        "controller_rescued": row["controller_rescued"],
        "controller_risk_reduction": row["controller_risk_reduction"],
        "ledger_groups": sorted({event.get("ledger_group") for event in related_events if event.get("ledger_group")}),
        "risks": sorted({event.get("risk") for event in related_events if event.get("risk")}),
        "rule_replacement_allowed": False,
    }


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(payload: dict, json_path: Path) -> str:
    lines = [
        f"# PSM {version_tag(payload['version'])} Candidate Regression Fixtures Report",
        "",
        "## Summary",
        "",
        f"- Source version: `{payload['source_version']}`",
        f"- Fixtures: {len(payload['fixtures'])}",
        f"- Coverage passed: {payload['coverage']['passed']}",
        f"- Missing: {payload['coverage']['missing']}",
        f"- JSON: `{json_path}`",
        f"- Rule replacement allowed: {payload['rule_replacement_allowed']}",
        "",
        "## Fixtures",
        "",
    ]
    for fixture in payload["fixtures"]:
        lines.extend(
            [
                f"### {fixture['fixture']}",
                "",
                f"- Present: {fixture.get('present')}",
                f"- Case: {fixture.get('case_id')}",
                f"- Adapter: {fixture.get('adapter_name')}",
                f"- Gate scope: {fixture.get('gate_scope')}",
                f"- Fault mode: {fixture.get('fault_mode')}",
                f"- Ordinary status: {fixture.get('ordinary_status')}",
                f"- Raw PSM status: {fixture.get('raw_psm_status')}",
                f"- Gated PSM status: {fixture.get('gated_psm_status')}",
                f"- Controller rescued: {fixture.get('controller_rescued')}",
                f"- Ledger groups: {fixture.get('ledger_groups')}",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
