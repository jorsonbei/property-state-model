from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .case_loader import load_cases
from .candidate_auditor import audit_candidate_text
from .failure_ledger import append_ledger
from .model_adapter import build_model_adapter, response_to_dict
from .pipeline import run_pipeline
from .psm_gate_controller import apply_psm_gate


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ordinary model output vs PSM-gated model output.")
    parser.add_argument("--cases-dir", type=Path, default=Path("cases"))
    parser.add_argument("--outdir", type=Path, default=Path("compare_out"))
    parser.add_argument("--ledger", type=Path, default=Path("compare_out/candidate_failure_ledger.jsonl"))
    parser.add_argument("--adapter", choices=["command", "builtin"], default="command")
    parser.add_argument("--model-command", default=None, help="External model command. Receives JSON on stdin.")
    parser.add_argument("--adapter-timeout", type=int, default=30)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.ledger.exists():
        args.ledger.unlink()

    adapter = build_model_adapter(args.adapter, args.model_command, args.adapter_timeout)
    adapter_descriptor = adapter.descriptor() if hasattr(adapter, "descriptor") else {"adapter": args.adapter}
    rows = []
    for case in load_cases(args.cases_dir):
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
        psm_audit = (
            audit_candidate_text(psm_candidate, result)
            if psm_generation["ok"]
            else adapter_failure_audit(psm_generation["error"])
        )
        psm_raw_audit = (
            audit_candidate_text(psm_raw_candidate, result)
            if psm_generation["ok"]
            else adapter_failure_audit(psm_generation["error"])
        )
        improvement = ordinary_audit["net_risk"] - psm_audit["net_risk"]
        controller_risk_reduction = psm_raw_audit["net_risk"] - psm_audit["net_risk"]
        row = {
            "case": case,
            "adapter_descriptor": adapter_descriptor,
            "ordinary_response": ordinary_generation["response"],
            "psm_response": psm_generation["response"],
            "ordinary_adapter_ok": ordinary_generation["ok"],
            "psm_adapter_ok": psm_generation["ok"],
            "ordinary_latency_ms": ordinary_generation["latency_ms"],
            "psm_latency_ms": psm_generation["latency_ms"],
            "ordinary_candidate": ordinary_candidate,
            "psm_raw_candidate": psm_raw_candidate,
            "psm_candidate": psm_candidate,
            "ordinary_audit": ordinary_audit,
            "psm_raw_audit": psm_raw_audit,
            "psm_audit": psm_audit,
            "risk_reduction": improvement,
            "controller_changed_output": psm_raw_candidate.strip() != psm_candidate.strip(),
            "controller_risk_reduction": controller_risk_reduction,
            "controller_rescued": controller_risk_reduction > 0,
        }
        (args.outdir / f"{case['id']}.compare.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        append_ledger(args.ledger, build_candidate_ledger_events(case, result, row))
        rows.append(row)

    report = build_comparison_report(rows, args.ledger)
    report_path = args.outdir / "PSM_V0.6_Comparison_Report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"cases: {len(rows)}")
    print(f"adapter: {args.adapter}")
    print(f"adapter_failures: {count_adapter_failures(rows)}")
    print(f"ordinary_avg_latency_ms: {average_latency(rows, 'ordinary'):.1f}")
    print(f"psm_avg_latency_ms: {average_latency(rows, 'psm'):.1f}")
    print(f"ordinary_unsafe_or_risky: {sum(1 for row in rows if row['ordinary_audit']['status'] in {'unsafe', 'risky'})}")
    print(f"raw_psm_unsafe_or_risky: {sum(1 for row in rows if row['psm_raw_audit']['status'] in {'unsafe', 'risky'})}")
    print(f"psm_unsafe_or_risky: {sum(1 for row in rows if row['psm_audit']['status'] in {'unsafe', 'risky'})}")
    print(f"controller_rescue_count: {sum(1 for row in rows if row['controller_rescued'])}")
    print(f"controller_risk_reduction_total: {sum(row['controller_risk_reduction'] for row in rows)}")
    print(f"risk_reduction_total: {sum(row['risk_reduction'] for row in rows)}")
    print(f"ledger: {args.ledger}")
    print(f"report: {report_path}")


def generate_with_metrics(adapter, *, mode: str, case: dict, result: dict) -> dict:
    started = time.perf_counter()
    try:
        response = adapter.generate(mode=mode, case=case, result=result)
    except Exception as exc:  # pragma: no cover - exercised by external tool failures.
        return {
            "ok": False,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "candidate": "",
            "response": {
                "text": "",
                "adapter": "adapter_failure",
                "model": "adapter_failure",
                "metadata": {"mode": mode},
            },
            "error": str(exc),
        }
    return {
        "ok": True,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "candidate": response.text,
        "response": response_to_dict(response),
        "error": None,
    }


def adapter_failure_audit(error: str) -> dict:
    return {
        "status": "adapter_failed",
        "risk_score": 0,
        "mitigation_score": 0,
        "net_risk": 0,
        "items": [
            {
                "risk": "adapter_failure",
                "severity": "critical",
                "finding": f"模型适配器调用失败：{error}",
            }
        ],
        "mitigations": [],
    }


def build_candidate_ledger_events(case: dict, result: dict, row: dict) -> list[dict]:
    packet = result["packet"]
    events = []
    audit_specs = (
        ("ordinary", row["ordinary_audit"], row["ordinary_response"]),
        ("psm_raw", row["psm_raw_audit"], row["psm_response"]),
        ("psm_gated", row["psm_audit"], row["psm_response"]),
    )
    for mode, audit, response in audit_specs:
        for item in audit["items"]:
            events.append(
                {
                    "case_id": case["id"],
                    "packet_id": packet["packet_id"],
                    "domain": packet["domain"],
                    "risk_level": packet["omega"]["risk_level"],
                    "event_type": "candidate_bsigma",
                    "candidate_mode": mode,
                    "adapter": response["adapter"],
                    "model": response["model"],
                    "status": audit["status"],
                    "severity": item["severity"],
                    "reason": item["finding"],
                    "risk": item["risk"],
                }
            )
    return events


def build_comparison_report(rows: list[dict], ledger_path: Path) -> str:
    ordinary_risk = sum(row["ordinary_audit"]["net_risk"] for row in rows)
    raw_psm_risk = sum(row["psm_raw_audit"]["net_risk"] for row in rows)
    psm_risk = sum(row["psm_audit"]["net_risk"] for row in rows)
    reduction = ordinary_risk - psm_risk
    raw_psm_reduction = ordinary_risk - raw_psm_risk
    controller_risk_reduction = sum(row["controller_risk_reduction"] for row in rows)
    controller_rescue_count = sum(1 for row in rows if row["controller_rescued"])
    controller_changed_count = sum(1 for row in rows if row["controller_changed_output"])
    total_generations = max(1, len(rows) * 2)
    adapter_failures = count_adapter_failures(rows)
    adapter_descriptors = {json.dumps(row["adapter_descriptor"], ensure_ascii=False) for row in rows}
    ordinary_models = sorted({row["ordinary_response"]["model"] for row in rows})
    psm_models = sorted({row["psm_response"]["model"] for row in rows})
    lines = [
        "# PSM V0.6 Candidate Comparison Report",
        "",
        "## Summary",
        "",
        f"- Cases: {len(rows)}",
        f"- Adapter descriptors: {sorted(adapter_descriptors)}",
        f"- Ordinary models: {ordinary_models}",
        f"- PSM models: {psm_models}",
        "- PSM gate controller: enabled",
        f"- Adapter failures: {adapter_failures}/{total_generations} ({adapter_failures / total_generations:.3f})",
        f"- Ordinary average latency ms: {average_latency(rows, 'ordinary'):.1f}",
        f"- PSM average latency ms: {average_latency(rows, 'psm'):.1f}",
        f"- Ordinary total net risk: {ordinary_risk}",
        f"- Raw PSM total net risk: {raw_psm_risk}",
        f"- Gated PSM total net risk: {psm_risk}",
        f"- Raw PSM risk reduction: {raw_psm_reduction}",
        f"- Gated PSM risk reduction: {reduction}",
        f"- Controller changed outputs: {controller_changed_count}",
        f"- Controller rescue count: {controller_rescue_count}",
        f"- Controller risk reduction: {controller_risk_reduction}",
        f"- Candidate failure ledger: `{ledger_path}`",
        "",
        "## Case Comparison",
        "",
    ]
    for row in rows:
        case = row["case"]
        ordinary = row["ordinary_audit"]
        raw_psm = row["psm_raw_audit"]
        psm = row["psm_audit"]
        lines.extend(
            [
                f"### {case['id']}",
                "",
                f"- Ordinary status: {ordinary['status']} net_risk={ordinary['net_risk']}",
                f"- Ordinary model: {row['ordinary_response']['model']}",
                f"- Ordinary adapter ok: {row['ordinary_adapter_ok']} latency_ms={row['ordinary_latency_ms']}",
                f"- Raw PSM status: {raw_psm['status']} net_risk={raw_psm['net_risk']}",
                f"- Gated PSM status: {psm['status']} net_risk={psm['net_risk']}",
                f"- PSM model: {row['psm_response']['model']}",
                f"- PSM adapter ok: {row['psm_adapter_ok']} latency_ms={row['psm_latency_ms']}",
                f"- Controller changed output: {row['controller_changed_output']}",
                f"- Controller rescued: {row['controller_rescued']} risk_reduction={row['controller_risk_reduction']}",
                f"- Gated risk reduction vs ordinary: {row['risk_reduction']}",
                "",
                "Ordinary risks:",
            ]
        )
        if ordinary["items"]:
            for item in ordinary["items"]:
                lines.append(f"- {item['risk']} [{item['severity']}]: {item['finding']}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Raw PSM risks:")
        if raw_psm["items"]:
            for item in raw_psm["items"]:
                lines.append(f"- {item['risk']} [{item['severity']}]: {item['finding']}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Gated PSM mitigations:")
        if psm["mitigations"]:
            for mitigation in psm["mitigations"]:
                lines.append(f"- {mitigation}")
        else:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines)


def count_adapter_failures(rows: list[dict]) -> int:
    return sum(
        1
        for row in rows
        for mode in ("ordinary", "psm")
        if not row[f"{mode}_adapter_ok"]
    )


def average_latency(rows: list[dict], mode: str) -> float:
    latencies = [row[f"{mode}_latency_ms"] for row in rows if row[f"{mode}_adapter_ok"]]
    return sum(latencies) / len(latencies) if latencies else 0.0


if __name__ == "__main__":
    main()
