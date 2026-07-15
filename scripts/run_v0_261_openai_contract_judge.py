from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from psm_v0.openai_external_contract_judge import (
    DEFAULT_MODEL,
    build_markdown_report,
    review_contract,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
DEFAULT_PACKAGE = PSM_ROOT / "runtime" / "v0_261_external_contract_review_package.json"
DEFAULT_OUTPUT = PSM_ROOT / "runtime" / "v0_261_openai_external_contract_judge.json"
DEFAULT_KEYCHAIN_SERVICE = "com.property-state-model.openai-api-key"


def load_api_key(service: str) -> str:
    from_environment = os.environ.get("OPENAI_API_KEY", "").strip()
    if from_environment:
        return from_environment
    completed = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        check=False,
        capture_output=True,
        text=True,
    )
    key = completed.stdout.strip()
    if completed.returncode != 0 or not key:
        raise SystemExit("OpenAI API key was not found in OPENAI_API_KEY or macOS Keychain.")
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the authorized PSM V0.261 OpenAI contract judge.")
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--keychain-service", default=DEFAULT_KEYCHAIN_SERVICE)
    args = parser.parse_args()

    package = json.loads(args.package.read_text(encoding="utf-8"))
    result = review_contract(package, api_key=load_api_key(args.keychain_service), model=args.model)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = args.out.with_suffix(".md")
    report_path.write_text(build_markdown_report(result), encoding="utf-8")
    print(f"passed: {result['passed']}")
    print(f"verdict: {result['review']['verdict']}")
    print(f"model: {result['actual_model']}")
    print(f"usage: {result['usage'].get('total_tokens', 0)} tokens")
    print(f"result: {args.out.relative_to(ROOT)}")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
