from __future__ import annotations


ALLOWED_DECISIONS = ("internal_trial_ready", "needs_more_work", "blocked")


def choose_readiness_decision(*, required_artifacts_available: bool, required_checks: dict[str, bool]) -> str:
    if not required_artifacts_available:
        return "blocked"
    if not required_checks or not all(required_checks.values()):
        return "needs_more_work"
    return "internal_trial_ready"


def internal_scope_boundary() -> dict:
    return {
        "scope": "local_single_user_internal",
        "external_user_trial_allowed": False,
        "privacy_compliance_claimed": False,
        "public_service_allowed": False,
        "medical_legal_trading_authority": False,
        "shadow_output_authority": False,
        "rule_replacement_allowed": False,
        "external_release_authority": False,
    }


def validate_contract(contract: dict) -> None:
    if contract.get("frozen") is not True:
        raise ValueError("Readiness contract must be frozen.")
    if tuple(contract.get("allowed_decisions") or ()) != ALLOWED_DECISIONS:
        raise ValueError("Readiness contract decision enum changed.")
    if contract.get("required_boundaries") != internal_scope_boundary():
        raise ValueError("Readiness scope or release boundary changed.")
