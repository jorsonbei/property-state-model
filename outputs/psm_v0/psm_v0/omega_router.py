from __future__ import annotations


ROUTES = {
    "low": {
        "route": "direct_language",
        "allowed_statement_level": "C1",
        "required_judges": [],
    },
    "medium": {
        "route": "retrieval_or_tool_check",
        "allowed_statement_level": "C2",
        "required_judges": ["source_or_tool_check"],
    },
    "high": {
        "route": "audited_generation",
        "allowed_statement_level": "C3",
        "required_judges": ["domain_specific_check", "bsigma_audit", "boundary_statement"],
    },
    "critical": {
        "route": "external_judge_and_human_confirmation",
        "allowed_statement_level": "C4",
        "required_judges": ["external_judge", "human_confirmation", "failure_ledger"],
    },
}


def route_packet(packet: dict) -> dict:
    risk_level = packet["omega"]["risk_level"]
    base = dict(ROUTES[risk_level])
    judges = list(dict.fromkeys(base["required_judges"] + packet.get("external_judges", [])))
    base["required_judges"] = judges
    base["reason"] = f"domain={packet['domain']}, risk_level={risk_level}"
    return base
