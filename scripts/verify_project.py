from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


def parse_python_sources() -> int:
    roots = [PSM_ROOT / "psm_v0", PSM_ROOT / "product_alpha_app", PSM_ROOT / "tools", PSM_ROOT / "work", ROOT / "scripts", ROOT / "tests"]
    files = sorted(path for source_root in roots for path in source_root.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return len(files)


def latest_status() -> dict:
    paths = list((PSM_ROOT / "project_status_out").glob("psm_v0.*_project_status.json"))
    if not paths:
        raise AssertionError("No project status files found.")
    path = max(paths, key=lambda item: int(item.name.split(".")[1].split("_")[0]))
    return json.loads(path.read_text(encoding="utf-8"))


def verify_recovery_docs(status: dict) -> None:
    text = (PSM_ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    expected = status["current_version"].replace("psm_v", "PSM V")
    if expected not in text:
        raise AssertionError(f"CURRENT_STATUS.md does not contain {expected}.")
    if "## Prior Status History" in text:
        raise AssertionError("CURRENT_STATUS.md still contains recursively embedded history.")


def verify_existing_regression(status: dict) -> None:
    regression = status.get("regression", {})
    if regression.get("passed") is not True:
        raise AssertionError("Latest project regression is not passing.")
    failed = [name for name, passed in regression.get("checks", {}).items() if passed is not True]
    if failed:
        raise AssertionError(f"Latest regression has failed checks: {failed}")


def run_tests() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PSM_ROOT)
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> None:
    source_count = parse_python_sources()
    status = latest_status()
    verify_recovery_docs(status)
    verify_existing_regression(status)
    json.loads((PSM_ROOT / "roadmap_out" / "psm_v0.248_to_v0.260_execution_plan.json").read_text(encoding="utf-8"))
    run_tests()
    print(f"python_sources_parsed: {source_count}")
    print(f"current_version: {status['current_version']}")
    print("latest_regression: passed")
    print("project_check: passed")


if __name__ == "__main__":
    main()
