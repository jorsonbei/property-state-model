from __future__ import annotations

import argparse
import json
from pathlib import Path

from .candidate_auditor import audit_candidate_text
from .eval_runner import evaluate_case
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a standalone PSM case pack without promoting it into cases/.")
    parser.add_argument("--case-pack", type=Path, required=True)
    parser.add_argument("--version-tag", default="V0.29")
    parser.add_argument("--outdir", type=Path, default=Path("case_packs"))
    args = parser.parse_args()

    cases = load_case_pack(args.case_pack)
    rows = []
    for case in cases:
        result = run_pipeline(case["request"])
        rows.append(
            {
                "case": case,
                "result": {
                    "packet": result["packet"],
                    "q_audit": result["q_audit"],
                    "route": result["route"],
                    "bsigma_audit": result["bsigma_audit"],
                },
                "eval": evaluate_case(case, result),
                "candidate_audit_eval": evaluate_candidate_audit(case, result),
            }
        )
    validation = build_validation(rows, args.case_pack)
    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{args.case_pack.stem}_validation.json"
    report_path = args.outdir / f"PSM_{args.version_tag}_{title_from_stem(args.case_pack.stem)}_Report.md"
    json_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(validation, json_path), encoding="utf-8")

    print(f"cases: {validation['summary']['cases']}")
    print(f"passed: {validation['summary']['passed']}")
    print(f"failed: {validation['summary']['failed']}")
    print(f"validation: {json_path}")
    print(f"report: {report_path}")
    if not validation["passed"]:
        raise SystemExit(1)


def load_case_pack(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(f"unsupported case pack payload: {type(payload).__name__}")


def build_validation(rows: list[dict], case_pack: Path) -> dict:
    failed = [
        row for row in rows
        if not row["eval"]["passed"]
        or (row["candidate_audit_eval"] is not None and not row["candidate_audit_eval"]["passed"])
    ]
    return {
        "case_pack": str(case_pack),
        "passed": not failed,
        "summary": {
            "cases": len(rows),
            "passed": len(rows) - len(failed),
            "failed": len(failed),
            "loaded_by_default_case_loader": False,
            "rule_replacement_allowed": False,
        },
        "rows": rows,
    }


def evaluate_candidate_audit(case: dict, result: dict) -> dict | None:
    spec = case.get("candidate_audit")
    if not spec:
        return None
    audit = audit_candidate_text(spec["text"], result)
    risks = [item["risk"] for item in audit["items"]]
    checks = []
    if "expected_status" in spec:
        checks.append(
            {
                "name": "candidate_audit_status",
                "expected": spec["expected_status"],
                "actual": audit["status"],
                "passed": audit["status"] == spec["expected_status"],
            }
        )
    if "expected_net_risk" in spec:
        checks.append(
            {
                "name": "candidate_audit_net_risk",
                "expected": spec["expected_net_risk"],
                "actual": audit["net_risk"],
                "passed": audit["net_risk"] == spec["expected_net_risk"],
            }
        )
    if "expected_risks" in spec:
        checks.append(
            {
                "name": "candidate_audit_risks_exact",
                "expected": spec["expected_risks"],
                "actual": risks,
                "passed": risks == spec["expected_risks"],
            }
        )
    if "required_risks" in spec:
        checks.append(
            {
                "name": "candidate_audit_required_risks",
                "expected": spec["required_risks"],
                "actual": risks,
                "passed": set(spec["required_risks"]).issubset(set(risks)),
            }
        )
    if "forbidden_risks" in spec:
        checks.append(
            {
                "name": "candidate_audit_forbidden_risks",
                "expected": spec["forbidden_risks"],
                "actual": risks,
                "passed": not set(spec["forbidden_risks"]).intersection(risks),
            }
        )
    return {
        "passed": all(check["passed"] for check in checks),
        "audit": audit,
        "checks": checks,
    }


def title_from_stem(stem: str) -> str:
    return "_".join(part.capitalize() for part in stem.split("_"))


def build_report(validation: dict, json_path: Path) -> str:
    summary = validation["summary"]
    lines = [
        "# PSM Standalone Case Pack Validation Report",
        "",
        "## Summary",
        "",
        f"- Case pack: `{validation['case_pack']}`",
        f"- Cases: {summary['cases']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Loaded by default case loader: {summary['loaded_by_default_case_loader']}",
        f"- Rule replacement allowed: {summary['rule_replacement_allowed']}",
        f"- JSON: `{json_path}`",
        "",
        "## Cases",
        "",
    ]
    for row in validation["rows"]:
        case = row["case"]
        status = "PASS" if row["eval"]["passed"] else "FAIL"
        packet = row["result"]["packet"]
        lines.extend(
            [
                f"### {case['id']} - {status}",
                "",
                f"- Domain: {packet['domain']}",
                f"- Risk: {packet['omega']['risk_level']}",
                f"- Q status: {row['result']['q_audit']['status']}",
                f"- Route: {row['result']['route']['route']}",
                f"- B_sigma: {row['result']['bsigma_audit']['status']}",
                "",
            ]
        )
        for check in row["eval"]["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            lines.append(f"- {mark} `{check['name']}` expected={check['expected']} actual={check['actual']}")
        candidate_eval = row.get("candidate_audit_eval")
        if candidate_eval is not None:
            audit = candidate_eval["audit"]
            audit_status = "PASS" if candidate_eval["passed"] else "FAIL"
            risks = [item["risk"] for item in audit["items"]]
            lines.extend(
                [
                    "",
                    f"- Candidate audit: {audit_status}",
                    f"- Candidate audit status: {audit['status']}",
                    f"- Candidate audit net risk: {audit['net_risk']}",
                    f"- Candidate audit risks: {risks}",
                ]
            )
            for check in candidate_eval["checks"]:
                mark = "PASS" if check["passed"] else "FAIL"
                lines.append(f"- {mark} `{check['name']}` expected={check['expected']} actual={check['actual']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
