from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_ledger_events(result: dict, case_id: str | None = None) -> list[dict]:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    events: list[dict] = []

    if q_audit["status"] in {"veto", "review_required"}:
        events.append(
            {
                "event_type": "q_core_gate",
                "severity": "high" if q_audit["status"] == "veto" else "medium",
                "status": q_audit["status"],
                "reason": "; ".join(q_audit["findings"]),
            }
        )

    if bsigma["status"] in {"suspect", "review"}:
        events.append(
            {
                "event_type": "bsigma_risk",
                "severity": _max_item_severity(bsigma["items"]),
                "status": bsigma["status"],
                "reason": "; ".join(item["finding"] for item in bsigma["items"]),
            }
        )

    if route["required_judges"]:
        events.append(
            {
                "event_type": "external_judge_required",
                "severity": "medium" if packet["omega"]["risk_level"] != "critical" else "critical",
                "status": "pending",
                "reason": ", ".join(route["required_judges"]),
            }
        )

    now = datetime.now(timezone.utc).isoformat()
    for event in events:
        event.update(
            {
                "ts": now,
                "case_id": case_id,
                "packet_id": packet["packet_id"],
                "domain": packet["domain"],
                "risk_level": packet["omega"]["risk_level"],
                "statement_level": packet["statement_level"],
            }
        )
    return events


def append_ledger(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _max_item_severity(items: list[dict]) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if not items:
        return "low"
    return max((item["severity"] for item in items), key=lambda item: order[item])
