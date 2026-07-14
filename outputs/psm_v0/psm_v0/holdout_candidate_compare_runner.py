from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .candidate_auditor import audit_candidate_text
from .case_loader import load_cases
from .compare_runner import (
    adapter_failure_audit,
    build_candidate_ledger_events,
    count_adapter_failures,
    generate_with_metrics,
)
from .failure_ledger import append_ledger
from .model_adapter import build_model_adapter
from .pipeline import run_pipeline
from .psm_gate_controller import apply_psm_gate


VERSION_TAG = "V0.21"
DATASET_STEM = "psm_v0.21"
REFERENCE_HOLDOUT_METRICS = Path("holdout_out/psm_v0.15_holdout_stress_metrics.json")
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare candidate text outputs on a blind holdout slice.")
    parser.add_argument("--cases-dir", type=Path, default=Path("cases"))
    parser.add_argument("--dataset-stem", default=DATASET_STEM)
    parser.add_argument("--version-tag", default=VERSION_TAG)
    parser.add_argument(
        "--case-prefix",
        action="append",
        default=None,
        help="Case id prefix to include. May be repeated or comma-separated. Defaults to v15_.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("candidate_holdout_out"))
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--adapter-timeout", type=int, default=30)
    parser.add_argument("--include-ollama-if-available", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ollama-timeout", type=int, default=180)
    parser.add_argument("--include-fault-injection", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fault-case-limit", type=int, default=5)
    parser.add_argument("--fault-timeout", type=int, default=1)
    parser.add_argument("--fail-on-gated-risk", action="store_true")
    args = parser.parse_args()
    if args.ledger is None:
        args.ledger = args.outdir / f"{args.dataset_stem}_candidate_failure_ledger.jsonl"

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.ledger.exists():
        args.ledger.unlink()

    case_prefixes = normalize_case_prefixes(args.case_prefix)
    cases = [case for case in load_cases(args.cases_dir) if case["id"].startswith(tuple(case_prefixes))]
    if not cases:
        raise SystemExit(f"no cases found with prefixes {case_prefixes!r}")

    adapter_specs, skipped_adapters = build_adapter_specs(args)
    all_rows = []
    adapter_metrics = []
    for spec in adapter_specs:
        rows = run_adapter(spec, cases, args.outdir, args.ledger, args.dataset_stem)
        all_rows.extend(rows)
        adapter_metrics.append(build_adapter_metrics(spec, rows))

    state_holdout = load_state_holdout_metrics(REFERENCE_HOLDOUT_METRICS)
    metrics = build_metrics(cases, adapter_metrics, skipped_adapters, state_holdout, case_prefixes, all_rows, args.dataset_stem)
    metrics_path = args.outdir / f"{args.dataset_stem}_candidate_holdout_metrics.json"
    rows_path = args.outdir / f"{args.dataset_stem}_candidate_holdout_rows.jsonl"
    report_path = args.outdir / f"PSM_{args.version_tag}_Candidate_Holdout_Comparison_Report.md"
    rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in all_rows), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(metrics, rows_path, args.ledger, args.version_tag), encoding="utf-8")

    print(f"cases: {len(cases)}")
    print(f"adapters_run: {len(adapter_specs)}")
    print(f"skipped_adapters: {len(skipped_adapters)}")
    print(f"state_prediction_clean: {metrics['state_prediction_clean']}")
    print(f"candidate_text_clean: {metrics['candidate_text_clean']}")
    print(f"external_candidate_text_clean: {metrics['external_candidate_text_clean']}")
    print(f"fault_injection_events: {metrics['fault_injection_events']}")
    print(f"controller_rescue_count: {metrics['controller_rescue_count']}")
    print(f"gated_psm_unsafe_or_risky: {metrics['gated_psm_unsafe_or_risky']}")
    print(f"rule_replacement_allowed: {metrics['rule_replacement_allowed']}")
    print(f"ledger: {args.ledger}")
    print(f"report: {report_path}")
    if args.fail_on_gated_risk and not metrics["candidate_text_clean"]:
        raise SystemExit(1)


def build_adapter_specs(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    specs = [
        {
            "name": "builtin",
            "adapter": "builtin",
            "model_command": None,
            "timeout": args.adapter_timeout,
            "gate_scope": "required",
            "fault_injection": False,
        },
        {
            "name": "sample_command",
            "adapter": "command",
            "model_command": None,
            "timeout": args.adapter_timeout,
            "gate_scope": "required",
            "fault_injection": False,
        },
    ]
    skipped = []
    if args.include_ollama_if_available:
        base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        if ollama_available(base_url):
            tool_path = Path(__file__).resolve().parents[1] / "tools" / "ollama_model_tool.py"
            specs.append(
                {
                    "name": "ollama_command",
                    "adapter": "command",
                    "model_command": f"{sys.executable} {tool_path}",
                    "timeout": args.ollama_timeout,
                    "base_url": base_url,
                    "gate_scope": "optional_external",
                    "fault_injection": False,
                }
            )
        else:
            skipped.append({"name": "ollama_command", "reason": "local Ollama service unavailable", "base_url": base_url})
    if args.include_fault_injection:
        tool_path = Path(__file__).resolve().parents[1] / "tools" / "fault_model_tool.py"
        fault_specs = [
            ("fault_boundary_erasure", "boundary_erasure", args.adapter_timeout, None),
            ("fault_malformed_json", "malformed_json", args.adapter_timeout, args.fault_case_limit),
            ("fault_empty_stdout", "empty_stdout", args.adapter_timeout, args.fault_case_limit),
            ("fault_timeout", "timeout", args.fault_timeout, args.fault_case_limit),
        ]
        for name, fault_mode, timeout, case_limit in fault_specs:
            specs.append(
                {
                    "name": name,
                    "adapter": "command",
                    "model_command": f"env PSM_FAULT_MODE={fault_mode} {sys.executable} {tool_path}",
                    "timeout": timeout,
                    "gate_scope": "fault_injection",
                    "fault_injection": True,
                    "fault_mode": fault_mode,
                    "case_limit": case_limit,
                }
            )
    return specs, skipped


def normalize_case_prefixes(prefix_args: list[str] | None) -> list[str]:
    if not prefix_args:
        return ["v15_"]
    prefixes: list[str] = []
    for raw in prefix_args:
        for item in raw.split(","):
            item = item.strip()
            if item:
                prefixes.append(item)
    return list(dict.fromkeys(prefixes))


def ollama_available(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=2) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def run_adapter(spec: dict, cases: list[dict], outdir: Path, ledger_path: Path, dataset_stem: str) -> list[dict]:
    adapter = build_model_adapter(spec["adapter"], spec.get("model_command"), spec["timeout"])
    adapter_descriptor = adapter.descriptor() if hasattr(adapter, "descriptor") else {"adapter": spec["adapter"]}
    rows = []
    adapter_dir = outdir / spec["name"]
    adapter_dir.mkdir(parents=True, exist_ok=True)
    selected_cases = cases[: spec["case_limit"]] if spec.get("case_limit") else cases
    for case in selected_cases:
        result = run_pipeline(case["request"])
        ordinary_generation = generate_with_metrics(adapter, mode="ordinary", case=case, result=result)
        psm_generation = generate_with_metrics(adapter, mode="psm", case=case, result=result)
        ordinary_candidate = ordinary_generation["candidate"]
        psm_raw_candidate = psm_generation["candidate"]
        psm_candidate = apply_psm_gate(psm_raw_candidate, result) if psm_generation["ok"] else psm_raw_candidate
        ordinary_audit = (
            audit_candidate_text(ordinary_candidate, result)
            if ordinary_generation["ok"]
            else adapter_failure_audit(ordinary_generation["error"])
        )
        psm_raw_audit = (
            audit_candidate_text(psm_raw_candidate, result)
            if psm_generation["ok"]
            else adapter_failure_audit(psm_generation["error"])
        )
        psm_audit = (
            audit_candidate_text(psm_candidate, result)
            if psm_generation["ok"]
            else adapter_failure_audit(psm_generation["error"])
        )
        row = {
            "version": dataset_stem,
            "adapter_name": spec["name"],
            "gate_scope": spec.get("gate_scope", "required"),
            "fault_injection": bool(spec.get("fault_injection", False)),
            "fault_mode": spec.get("fault_mode"),
            "case": case,
            "adapter_descriptor": adapter_descriptor,
            "ordinary_response": ordinary_generation["response"],
            "psm_response": psm_generation["response"],
            "ordinary_adapter_ok": ordinary_generation["ok"],
            "psm_adapter_ok": psm_generation["ok"],
            "ordinary_error": ordinary_generation["error"],
            "psm_error": psm_generation["error"],
            "ordinary_error_type": classify_adapter_error(ordinary_generation["error"]),
            "psm_error_type": classify_adapter_error(psm_generation["error"]),
            "ordinary_latency_ms": ordinary_generation["latency_ms"],
            "psm_latency_ms": psm_generation["latency_ms"],
            "ordinary_candidate": ordinary_candidate,
            "psm_raw_candidate": psm_raw_candidate,
            "psm_candidate": psm_candidate,
            "ordinary_audit": ordinary_audit,
            "psm_raw_audit": psm_raw_audit,
            "psm_audit": psm_audit,
            "risk_reduction": ordinary_audit["net_risk"] - psm_audit["net_risk"],
            "raw_psm_risk_reduction": ordinary_audit["net_risk"] - psm_raw_audit["net_risk"],
            "controller_changed_output": psm_raw_candidate.strip() != psm_candidate.strip(),
            "controller_risk_reduction": psm_raw_audit["net_risk"] - psm_audit["net_risk"],
            "controller_rescued": psm_raw_audit["net_risk"] - psm_audit["net_risk"] > 0,
            "rule_replacement_allowed": False,
        }
        compare_path = adapter_dir / f"{case['id']}.compare.json"
        compare_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        events = build_candidate_ledger_events(case, result, row)
        events = annotate_candidate_ledger_events(events, row)
        events.extend(build_controller_rescue_events(case, result, row))
        append_ledger(ledger_path, events)
        rows.append(row)
    return rows


def build_adapter_metrics(spec: dict, rows: list[dict]) -> dict:
    ordinary_risk = sum(row["ordinary_audit"]["net_risk"] for row in rows)
    raw_psm_risk = sum(row["psm_raw_audit"]["net_risk"] for row in rows)
    gated_psm_risk = sum(row["psm_audit"]["net_risk"] for row in rows)
    controller_rescue_count = sum(1 for row in rows if row["controller_rescued"])
    controller_changed_count = sum(1 for row in rows if row["controller_changed_output"])
    controller_risk_reduction = sum(row["controller_risk_reduction"] for row in rows)
    return {
        "adapter_name": spec["name"],
        "gate_scope": spec.get("gate_scope", "required"),
        "fault_injection": bool(spec.get("fault_injection", False)),
        "fault_mode": spec.get("fault_mode"),
        "case_limit": spec.get("case_limit"),
        "cases": len(rows),
        "adapter_failures": count_adapter_failures(rows),
        "adapter_failure_types": count_adapter_failure_types(rows),
        "ordinary_unsafe_or_risky": count_status(rows, "ordinary_audit"),
        "raw_psm_unsafe_or_risky": count_status(rows, "psm_raw_audit"),
        "gated_psm_unsafe_or_risky": count_status(rows, "psm_audit"),
        "ordinary_total_net_risk": ordinary_risk,
        "raw_psm_total_net_risk": raw_psm_risk,
        "gated_psm_total_net_risk": gated_psm_risk,
        "raw_psm_risk_reduction": ordinary_risk - raw_psm_risk,
        "gated_psm_risk_reduction": ordinary_risk - gated_psm_risk,
        "controller_changed_count": controller_changed_count,
        "controller_rescue_count": controller_rescue_count,
        "controller_risk_reduction": controller_risk_reduction,
        "ordinary_avg_latency_ms": average_latency(rows, "ordinary"),
        "psm_avg_latency_ms": average_latency(rows, "psm"),
        "candidate_text_clean": count_status(rows, "psm_audit") == 0 and count_adapter_failures(rows) == 0,
        "rule_replacement_allowed": False,
    }


def average_latency(rows: list[dict], mode: str) -> float:
    latencies = [row[f"{mode}_latency_ms"] for row in rows if row[f"{mode}_adapter_ok"]]
    return round(sum(latencies) / len(latencies), 1) if latencies else 0.0


def count_status(rows: list[dict], audit_key: str) -> int:
    return sum(1 for row in rows if row[audit_key]["status"] in {"unsafe", "risky"})


def load_state_holdout_metrics(path: Path) -> dict:
    if not path.exists():
        return {"available": False, "no_retrain_clean": False, "path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    no_retrain = payload.get("no_retrain", {})
    return {
        "available": True,
        "path": str(path),
        "holdout_records": payload.get("holdout_records"),
        "no_retrain_clean": no_retrain.get("ledger_events") == 0 and no_retrain.get("holdout_boundary_passed") is True,
        "no_retrain_ledger_events": no_retrain.get("ledger_events"),
        "no_retrain_target_match_rates": no_retrain.get("target_match_rates", {}),
        "no_retrain_bsigma_exact_match": no_retrain.get("bsigma_exact_match"),
    }


def build_metrics(
    cases: list[dict],
    adapter_metrics: list[dict],
    skipped_adapters: list[dict],
    state_holdout: dict,
    case_prefixes: list[str],
    rows: list[dict],
    dataset_stem: str,
) -> dict:
    required_metrics = [item for item in adapter_metrics if item["gate_scope"] == "required"]
    optional_metrics = [item for item in adapter_metrics if item["gate_scope"] == "optional_external"]
    fault_metrics = [item for item in adapter_metrics if item["gate_scope"] == "fault_injection"]
    gated_psm_unsafe_or_risky = sum(item["gated_psm_unsafe_or_risky"] for item in required_metrics)
    adapter_failures = sum(item["adapter_failures"] for item in required_metrics)
    optional_gated = sum(item["gated_psm_unsafe_or_risky"] for item in optional_metrics)
    optional_failures = sum(item["adapter_failures"] for item in optional_metrics)
    fault_gated = sum(item["gated_psm_unsafe_or_risky"] for item in fault_metrics)
    fault_failures = sum(item["adapter_failures"] for item in fault_metrics)
    controller_rescue_count = sum(item["controller_rescue_count"] for item in adapter_metrics)
    controller_risk_reduction = sum(item["controller_risk_reduction"] for item in adapter_metrics)
    ledger_group_counts = count_ledger_groups(rows)
    adapter_failure_types = Counter()
    for item in adapter_metrics:
        adapter_failure_types.update(item["adapter_failure_types"])
    return {
        "version": dataset_stem,
        "case_prefix": ",".join(case_prefixes),
        "case_prefixes": case_prefixes,
        "holdout_cases": len(cases),
        "adapters_run": [item["adapter_name"] for item in adapter_metrics],
        "required_gate_adapters": [item["adapter_name"] for item in required_metrics],
        "optional_external_adapters": [item["adapter_name"] for item in optional_metrics],
        "fault_injection_adapters": [item["adapter_name"] for item in fault_metrics],
        "skipped_adapters": skipped_adapters,
        "state_holdout_metrics": state_holdout,
        "state_prediction_clean": bool(state_holdout.get("no_retrain_clean")),
        "candidate_text_clean": gated_psm_unsafe_or_risky == 0 and adapter_failures == 0,
        "external_candidate_text_clean": optional_gated == 0 and optional_failures == 0 if optional_metrics else None,
        "gated_psm_unsafe_or_risky": gated_psm_unsafe_or_risky,
        "adapter_failures": adapter_failures,
        "optional_gated_psm_unsafe_or_risky": optional_gated,
        "optional_adapter_failures": optional_failures,
        "fault_gated_psm_unsafe_or_risky": fault_gated,
        "fault_adapter_failures": fault_failures,
        "fault_injection_events": sum(ledger_group_counts.get(group, 0) for group in ("adapter_failure", "raw_psm_risk", "controller_rescue")),
        "ledger_group_counts": dict(sorted(ledger_group_counts.items())),
        "adapter_failure_types": dict(sorted(adapter_failure_types.items())),
        "controller_rescue_count": controller_rescue_count,
        "controller_risk_reduction": controller_risk_reduction,
        "adapter_metrics": adapter_metrics,
        "rule_replacement_allowed": False,
    }


def build_report(metrics: dict, rows_path: Path, ledger_path: Path, version_tag: str) -> str:
    lines = [
        f"# PSM {version_tag} Candidate Holdout Comparison Report",
        "",
        "## Summary",
        "",
        f"- Holdout case prefix: `{metrics['case_prefix']}`",
        f"- Holdout case prefixes: {metrics.get('case_prefixes')}",
        f"- Holdout cases: {metrics['holdout_cases']}",
        f"- Adapters run: {metrics['adapters_run']}",
        f"- Required gate adapters: {metrics['required_gate_adapters']}",
        f"- Optional external adapters: {metrics['optional_external_adapters']}",
        f"- Fault injection adapters: {metrics['fault_injection_adapters']}",
        f"- Skipped adapters: {metrics['skipped_adapters']}",
        f"- State prediction clean: {metrics['state_prediction_clean']}",
        f"- Required candidate text clean: {metrics['candidate_text_clean']}",
        f"- Optional external candidate text clean: {metrics['external_candidate_text_clean']}",
        f"- Required gated PSM unsafe/risky: {metrics['gated_psm_unsafe_or_risky']}",
        f"- Required adapter failures: {metrics['adapter_failures']}",
        f"- Optional gated PSM unsafe/risky: {metrics['optional_gated_psm_unsafe_or_risky']}",
        f"- Optional adapter failures: {metrics['optional_adapter_failures']}",
        f"- Fault gated PSM unsafe/risky: {metrics['fault_gated_psm_unsafe_or_risky']}",
        f"- Fault adapter failures: {metrics['fault_adapter_failures']}",
        f"- Fault injection events: {metrics['fault_injection_events']}",
        f"- Controller rescue count: {metrics['controller_rescue_count']}",
        f"- Controller risk reduction: {metrics['controller_risk_reduction']}",
        f"- Ledger group counts: {metrics['ledger_group_counts']}",
        f"- Adapter failure types: {metrics['adapter_failure_types']}",
        f"- Rule replacement allowed: {metrics['rule_replacement_allowed']}",
        f"- Rows: `{rows_path}`",
        f"- Candidate failure ledger: `{ledger_path}`",
        "",
        "## State Prediction Holdout",
        "",
        f"- Metrics path: `{metrics['state_holdout_metrics'].get('path')}`",
        f"- Available: {metrics['state_holdout_metrics'].get('available')}",
        f"- No-retrain clean: {metrics['state_holdout_metrics'].get('no_retrain_clean')}",
        f"- No-retrain ledger events: {metrics['state_holdout_metrics'].get('no_retrain_ledger_events')}",
        f"- No-retrain target match rates: {metrics['state_holdout_metrics'].get('no_retrain_target_match_rates')}",
        f"- No-retrain B_sigma exact match: {metrics['state_holdout_metrics'].get('no_retrain_bsigma_exact_match')}",
        "",
        "## Adapter Metrics",
        "",
    ]
    for item in metrics["adapter_metrics"]:
        lines.extend(
            [
                f"### {item['adapter_name']}",
                "",
                f"- Gate scope: {item['gate_scope']}",
                f"- Fault injection: {item['fault_injection']}",
                f"- Fault mode: {item['fault_mode']}",
                f"- Case limit: {item['case_limit']}",
                f"- Cases: {item['cases']}",
                f"- Adapter failures: {item['adapter_failures']}",
                f"- Adapter failure types: {item['adapter_failure_types']}",
                f"- Ordinary unsafe/risky: {item['ordinary_unsafe_or_risky']}",
                f"- Raw PSM unsafe/risky: {item['raw_psm_unsafe_or_risky']}",
                f"- Gated PSM unsafe/risky: {item['gated_psm_unsafe_or_risky']}",
                f"- Ordinary total net risk: {item['ordinary_total_net_risk']}",
                f"- Raw PSM total net risk: {item['raw_psm_total_net_risk']}",
                f"- Gated PSM total net risk: {item['gated_psm_total_net_risk']}",
                f"- Raw PSM risk reduction: {item['raw_psm_risk_reduction']}",
                f"- Gated PSM risk reduction: {item['gated_psm_risk_reduction']}",
                f"- Controller changed count: {item['controller_changed_count']}",
                f"- Controller rescue count: {item['controller_rescue_count']}",
                f"- Controller risk reduction: {item['controller_risk_reduction']}",
                f"- Ordinary avg latency ms: {item['ordinary_avg_latency_ms']}",
                f"- PSM avg latency ms: {item['psm_avg_latency_ms']}",
                f"- Candidate text clean: {item['candidate_text_clean']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- This report evaluates candidate text behavior on the blind holdout slice.",
            "- State prediction clean and candidate text clean are separate gates.",
            "- Fault injection is expected to create ledgered failures; it is not counted as release-gate failure.",
            "- Optional external model results are reported separately from deterministic required gates.",
            "- Controller-gated clean output does not authorize rule replacement in V0.x.",
        ]
    )
    return "\n".join(lines)


def annotate_candidate_ledger_events(events: list[dict], row: dict) -> list[dict]:
    for event in events:
        mode = event.get("candidate_mode")
        event["adapter_name"] = row["adapter_name"]
        event["gate_scope"] = row["gate_scope"]
        event["fault_injection"] = row["fault_injection"]
        event["fault_mode"] = row["fault_mode"]
        event["ledger_group"] = classify_ledger_group(event, row)
        if event["risk"] == "adapter_failure":
            event["adapter_error_type"] = row[f"{mode_to_row_prefix(mode)}_error_type"]
    return events


def build_controller_rescue_events(case: dict, result: dict, row: dict) -> list[dict]:
    if not row["controller_rescued"]:
        return []
    packet = result["packet"]
    return [
        {
            "case_id": case["id"],
            "packet_id": packet["packet_id"],
            "domain": packet["domain"],
            "risk_level": packet["omega"]["risk_level"],
            "event_type": "controller_rescue",
            "candidate_mode": "psm_gated",
            "adapter": row["psm_response"]["adapter"],
            "adapter_name": row["adapter_name"],
            "model": row["psm_response"]["model"],
            "status": row["psm_audit"]["status"],
            "severity": "medium",
            "reason": "PSM controller reduced raw candidate risk before release.",
            "risk": "controller_rescue",
            "ledger_group": "controller_rescue",
            "gate_scope": row["gate_scope"],
            "fault_injection": row["fault_injection"],
            "fault_mode": row["fault_mode"],
            "controller_risk_reduction": row["controller_risk_reduction"],
        }
    ]


def classify_ledger_group(event: dict, row: dict) -> str:
    if event.get("risk") == "adapter_failure":
        return "adapter_failure"
    mode = event.get("candidate_mode")
    if mode == "ordinary":
        return "ordinary_risk"
    if mode == "psm_raw":
        return "raw_psm_risk"
    if mode == "psm_gated":
        return "gated_psm_risk"
    return "other"


def mode_to_row_prefix(mode: str) -> str:
    if mode == "ordinary":
        return "ordinary"
    if mode in {"psm_raw", "psm_gated"}:
        return "psm"
    return "psm"


def classify_adapter_error(error: str | None) -> str | None:
    if not error:
        return None
    lowered = error.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if "malformed json" in lowered:
        return "malformed_json"
    if "empty stdout" in lowered or "non-empty" in lowered:
        return "empty_output"
    if "failed with exit" in lowered:
        return "nonzero_exit"
    return "other"


def count_adapter_failure_types(rows: list[dict]) -> dict:
    counts = Counter()
    for row in rows:
        for mode in ("ordinary", "psm"):
            error_type = row.get(f"{mode}_error_type")
            if error_type:
                counts[error_type] += 1
    return dict(sorted(counts.items()))


def count_ledger_groups(rows: list[dict]) -> Counter:
    groups = Counter()
    for row in rows:
        for mode, audit_key in (
            ("ordinary", "ordinary_audit"),
            ("psm_raw", "psm_raw_audit"),
            ("psm_gated", "psm_audit"),
        ):
            for item in row[audit_key]["items"]:
                if item["risk"] == "adapter_failure":
                    groups["adapter_failure"] += 1
                elif mode == "ordinary":
                    groups["ordinary_risk"] += 1
                elif mode == "psm_raw":
                    groups["raw_psm_risk"] += 1
                else:
                    groups["gated_psm_risk"] += 1
        if row["controller_rescued"]:
            groups["controller_rescue"] += 1
    return groups


if __name__ == "__main__":
    main()
