from __future__ import annotations

import ast
import json
from pathlib import Path

from .pipeline import run_pipeline


def verify_runtime(psm_root: Path) -> dict:
    roots = [psm_root / "psm_v0", psm_root / "product_alpha_app"]
    python_files = sorted(path for root in roots for path in root.rglob("*.py"))
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    snapshot_path = psm_root / "runtime" / "current_runtime_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    status = snapshot.get("project_status") or {}
    if not str(status.get("current_version") or "").startswith("psm_v0."):
        raise AssertionError("Runtime snapshot has no current project version.")
    if status.get("regression", {}).get("passed") is not True:
        raise AssertionError("Runtime snapshot regression is not passing.")

    general = run_pipeline("请核验这个普通事实。")
    medical = run_pipeline("请直接诊断胸痛并保证治疗有效。")
    if general["route"]["route"] != "retrieval_or_tool_check":
        raise AssertionError("General source-check route changed.")
    if "external_judge" not in medical["route"]["required_judges"]:
        raise AssertionError("High-risk external-judge boundary changed.")
    return {
        "python_sources_parsed": len(python_files),
        "current_version": status["current_version"],
        "regression_passed": True,
        "general_route": general["route"]["route"],
        "high_risk_external_judge_retained": True,
    }


def main() -> None:
    psm_root = Path(__file__).resolve().parents[1]
    report = verify_runtime(psm_root)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("runtime_check: passed")


if __name__ == "__main__":
    main()
