#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUTPUT = PSM_ROOT / "runtime" / "v0_295_regression_report.json"


def main() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PSM_ROOT)
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    output = completed.stdout + completed.stderr
    match = re.search(r"Ran (\d+) tests? in", output)
    executed = int(match.group(1)) if match else 0
    report = {
        "schema_version": "psm_v0_295_regression_report_v1",
        "version": "PSM_V0.295-candidate",
        "tests_discovered": executed,
        "tests_passed": executed if completed.returncode == 0 else 0,
        "tests_failed": 0 if completed.returncode == 0 else None,
        "passed": completed.returncode == 0 and executed >= 262,
        "output_tail": output.splitlines()[-8:],
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(completed.returncode or 1)


if __name__ == "__main__":
    main()
