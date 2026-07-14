from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED_TOP_LEVEL = {"schema_version", "record_id", "split", "source", "input", "labels", "audits"}
REQUIRED_INPUT = {"user_request", "domain", "phi_state", "q_core", "omega_observed", "delta_sigma", "pi_cavity", "eta"}
REQUIRED_LABELS = {"q_status", "risk_level", "route", "bsigma_status", "bsigma_risks", "statement_level", "gate_score"}
FORBIDDEN_KEYS = {"expected", "ordinary_llm_failure"}
ALLOWED_SPLITS = {"train", "validation", "test"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PSM state-encoder dataset JSONL.")
    parser.add_argument("--stem", default="psm_v0.20")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("state_dataset_out"))
    args = parser.parse_args()
    if args.dataset is None:
        args.dataset = Path(f"state_dataset_out/{args.stem}_state_encoder.jsonl")

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(args.dataset)
    validation = validate_records(records)
    validation_path = args.outdir / f"{args.stem}_state_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = args.outdir / f"PSM_{stem_to_tag(args.stem)}_State_Dataset_Report.md"
    report_path.write_text(build_report(args.dataset, validation, stem_to_tag(args.stem)), encoding="utf-8")
    print(f"records: {validation['records']}")
    print(f"passed: {validation['passed']}")
    print(f"errors: {len(validation['errors'])}")
    print(f"warnings: {len(validation['warnings'])}")
    print(f"validation: {validation_path}")
    print(f"report: {report_path}")
    if not validation["passed"]:
        raise SystemExit(1)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_records(records: list[dict]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for record in records:
        record_id = record.get("record_id", "<missing>")
        missing = REQUIRED_TOP_LEVEL - set(record)
        if missing:
            errors.append(f"{record_id}: missing top-level fields {sorted(missing)}")
            continue
        if record_id in seen:
            errors.append(f"{record_id}: duplicate record_id")
        seen.add(record_id)
        if record["split"] not in ALLOWED_SPLITS:
            errors.append(f"{record_id}: invalid split {record['split']}")
        _require(record_id, "input", REQUIRED_INPUT, record["input"], errors)
        _require(record_id, "labels", REQUIRED_LABELS, record["labels"], errors)
        _check_forbidden(record_id, record, errors)
        if not str(record["input"].get("user_request", "")).strip():
            errors.append(f"{record_id}: empty user_request")
        if not isinstance(record["labels"].get("bsigma_risks"), list):
            errors.append(f"{record_id}: bsigma_risks must be a list")
        if record["labels"].get("gate_score") != 1.0:
            warnings.append(f"{record_id}: gate_score is not 1.0")

    split_counts = Counter(record.get("split") for record in records)
    for split in ALLOWED_SPLITS:
        if split_counts.get(split, 0) == 0:
            warnings.append(f"split `{split}` is empty")
    return {
        "passed": not errors,
        "records": len(records),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "splits": dict(sorted(split_counts.items())),
            "domains": dict(sorted(Counter(record["input"].get("domain") for record in records).items())),
            "risk_levels": dict(sorted(Counter(record["labels"].get("risk_level") for record in records).items())),
            "q_statuses": dict(sorted(Counter(record["labels"].get("q_status") for record in records).items())),
            "routes": dict(sorted(Counter(record["labels"].get("route") for record in records).items())),
        },
    }


def _require(record_id: str, section: str, required: set[str], actual: dict, errors: list[str]) -> None:
    missing = required - set(actual)
    if missing:
        errors.append(f"{record_id}: missing {section} fields {sorted(missing)}")


def _check_forbidden(record_id: str, value, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEYS:
                errors.append(f"{record_id}: forbidden leakage key `{key}` present")
            _check_forbidden(record_id, item, errors)
    elif isinstance(value, list):
        for item in value:
            _check_forbidden(record_id, item, errors)


def stem_to_tag(stem: str) -> str:
    return stem.replace("psm_v", "V")


def build_report(dataset_path: Path, validation: dict, version_tag: str) -> str:
    summary = validation["summary"]
    lines = [
        f"# PSM {version_tag} State Dataset Report",
        "",
        "## Summary",
        "",
        f"- Dataset: `{dataset_path}`",
        f"- Records: {validation['records']}",
        f"- Validation passed: {validation['passed']}",
        f"- Errors: {len(validation['errors'])}",
        f"- Warnings: {len(validation['warnings'])}",
        f"- Splits: {summary['splits']}",
        f"- Domains: {summary['domains']}",
        f"- Risk levels: {summary['risk_levels']}",
        f"- Q statuses: {summary['q_statuses']}",
        f"- Routes: {summary['routes']}",
        "",
        "## Boundary",
        "",
        "- This dataset excludes `expected` and `ordinary_llm_failure` fields.",
        "- Labels are generated from the executable PSM pipeline and eval outputs.",
        "- The dataset is intended for state-encoder baseline experiments, not candidate-generation training.",
        "",
        "## Validation",
        "",
    ]
    lines.append("- No validation errors." if not validation["errors"] else "Errors:")
    lines.extend(f"- {error}" for error in validation["errors"])
    lines.append("")
    lines.append("- No validation warnings." if not validation["warnings"] else "Warnings:")
    lines.extend(f"- {warning}" for warning in validation["warnings"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
