#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_286_natural_recovery_reference_contract.json"


def main() -> None:
    positives = (
        ("N01", "那个项目代号来着？"),
        ("N02", "项目代号是什么来着？"),
        ("N03", "代號叫什麼來著？"),
        ("N04", "我们定的文件名呢？"),
        ("N05", "我們定的檔名叫什麼？"),
        ("N06", "定稿文件叫什么？"),
        ("N07", "原定的会议是几点？"),
        ("N08", "原定的會議安排在哪天？"),
        ("N09", "未完成的那一项是什么？"),
        ("N10", "剩下哪件没做？"),
        ("N11", "What was the project codename?"),
        ("N12", "Remind me of the filename we settled on."),
    )
    negatives = (
        ("N13", "请给这个新项目起个代号。"),
        ("N14", "新文件应该叫什么？"),
        ("N15", "安排一个新的会议时间。"),
        ("N16", "列出今天的新待办。"),
    )
    cases = [
        {"case_id": case_id, "text": text, "should_trigger_recovery": True}
        for case_id, text in positives
    ] + [
        {"case_id": case_id, "text": text, "should_trigger_recovery": False}
        for case_id, text in negatives
    ]
    canonical = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    contract = {
        "schema_version": "psm_v0_286_natural_recovery_reference_contract_v1",
        "version": "PSM_V0.286-candidate",
        "source_version": "PSM_V0.285",
        "frozen": True,
        "synthetic_only": True,
        "case_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "positive_cases": len(positives),
        "negative_cases": len(negatives),
        "cases": cases,
        "requirements": {
            "positive_recall": 1.0,
            "negative_specificity": 1.0,
            "archived_fact_fabrication_allowed": 0,
            "external_release_authority": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"contract: {OUT.relative_to(ROOT)}")
    print(f"cases: {len(cases)}")


if __name__ == "__main__":
    main()
