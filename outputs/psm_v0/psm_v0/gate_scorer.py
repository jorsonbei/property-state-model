from __future__ import annotations


GATES = [
    "q_core",
    "omega",
    "phi_state",
    "delta_sigma",
    "pi_cavity",
    "bsigma",
    "external_judge",
    "sigma_output",
]


def score_gates(result: dict) -> dict:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    report = result["report"]

    checks = {
        "q_core": bool(packet.get("q_core", {}).get("primary")) and q_audit["status"] in {"pass", "review_required", "veto"},
        "omega": bool(packet.get("omega", {}).get("risk_level")) and bool(route.get("route")),
        "phi_state": bool(packet.get("phi_state", {}).get("facts")) and bool(packet.get("phi_state", {}).get("unknowns")),
        "delta_sigma": bool(packet.get("delta_sigma", {}).get("pressures")),
        "pi_cavity": all(packet.get("pi_cavity", {}).get(key) for key in ("actors", "artifacts", "dependencies")),
        "bsigma": bool(bsigma.get("items")) and bsigma["status"] in {"clean", "review", "suspect"},
        "external_judge": _external_judge_gate(packet, route),
        "sigma_output": "## Σ+ 输出" in report and "## 下一步协议" in report,
    }
    passed = sum(1 for ok in checks.values() if ok)
    total = len(GATES)
    return {
        "passed": passed,
        "total": total,
        "score": round(passed / total, 3),
        "checks": checks,
    }


def _external_judge_gate(packet: dict, route: dict) -> bool:
    risk = packet["omega"]["risk_level"]
    judges = route.get("required_judges", [])
    if risk == "low":
        return True
    return bool(judges)
