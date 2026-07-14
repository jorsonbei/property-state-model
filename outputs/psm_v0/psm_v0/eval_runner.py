from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .case_loader import load_cases
from .failure_ledger import append_ledger, build_ledger_events
from .gate_scorer import score_gates
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PSM case evals.")
    parser.add_argument("--cases-dir", type=Path, default=Path("cases"))
    parser.add_argument("--outdir", type=Path, default=Path("eval_out"))
    parser.add_argument("--ledger", type=Path, default=Path("eval_out/failure_ledger.jsonl"))
    parser.add_argument("--stem", default="psm_v0.20")
    parser.add_argument("--version-tag", default="V0.20")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.ledger.exists():
        args.ledger.unlink()

    rows = []
    for case in load_cases(args.cases_dir):
        result = run_pipeline(case["request"])
        eval_result = evaluate_case(case, result)
        gate_score = score_gates(result)
        events = build_ledger_events(result, case_id=case["id"])
        append_ledger(args.ledger, events)
        case_out = {
            "case": case,
            "result": {
                "packet": result["packet"],
                "q_audit": result["q_audit"],
                "route": result["route"],
                "bsigma_audit": result["bsigma_audit"],
            },
            "eval": eval_result,
            "gate_score": gate_score,
            "ledger_events": events,
        }
        (args.outdir / f"{case['id']}.result.json").write_text(
            json.dumps(case_out, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rows.append(case_out)

    report = build_eval_report(rows, args.ledger, args.version_tag)
    report_path = args.outdir / f"PSM_{args.version_tag}_Eval_Report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"cases: {len(rows)}")
    print(f"passed: {sum(1 for row in rows if row['eval']['passed'])}")
    print(f"failed: {sum(1 for row in rows if not row['eval']['passed'])}")
    print(f"ledger: {args.ledger}")
    print(f"report: {report_path}")


def evaluate_case(case: dict, result: dict) -> dict:
    expected = case["expected"]
    checks = []
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]

    checks.append(_check("domain", packet["domain"], expected.get("domain")))
    checks.append(_check("q_status", q_audit["status"], expected.get("q_status")))
    checks.append(_check("risk_level", packet["omega"]["risk_level"], expected.get("risk_level")))
    checks.append(_check("route", route["route"], expected.get("route")))
    checks.append(_check("bsigma_status", bsigma["status"], expected.get("bsigma_status")))

    for required in expected.get("required_bsigma_risks", []):
        actual_risks = {item["risk"] for item in packet.get("bsigma_risks", [])}
        checks.append(
            {
                "name": f"required_bsigma:{required}",
                "passed": required in actual_risks,
                "expected": required,
                "actual": sorted(actual_risks),
            }
        )

    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _check(name: str, actual: str, expected: str | None) -> dict:
    if expected is None:
        return {"name": name, "passed": True, "expected": None, "actual": actual}
    return {"name": name, "passed": actual == expected, "expected": expected, "actual": actual}


def build_eval_report(rows: list[dict], ledger_path: Path, version_tag: str) -> str:
    total = len(rows)
    passed = sum(1 for row in rows if row["eval"]["passed"])
    failed = total - passed
    domains = Counter(row["result"]["packet"]["domain"] for row in rows)
    q_statuses = Counter(row["result"]["q_audit"]["status"] for row in rows)
    bsigma_statuses = Counter(row["result"]["bsigma_audit"]["status"] for row in rows)
    avg_gate_score = sum(row["gate_score"]["score"] for row in rows) / total if total else 0

    lines = [
        f"# PSM {version_tag} State Audit Eval Report",
        "",
        "## Summary",
        "",
        f"- Cases: {total}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Average gate score: {avg_gate_score:.3f}",
        f"- Failure ledger: `{ledger_path}`",
        "",
        "## Distribution",
        "",
        f"- Domains: {dict(domains)}",
        f"- Q statuses: {dict(q_statuses)}",
        f"- B_sigma statuses: {dict(bsigma_statuses)}",
        "",
        "## Case Results",
        "",
    ]
    for row in rows:
        case = row["case"]
        status = "PASS" if row["eval"]["passed"] else "FAIL"
        packet = row["result"]["packet"]
        q_audit = row["result"]["q_audit"]
        route = row["result"]["route"]
        bsigma = row["result"]["bsigma_audit"]
        gate_score = row["gate_score"]
        lines.extend(
            [
                f"### {case['id']} - {status}",
                "",
                f"- Domain: {packet['domain']}",
                f"- Risk: {packet['omega']['risk_level']}",
                f"- Q status: {q_audit['status']}",
                f"- Route: {route['route']}",
                f"- B_sigma: {bsigma['status']}",
                f"- Gate score: {gate_score['passed']}/{gate_score['total']} ({gate_score['score']:.3f})",
                f"- Ledger events: {len(row['ledger_events'])}",
                "",
            ]
        )
        for check in row["eval"]["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            lines.append(f"- {mark} `{check['name']}` expected={check['expected']} actual={check['actual']}")
        lines.append("")
        lines.append("Gate coverage:")
        for gate, ok in gate_score["checks"].items():
            mark = "PASS" if ok else "FAIL"
            lines.append(f"- {mark} `{gate}`")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
