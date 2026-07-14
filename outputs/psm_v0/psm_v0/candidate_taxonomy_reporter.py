from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


REPORT_VERSION = "psm_v0.21"
SOURCE_STEM = "psm_v0.21"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a machine-readable candidate-output taxonomy report.")
    parser.add_argument("--source-stem", default=SOURCE_STEM)
    parser.add_argument("--report-version", default=REPORT_VERSION)
    parser.add_argument("--rows", type=Path, default=None)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("taxonomy_out"))
    args = parser.parse_args()
    if args.rows is None:
        args.rows = Path(f"candidate_external_out/{args.source_stem}_candidate_holdout_rows.jsonl")
    if args.ledger is None:
        args.ledger = Path(f"candidate_external_out/{args.source_stem}_candidate_failure_ledger.jsonl")
    if args.metrics is None:
        args.metrics = Path(f"candidate_external_out/{args.source_stem}_candidate_holdout_metrics.json")

    rows = read_jsonl(args.rows)
    ledger_events = read_jsonl(args.ledger)
    metrics = read_json(args.metrics)
    taxonomy = build_taxonomy(
        rows=rows,
        ledger_events=ledger_events,
        metrics=metrics,
        source_paths=args,
        report_version=args.report_version,
        source_stem=args.source_stem,
    )

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.report_version}_candidate_taxonomy.json"
    md_path = args.outdir / f"PSM_{version_tag(args.report_version)}_Candidate_Taxonomy_Report.md"
    json_path.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_report(taxonomy, json_path), encoding="utf-8")

    print(f"rows: {taxonomy['summary']['rows']}")
    print(f"ledger_events: {taxonomy['summary']['ledger_events']}")
    print(f"invariants_passed: {taxonomy['invariants']['passed']}")
    print(f"taxonomy: {json_path}")
    print(f"report: {md_path}")
    if not taxonomy["invariants"]["passed"]:
        raise SystemExit(1)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_taxonomy(
    *,
    rows: list[dict],
    ledger_events: list[dict],
    metrics: dict,
    source_paths: argparse.Namespace,
    report_version: str,
    source_stem: str,
) -> dict:
    row_groups = Counter()
    audit_groups = Counter()
    ledger_groups = Counter()
    adapter_domain_counts = Counter()
    fault_modes = Counter()
    case_domains = {
        event["case_id"]: event["domain"]
        for event in ledger_events
        if event.get("case_id") and event.get("domain")
    }

    for row in rows:
        case = row["case"]
        domain = domain_of(row, case_domains)
        adapter = row["adapter_name"]
        gate_scope = row["gate_scope"]
        fault_mode = row.get("fault_mode") or "none"
        row_groups[(gate_scope, adapter)] += 1
        adapter_domain_counts[(gate_scope, adapter, domain)] += 1
        if row.get("fault_injection"):
            fault_modes[fault_mode] += 1
        for mode, audit_key in (
            ("ordinary", "ordinary_audit"),
            ("psm_raw", "psm_raw_audit"),
            ("psm_gated", "psm_audit"),
        ):
            audit = row[audit_key]
            for item in audit["items"]:
                audit_groups[(gate_scope, adapter, domain, mode, item["risk"], item["severity"])] += 1
        if not case.get("id"):
            audit_groups[(gate_scope, adapter, domain, "case", "missing_case_id", "critical")] += 1

    for event in ledger_events:
        ledger_groups[
            (
                event.get("gate_scope", "unknown"),
                event.get("adapter_name", event.get("adapter", "unknown")),
                event.get("domain", "unknown"),
                event.get("ledger_group", "unknown"),
                event.get("risk", "unknown"),
                event.get("severity", "unknown"),
            )
        ] += 1

    invariants = check_invariants(metrics=metrics, ledger_events=ledger_events)
    return {
        "version": report_version,
        "source_version": source_stem,
        "source_paths": {
            "rows": str(source_paths.rows),
            "ledger": str(source_paths.ledger),
            "metrics": str(source_paths.metrics),
        },
        "summary": {
            "rows": len(rows),
            "ledger_events": len(ledger_events),
            "adapters_run": metrics.get("adapters_run", []),
            "required_gate_adapters": metrics.get("required_gate_adapters", []),
            "optional_external_adapters": metrics.get("optional_external_adapters", []),
            "fault_injection_adapters": metrics.get("fault_injection_adapters", []),
            "rule_replacement_allowed": metrics.get("rule_replacement_allowed"),
        },
        "metrics_snapshot": {
            "state_prediction_clean": metrics.get("state_prediction_clean"),
            "candidate_text_clean": metrics.get("candidate_text_clean"),
            "external_candidate_text_clean": metrics.get("external_candidate_text_clean"),
            "fault_injection_events": metrics.get("fault_injection_events"),
            "ledger_group_counts": metrics.get("ledger_group_counts", {}),
            "adapter_failure_types": metrics.get("adapter_failure_types", {}),
            "controller_rescue_count": metrics.get("controller_rescue_count"),
            "controller_risk_reduction": metrics.get("controller_risk_reduction"),
        },
        "row_groups": counter_to_records(row_groups, ["gate_scope", "adapter_name"]),
        "adapter_domain_counts": counter_to_records(adapter_domain_counts, ["gate_scope", "adapter_name", "domain"]),
        "audit_groups": counter_to_records(
            audit_groups,
            ["gate_scope", "adapter_name", "domain", "candidate_mode", "risk", "severity"],
        ),
        "ledger_groups": counter_to_records(
            ledger_groups,
            ["gate_scope", "adapter_name", "domain", "ledger_group", "risk", "severity"],
        ),
        "fault_modes": counter_to_records(fault_modes, ["fault_mode"]),
        "invariants": invariants,
    }


def domain_of(row: dict, case_domains: dict[str, str]) -> str:
    case = row.get("case", {})
    if case.get("domain"):
        return case["domain"]
    if case.get("id") in case_domains:
        return case_domains[case["id"]]
    return "unknown"


def check_invariants(*, metrics: dict, ledger_events: list[dict]) -> dict:
    checks = {
        "state_prediction_clean": metrics.get("state_prediction_clean") is True,
        "required_candidate_text_clean": metrics.get("candidate_text_clean") is True,
        "external_candidate_text_clean": metrics.get("external_candidate_text_clean") in {True, None},
        "required_gated_psm_zero": metrics.get("gated_psm_unsafe_or_risky") == 0,
        "optional_gated_psm_zero": metrics.get("optional_gated_psm_unsafe_or_risky") == 0,
        "fault_gated_psm_zero": metrics.get("fault_gated_psm_unsafe_or_risky") == 0,
        "required_adapter_failures_zero": metrics.get("adapter_failures") == 0,
        "fault_adapter_failures_present": metrics.get("fault_adapter_failures", 0) > 0,
        "controller_rescue_present": metrics.get("controller_rescue_count", 0) > 0,
        "rule_replacement_forbidden": metrics.get("rule_replacement_allowed") is False,
        "typed_failures_present": {"empty_output", "malformed_json", "timeout"}.issubset(
            set(metrics.get("adapter_failure_types", {}))
        ),
        "ledger_has_controller_rescue": any(event.get("ledger_group") == "controller_rescue" for event in ledger_events),
        "ledger_has_adapter_failure": any(event.get("ledger_group") == "adapter_failure" for event in ledger_events),
        "ledger_has_raw_psm_risk": any(event.get("ledger_group") == "raw_psm_risk" for event in ledger_events),
    }
    return {"passed": all(checks.values()), "checks": checks}


def counter_to_records(counter: Counter, fields: list[str]) -> list[dict]:
    records = []
    for key, count in sorted(counter.items()):
        if not isinstance(key, tuple):
            key = (key,)
        record = {field: value for field, value in zip(fields, key)}
        record["count"] = count
        records.append(record)
    return records


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(taxonomy: dict, json_path: Path) -> str:
    summary = taxonomy["summary"]
    metrics = taxonomy["metrics_snapshot"]
    invariants = taxonomy["invariants"]
    lines = [
        f"# PSM {version_tag(taxonomy['version'])} Candidate Taxonomy Report",
        "",
        "## Summary",
        "",
        f"- Source version: `{taxonomy['source_version']}`",
        f"- Rows: {summary['rows']}",
        f"- Ledger events: {summary['ledger_events']}",
        f"- Required gate adapters: {summary['required_gate_adapters']}",
        f"- Optional external adapters: {summary['optional_external_adapters']}",
        f"- Fault injection adapters: {summary['fault_injection_adapters']}",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
        f"- Machine-readable taxonomy: `{json_path}`",
        "",
        "## Gate Metrics",
        "",
        f"- State prediction clean: {metrics['state_prediction_clean']}",
        f"- Required candidate text clean: {metrics['candidate_text_clean']}",
        f"- Optional external candidate text clean: {metrics['external_candidate_text_clean']}",
        f"- Fault injection events: {metrics['fault_injection_events']}",
        f"- Ledger group counts: {metrics['ledger_group_counts']}",
        f"- Adapter failure types: {metrics['adapter_failure_types']}",
        f"- Controller rescue count: {metrics['controller_rescue_count']}",
        f"- Controller risk reduction: {metrics['controller_risk_reduction']}",
        "",
        "## Invariants",
        "",
        f"- Passed: {invariants['passed']}",
    ]
    for name, passed in invariants["checks"].items():
        lines.append(f"- {name}: {passed}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This taxonomy is an evidence index over the V0.21 optional-external candidate-output run.",
            "- It does not re-authorize rule replacement.",
            "- It exists to make future recovery, regression checks, and failure review deterministic.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
