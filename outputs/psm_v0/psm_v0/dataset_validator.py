from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED_TOP_LEVEL = {"schema_version", "record_id", "split", "source", "input", "labels", "outputs", "audits", "metrics"}
REQUIRED_INPUT = {"user_request", "domain", "phi_state", "q_core", "omega", "delta_sigma", "pi_cavity", "eta"}
REQUIRED_LABELS = {
    "q_status",
    "risk_level",
    "route",
    "bsigma_status",
    "bsigma_risks",
    "ordinary_status",
    "ordinary_net_risk",
    "raw_psm_status",
    "raw_psm_net_risk",
    "gated_psm_status",
    "gated_psm_net_risk",
    "controller_changed_output",
    "controller_rescued",
    "controller_risk_reduction",
}
REQUIRED_OUTPUTS = {"ordinary_candidate", "raw_psm_candidate", "gated_psm_candidate"}
FORBIDDEN_KEYS = {"expected", "ordinary_llm_failure"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate exported PSM training dataset JSONL.")
    parser.add_argument("--dataset", type=Path, default=Path("dataset_out/psm_v0.7_training.jsonl"))
    parser.add_argument("--outdir", type=Path, default=Path("dataset_out"))
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    validation = validate_records(records)
    validation_path = args.outdir / "psm_v0.7_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = args.outdir / "PSM_V0.7_Dataset_Report.md"
    report_path.write_text(build_report(args.dataset, validation), encoding="utf-8")
    print(f"records: {validation['records']}")
    print(f"passed: {validation['passed']}")
    print(f"errors: {len(validation['errors'])}")
    print(f"warnings: {len(validation['warnings'])}")
    print(f"validation: {validation_path}")
    print(f"report: {report_path}")
    if not validation["passed"]:
        raise SystemExit(1)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL at line {line_no}: {exc}") from exc
    return records


def validate_records(records: list[dict]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        record_id = record.get("record_id", f"line_{index}")
        missing = REQUIRED_TOP_LEVEL - set(record)
        if missing:
            errors.append(f"{record_id}: missing top-level fields {sorted(missing)}")
            continue
        if record_id in seen_ids:
            errors.append(f"{record_id}: duplicate record_id")
        seen_ids.add(record_id)

        _require_subset(record_id, "input", REQUIRED_INPUT, record["input"], errors)
        _require_subset(record_id, "labels", REQUIRED_LABELS, record["labels"], errors)
        _require_subset(record_id, "outputs", REQUIRED_OUTPUTS, record["outputs"], errors)
        _check_forbidden_keys(record_id, record, errors)
        _check_non_empty_outputs(record_id, record, errors)
        _check_label_consistency(record_id, record, errors)
        _check_gate_boundary(record_id, record, errors, warnings)

    return {
        "passed": not errors,
        "records": len(records),
        "errors": errors,
        "warnings": warnings,
        "summary": build_summary(records),
    }


def _require_subset(record_id: str, section: str, required: set[str], actual: dict, errors: list[str]) -> None:
    missing = required - set(actual)
    if missing:
        errors.append(f"{record_id}: missing {section} fields {sorted(missing)}")


def _check_forbidden_keys(record_id: str, value, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEYS:
                errors.append(f"{record_id}: forbidden leakage key `{key}` present")
            _check_forbidden_keys(record_id, item, errors)
    elif isinstance(value, list):
        for item in value:
            _check_forbidden_keys(record_id, item, errors)


def _check_non_empty_outputs(record_id: str, record: dict, errors: list[str]) -> None:
    for key in REQUIRED_OUTPUTS:
        if not str(record["outputs"].get(key, "")).strip():
            errors.append(f"{record_id}: output `{key}` is empty")


def _check_label_consistency(record_id: str, record: dict, errors: list[str]) -> None:
    labels = record["labels"]
    audit_map = {
        "ordinary": record["audits"]["ordinary_candidate_audit"],
        "raw_psm": record["audits"]["raw_psm_candidate_audit"],
        "gated_psm": record["audits"]["gated_psm_candidate_audit"],
    }
    for prefix, audit in audit_map.items():
        if labels[f"{prefix}_status"] != audit["status"]:
            errors.append(f"{record_id}: {prefix} status label does not match audit")
        if labels[f"{prefix}_net_risk"] != audit["net_risk"]:
            errors.append(f"{record_id}: {prefix} net risk label does not match audit")

    expected_controller_reduction = labels["raw_psm_net_risk"] - labels["gated_psm_net_risk"]
    if labels["controller_risk_reduction"] != expected_controller_reduction:
        errors.append(f"{record_id}: controller risk reduction mismatch")
    if labels["controller_rescued"] != (expected_controller_reduction > 0):
        errors.append(f"{record_id}: controller rescued flag mismatch")


def _check_gate_boundary(record_id: str, record: dict, errors: list[str], warnings: list[str]) -> None:
    labels = record["labels"]
    if labels["gated_psm_net_risk"] > labels["raw_psm_net_risk"]:
        errors.append(f"{record_id}: gated PSM risk is higher than raw PSM risk")
    if labels["gated_psm_unsafe_or_risky"]:
        errors.append(f"{record_id}: gated PSM candidate remains unsafe/risky")
    if labels["risk_level"] in {"high", "critical"} and not labels["controller_changed_output"]:
        warnings.append(f"{record_id}: high-risk record was not changed by controller")


def build_summary(records: list[dict]) -> dict:
    domains = Counter(record["input"].get("domain") for record in records)
    q_statuses = Counter(record["labels"].get("q_status") for record in records)
    risks = Counter(record["labels"].get("risk_level") for record in records)
    return {
        "domains": dict(sorted(domains.items())),
        "q_statuses": dict(sorted(q_statuses.items())),
        "risk_levels": dict(sorted(risks.items())),
        "ordinary_total_net_risk": sum(record["labels"]["ordinary_net_risk"] for record in records),
        "raw_psm_total_net_risk": sum(record["labels"]["raw_psm_net_risk"] for record in records),
        "gated_psm_total_net_risk": sum(record["labels"]["gated_psm_net_risk"] for record in records),
        "controller_rescue_count": sum(1 for record in records if record["labels"]["controller_rescued"]),
        "controller_risk_reduction": sum(record["labels"]["controller_risk_reduction"] for record in records),
    }


def build_report(dataset_path: Path, validation: dict) -> str:
    summary = validation["summary"]
    lines = [
        "# PSM V0.7 Dataset Report",
        "",
        "## Summary",
        "",
        f"- Dataset: `{dataset_path}`",
        f"- Records: {validation['records']}",
        f"- Validation passed: {validation['passed']}",
        f"- Errors: {len(validation['errors'])}",
        f"- Warnings: {len(validation['warnings'])}",
        f"- Domains: {summary['domains']}",
        f"- Q statuses: {summary['q_statuses']}",
        f"- Risk levels: {summary['risk_levels']}",
        f"- Ordinary total net risk: {summary['ordinary_total_net_risk']}",
        f"- Raw PSM total net risk: {summary['raw_psm_total_net_risk']}",
        f"- Gated PSM total net risk: {summary['gated_psm_total_net_risk']}",
        f"- Controller rescue count: {summary['controller_rescue_count']}",
        f"- Controller risk reduction: {summary['controller_risk_reduction']}",
        "",
        "## Dataset Boundary",
        "",
        "- `input` excludes case `expected` labels and `ordinary_llm_failure` hints.",
        "- `labels` are derived from actual pipeline, candidate audit, and controller-ablation outputs.",
        "- `outputs` preserve ordinary, raw PSM, and gated PSM candidates for future state-encoder and reward-model experiments.",
        "",
        "## Validation",
        "",
    ]
    if validation["errors"]:
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in validation["errors"])
        lines.append("")
    else:
        lines.append("- No validation errors.")
        lines.append("")
    if validation["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in validation["warnings"])
        lines.append("")
    else:
        lines.append("- No validation warnings.")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
