from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidate_auditor import audit_candidate_text
from .compare_runner import adapter_failure_audit
from .holdout_candidate_compare_runner import build_adapter_metrics, build_metrics
from .pipeline import run_pipeline
from .psm_gate_controller import apply_psm_gate


REAUDIT_VERSION = "psm_v0.25"
SOURCE_STEM = "psm_v0.24"


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-audit existing optional-external candidate rows under current auditor/controller.")
    parser.add_argument("--reaudit-version", default=REAUDIT_VERSION)
    parser.add_argument(
        "--source-rows",
        type=Path,
        default=Path(f"candidate_external_out/{SOURCE_STEM}_candidate_holdout_rows.jsonl"),
    )
    parser.add_argument(
        "--source-metrics",
        type=Path,
        default=Path(f"candidate_external_out/{SOURCE_STEM}_candidate_holdout_metrics.json"),
    )
    parser.add_argument("--outdir", type=Path, default=Path("candidate_external_reaudit_out"))
    args = parser.parse_args()

    source_rows = read_jsonl(args.source_rows)
    source_metrics = read_json(args.source_metrics)
    reaudited_rows = reaudited_candidate_rows(source_rows, args.reaudit_version)
    metrics = build_reaudit_metrics(reaudited_rows, source_metrics, args.reaudit_version)

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows_path = args.outdir / f"{args.reaudit_version}_candidate_reaudit_rows.jsonl"
    metrics_path = args.outdir / f"{args.reaudit_version}_candidate_reaudit_metrics.json"
    report_path = args.outdir / f"PSM_{version_tag(args.reaudit_version)}_Candidate_Reaudit_Report.md"
    rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in reaudited_rows), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(metrics, args.source_rows, rows_path, metrics_path), encoding="utf-8")

    optional = optional_adapter_metrics(metrics)
    print(f"rows: {len(reaudited_rows)}")
    print(f"external_candidate_text_clean: {metrics['external_candidate_text_clean']}")
    print(f"optional_raw_psm_unsafe_or_risky: {optional.get('raw_psm_unsafe_or_risky')}")
    print(f"optional_gated_psm_unsafe_or_risky: {optional.get('gated_psm_unsafe_or_risky')}")
    print(f"report: {report_path}")
    if not metrics["candidate_text_clean"] or metrics["external_candidate_text_clean"] is not True:
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


def reaudited_candidate_rows(rows: list[dict], reaudit_version: str) -> list[dict]:
    pipeline_cache: dict[str, dict] = {}
    reaudited = []
    for row in rows:
        case = row["case"]
        case_id = case["id"]
        if case_id not in pipeline_cache:
            pipeline_cache[case_id] = run_pipeline(case["request"])
        result = pipeline_cache[case_id]
        ordinary_audit = (
            audit_candidate_text(row["ordinary_candidate"], result)
            if row["ordinary_adapter_ok"]
            else adapter_failure_audit(row["ordinary_error"])
        )
        psm_raw_audit = (
            audit_candidate_text(row["psm_raw_candidate"], result)
            if row["psm_adapter_ok"]
            else adapter_failure_audit(row["psm_error"])
        )
        psm_candidate = apply_psm_gate(row["psm_raw_candidate"], result) if row["psm_adapter_ok"] else row["psm_raw_candidate"]
        psm_audit = (
            audit_candidate_text(psm_candidate, result)
            if row["psm_adapter_ok"]
            else adapter_failure_audit(row["psm_error"])
        )
        new_row = dict(row)
        new_row.update(
            {
                "version": reaudit_version,
                "source_version": row.get("version"),
                "reaudit_mode": "existing_model_text_current_auditor_and_controller",
                "psm_candidate": psm_candidate,
                "ordinary_audit": ordinary_audit,
                "psm_raw_audit": psm_raw_audit,
                "psm_audit": psm_audit,
                "risk_reduction": ordinary_audit["net_risk"] - psm_audit["net_risk"],
                "raw_psm_risk_reduction": ordinary_audit["net_risk"] - psm_raw_audit["net_risk"],
                "controller_changed_output": row["psm_raw_candidate"].strip() != psm_candidate.strip(),
                "controller_risk_reduction": psm_raw_audit["net_risk"] - psm_audit["net_risk"],
                "controller_rescued": psm_raw_audit["net_risk"] - psm_audit["net_risk"] > 0,
                "rule_replacement_allowed": False,
            }
        )
        reaudited.append(new_row)
    return reaudited


def build_reaudit_metrics(rows: list[dict], source_metrics: dict, reaudit_version: str) -> dict:
    adapter_metrics = []
    by_adapter = {name: [] for name in source_metrics.get("adapters_run", [])}
    for row in rows:
        by_adapter.setdefault(row["adapter_name"], []).append(row)
    for adapter_name, adapter_rows in by_adapter.items():
        if not adapter_rows:
            continue
        first = adapter_rows[0]
        spec = {
            "name": adapter_name,
            "gate_scope": first.get("gate_scope", "required"),
            "fault_injection": first.get("fault_injection", False),
            "fault_mode": first.get("fault_mode"),
            "case_limit": first.get("case_limit"),
        }
        adapter_metrics.append(build_adapter_metrics(spec, adapter_rows))

    cases_by_id = {}
    for row in rows:
        cases_by_id.setdefault(row["case"]["id"], row["case"])
    metrics = build_metrics(
        list(cases_by_id.values()),
        adapter_metrics,
        source_metrics.get("skipped_adapters", []),
        source_metrics.get("state_holdout_metrics", {}),
        source_metrics.get("case_prefixes", []),
        rows,
        reaudit_version,
    )
    metrics.update(
        {
            "source_version": source_metrics.get("version"),
            "source_metrics": source_metrics.get("version"),
            "reaudit_mode": "existing_model_text_current_auditor_and_controller",
        }
    )
    return metrics


def optional_adapter_metrics(metrics: dict) -> dict:
    for item in metrics.get("adapter_metrics", []):
        if item.get("gate_scope") == "optional_external":
            return item
    return {}


def version_tag(version: str) -> str:
    return version.replace("psm_v", "V")


def build_report(metrics: dict, source_rows: Path, rows_path: Path, metrics_path: Path) -> str:
    optional = optional_adapter_metrics(metrics)
    return "\n".join(
        [
            f"# PSM {version_tag(metrics['version'])} Candidate Reaudit Report",
            "",
            "## Summary",
            "",
            f"- Version: `{metrics['version']}`",
            f"- Source version: `{metrics.get('source_version')}`",
            f"- Reaudit mode: `{metrics['reaudit_mode']}`",
            f"- Rows: `{rows_path}`",
            f"- Metrics: `{metrics_path}`",
            f"- Source rows: `{source_rows}`",
            f"- External candidate text clean: {metrics['external_candidate_text_clean']}",
            f"- Required gated PSM unsafe/risky: {metrics['gated_psm_unsafe_or_risky']}",
            f"- Optional raw PSM unsafe/risky: {optional.get('raw_psm_unsafe_or_risky')}",
            f"- Optional gated PSM unsafe/risky: {optional.get('gated_psm_unsafe_or_risky')}",
            f"- Optional controller rescue count: {optional.get('controller_rescue_count')}",
            f"- Optional controller risk reduction: {optional.get('controller_risk_reduction')}",
            f"- Rule replacement allowed: {metrics['rule_replacement_allowed']}",
            "",
            "## Boundary",
            "",
            "- This report does not call external models.",
            "- It reuses existing model text and recomputes audits/gating under the current auditor/controller.",
            "- It does not authorize rule replacement.",
        ]
    )


if __name__ == "__main__":
    main()
