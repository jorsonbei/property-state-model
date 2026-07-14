from __future__ import annotations

from .bsigma_auditor import audit_bsigma
from .omega_router import route_packet
from .q_auditor import audit_q_core
from .sigma_reporter import build_sigma_report
from .state_extractor import build_state_packet


def run_pipeline(text: str) -> dict:
    packet = build_state_packet(text.strip())
    q_audit = audit_q_core(packet)
    route = route_packet(packet)
    bsigma = audit_bsigma(packet)
    report = build_sigma_report(packet, q_audit, route, bsigma)
    return {
        "packet": packet,
        "q_audit": q_audit,
        "route": route,
        "bsigma_audit": bsigma,
        "report": report,
    }
