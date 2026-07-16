#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from run_v0_277_openai_state_compression_judge import DEFAULT_KEYCHAIN_SERVICE, load_api_key
from psm_v0.openai_external_contract_judge import DEFAULT_MODEL
from psm_v0.openai_external_natural_recovery_judge import (
    build_markdown_report,
    review_natural_recovery_package,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
PACKAGE = PSM_ROOT / "runtime" / "v0_287_external_natural_recovery_review_package.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_287_openai_external_natural_recovery_judge.json"


def main() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    result = review_natural_recovery_package(
        package,
        api_key=load_api_key(DEFAULT_KEYCHAIN_SERVICE),
        model=DEFAULT_MODEL,
    )
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT.with_suffix(".md").write_text(build_markdown_report(result), encoding="utf-8")
    print(f"passed: {result['passed']}")
    print(f"verdict: {result['review']['verdict']}")
    print(f"model: {result['actual_model']}")
    print(f"usage: {result['usage'].get('total_tokens', 0)} tokens")
    print(f"result: {OUTPUT.relative_to(ROOT)}")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
