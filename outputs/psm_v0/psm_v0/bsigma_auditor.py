from __future__ import annotations


def audit_bsigma(packet: dict, candidate: str | None = None) -> dict:
    items: list[dict] = []
    for risk in packet.get("bsigma_risks", []):
        items.append(
            {
                "risk": risk["risk"],
                "severity": risk["severity"],
                "finding": risk["reason"],
                "action": _action_for(risk["risk"], risk["severity"]),
            }
        )

    if candidate:
        lowered = candidate.lower()
        if "一定" in candidate or "保证" in candidate or "guarantee" in lowered:
            items.append(
                {
                    "risk": "overclaim_in_candidate",
                    "severity": "high",
                    "finding": "候选输出包含强保证式语言。",
                    "action": "降级声明等级，补外部裁判或删除强保证。",
                }
            )
        if "引用" in candidate and "来源" not in candidate:
            items.append(
                {
                    "risk": "floating_citation",
                    "severity": "medium",
                    "finding": "候选输出提到引用但未绑定来源。",
                    "action": "补来源核验或删除引用。",
                }
            )

    max_severity = _max_severity([item["severity"] for item in items])
    if max_severity in {"high", "critical"}:
        status = "suspect"
    elif max_severity == "medium":
        status = "review"
    else:
        status = "clean"
    return {"status": status, "items": items}


def _action_for(risk: str, severity: str) -> str:
    if risk == "language_cover":
        return "禁止直接按语言表面生成，先输出状态审计。"
    if risk == "backfit":
        return "冻结假设，要求 NoBackfit 和外部裁判。"
    if risk == "untested_code":
        return "进入沙盒运行与测试。"
    if severity in {"high", "critical"}:
        return "降级或阻断，补外部证据。"
    return "补边界声明。"


def _max_severity(severities: list[str]) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if not severities:
        return "low"
    return max(severities, key=lambda item: order[item])
