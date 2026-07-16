#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUTPUT = PSM_ROOT / "runtime" / "v0_292_regression_report.json"
EVALUATOR_GAP = PSM_ROOT / "runtime" / "v0_292_regression_attempt_1_evaluator_gap.json"


def main() -> None:
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if previous.get("passed") is False and not EVALUATOR_GAP.exists():
            shutil.copyfile(OUTPUT, EVALUATOR_GAP)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PSM_ROOT)
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    combined_output = completed.stdout + completed.stderr
    count_match = re.search(r"Ran (\d+) tests? in", combined_output)
    executed = int(count_match.group(1)) if count_match else 0
    report = {
        "schema_version": "psm_v0_292_regression_report_v1",
        "version": "PSM_V0.292-candidate",
        "command": "PYTHONPATH=outputs/psm_v0 python3 -m unittest discover -s tests -v",
        "tests_discovered": executed,
        "tests_passed": executed if completed.returncode == 0 else 0,
        "tests_failed": 0 if completed.returncode == 0 else None,
        "passed": completed.returncode == 0 and executed >= 249,
        "output_tail": combined_output.splitlines()[-8:],
        "retained_evaluator_gap": str(EVALUATOR_GAP.relative_to(PSM_ROOT)) if EVALUATOR_GAP.exists() else None,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(completed.returncode or 1)


if __name__ == "__main__":
    main()
