from __future__ import annotations

import json
from pathlib import Path


def load_cases(cases_dir: Path) -> list[dict]:
    cases: list[dict] = []
    for case_path in sorted(cases_dir.glob("*.json")):
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            cases.extend(_with_source(item, case_path) for item in payload)
        elif isinstance(payload, dict):
            cases.append(_with_source(payload, case_path))
        else:
            raise ValueError(f"unsupported case payload in {case_path}: {type(payload).__name__}")
    seen: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not case_id:
            raise ValueError(f"case without id in {case.get('_source_path')}")
        if case_id in seen:
            raise ValueError(f"duplicate case id: {case_id}")
        seen.add(case_id)
    return cases


def _with_source(case: dict, case_path: Path) -> dict:
    result = dict(case)
    result["_source_path"] = str(case_path)
    return result
