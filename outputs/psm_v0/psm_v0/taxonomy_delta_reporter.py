from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


DELTA_VERSION = "psm_v0.21"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two candidate taxonomy JSON files.")
    parser.add_argument("--delta-version", default=DELTA_VERSION)
    parser.add_argument("--baseline", type=Path, default=Path("taxonomy_out/psm_v0.20_candidate_taxonomy.json"))
    parser.add_argument("--current", type=Path, default=Path("taxonomy_external_out/psm_v0.21_candidate_taxonomy.json"))
    parser.add_argument("--outdir", type=Path, default=Path("taxonomy_external_delta_out"))
    args = parser.parse_args()

    baseline = read_json(args.baseline)
    current = read_json(args.current)
    delta = build_delta(baseline, current, args.baseline, args.current, args.delta_version)

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.delta_version}_taxonomy_delta.json"
    report_path = args.outdir / f"PSM_{version_tag(args.delta_version)}_Taxonomy_Delta_Report.md"
    json_path.write_text(json.dumps(delta, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(delta, json_path), encoding="utf-8")

    print(f"changed_groups: {delta['summary']['changed_groups']}")
    print(f"unexpected_regression: {delta['summary']['unexpected_regression']}")
    print(f"delta_json: {json_path}")
    print(f"report: {report_path}")
    if delta["summary"]["unexpected_regression"]:
        raise SystemExit(1)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_delta(baseline: dict, current: dict, baseline_path: Path, current_path: Path, delta_version: str) -> dict:
    baseline_groups = group_counter(baseline.get("ledger_groups", []))
    current_groups = group_counter(current.get("ledger_groups", []))
    keys = sorted(set(baseline_groups) | set(current_groups))
    deltas = []
    for key in keys:
        before = baseline_groups.get(key, 0)
        after = current_groups.get(key, 0)
        if before != after:
            record = {field: value for field, value in zip(group_fields(), key)}
            record.update({"baseline_count": before, "current_count": after, "delta": after - before})
            deltas.append(record)

    invariant_changes = compare_invariants(baseline, current)
    unexpected_regression = any(change["current"] is False and change["baseline"] is True for change in invariant_changes)
    return {
        "version": delta_version,
        "baseline": str(baseline_path),
        "current": str(current_path),
        "summary": {
            "changed_groups": len(deltas),
            "invariant_changes": len(invariant_changes),
            "unexpected_regression": unexpected_regression,
            "rule_replacement_allowed": False,
        },
        "ledger_group_deltas": deltas,
        "invariant_changes": invariant_changes,
    }


def group_counter(records: list[dict]) -> Counter:
    counts = Counter()
    for record in records:
        key = tuple(record.get(field, "unknown") for field in group_fields())
        counts[key] = record.get("count", 0)
    return counts


def group_fields() -> list[str]:
    return ["gate_scope", "adapter_name", "domain", "ledger_group", "risk", "severity"]


def compare_invariants(baseline: dict, current: dict) -> list[dict]:
    before = baseline.get("invariants", {}).get("checks", {})
    after = current.get("invariants", {}).get("checks", {})
    changes = []
    for name in sorted(set(before) | set(after)):
        if before.get(name) != after.get(name):
            changes.append({"check": name, "baseline": before.get(name), "current": after.get(name)})
    return changes


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(delta: dict, json_path: Path) -> str:
    summary = delta["summary"]
    lines = [
        f"# PSM {version_tag(delta['version'])} Taxonomy Delta Report",
        "",
        "## Summary",
        "",
        f"- Baseline: `{delta['baseline']}`",
        f"- Current: `{delta['current']}`",
        f"- Changed groups: {summary['changed_groups']}",
        f"- Invariant changes: {summary['invariant_changes']}",
        f"- Unexpected regression: {summary['unexpected_regression']}",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
        f"- JSON: `{json_path}`",
        "",
        "## Boundary",
        "",
        "- This report is a future comparison hook.",
        "- A baseline compared with itself should produce zero changed groups.",
        "- Any invariant changing from true to false is treated as regression.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
