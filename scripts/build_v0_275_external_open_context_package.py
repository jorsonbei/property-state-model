#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from psm_v0.openai_external_open_context_judge import DIMENSIONS, PREPARED_AUTHORIZATION, canonical_sha256, validate_review_package


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
STATUS = PSM_ROOT / "project_status_out" / "psm_v0.274_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_274_open_context_generalization_contract.json"
REPORT = RUNTIME / "v0_274_open_context_generalization_report.json"
GATE = RUNTIME / "v0_274_open_context_generalization_gate.json"
MANIFEST = RUNTIME / "v0_274_open_context_generalization_promotion_manifest.json"
BUDGET = RUNTIME / "v0_267_api_budget_ledger.json"
PACKAGE = RUNTIME / "v0_275_external_open_context_review_package.json"
PACKAGE_GATE = RUNTIME / "v0_275_external_open_context_package_gate.json"
CHECKPOINT = RUNTIME / "v0_275_external_open_context_checkpoint.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    status, contract, report, gate, manifest, budget = map(read, (STATUS, CONTRACT, REPORT, GATE, MANIFEST, BUDGET))
    rows = {row["case_id"]: row for row in report["rows"]}
    items = [
        {
            "review_id": f"O{index:02d}",
            "family": case["family"],
            "conversation": case["messages"],
            "final_answer": rows[case["id"]]["answer"],
        }
        for index, case in enumerate(contract["cases"], start=1)
    ]
    payload = {
        "rubric_dimensions": list(DIMENSIONS),
        "items": items,
    }
    package = {
        "schema_version": "psm_v0_275_external_open_context_review_package_v1",
        "version": "PSM_V0.275-candidate",
        "authorization": PREPARED_AUTHORIZATION,
        "authorization_scope": "none_until_additional_user_budget_approval",
        "source_version": "PSM_V0.274",
        "source_contract": "benchmarks/v0_274_open_context_generalization_contract.json",
        "source_report": "runtime/v0_274_open_context_generalization_report.json",
        "source_gate": "runtime/v0_274_open_context_generalization_gate.json",
        "review_payload": payload,
        "review_payload_sha256": canonical_sha256(payload),
        "privacy": {
            "synthetic_only": True,
            "contains_private_data": False,
            "contains_user_documents": False,
            "contains_participant_content": False,
            "contains_secrets": False,
            "contains_local_paths": False,
            "contains_candidate_rules": False,
            "contains_hidden_labels": False,
            "training_eligible": False,
        },
        "budget": {
            "currency": "USD",
            "maximum_api_calls": 0,
            "reserved_usd": 0.0,
            "reserved_total_month_usd": 28.0,
            "monthly_limit_usd": 28.0,
            "additional_authorization_required_usd": 4.0,
        },
        "release_boundary": {
            "human_validation_claimed": False,
            "open_domain_generalization_claimed": False,
            "production_readiness_claimed": False,
            "public_service_allowed": False,
            "professional_authority_allowed": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
    }
    validate_review_package(package, require_authorization=False)
    serialized = json.dumps(package, ensure_ascii=False).casefold()
    prohibited = [token for token in ("sk-proj-", "/users/", "invitation_code", "api_key", "training_target", "expected_markers") if token in serialized]
    families = {item["family"] for item in items}
    checks = {
        "source_v0_274_promoted": status.get("current_version") == "psm_v0.274" and manifest.get("promoted") is True,
        "source_v0_274_gate_passed": gate.get("passed") is True and report.get("passed") is True,
        "exact_item_count": len(items) == 10,
        "exact_family_coverage": len(families) == 5 and all(sum(item["family"] == family for item in items) == 2 for family in families),
        "minimum_eleven_messages_per_item": all(len(item["conversation"]) >= 11 for item in items),
        "all_source_rows_passed": all(rows[case["id"]]["passed"] for case in contract["cases"]),
        "payload_hash_locked": canonical_sha256(package["review_payload"]) == package["review_payload_sha256"],
        "privacy_boundary_closed": package["privacy"]["synthetic_only"] is True and all(value is False for key, value in package["privacy"].items() if key != "synthetic_only"),
        "prohibited_material_absent": not prohibited,
        "external_api_call_disabled": package["budget"]["maximum_api_calls"] == 0,
        "monthly_budget_fully_reserved": float(budget.get("limit_usd", 0)) == float(budget.get("reserved_usd", 0)) == 28.0,
        "participant_content_calls_zero": budget.get("participant_content_calls") == 0,
        "release_boundary_closed": not any(package["release_boundary"].values()),
    }
    package_gate = {
        "schema_version": "psm_v0_275_external_open_context_package_gate_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "prohibited_material_found": prohibited,
        "review_payload_sha256": package["review_payload_sha256"],
        "authorization": PREPARED_AUTHORIZATION,
    }
    write(PACKAGE, package)
    write(PACKAGE_GATE, package_gate)
    if not package_gate["passed"]:
        raise SystemExit(f"V0.275 package gate failed: {[key for key, value in checks.items() if not value]}")
    checkpoint = {
        "schema_version": "psm_v0_275_external_open_context_checkpoint_v1",
        "current_promoted_version": "PSM_V0.274",
        "target_version": "PSM_V0.275",
        "target_promoted": False,
        "passed": False,
        "status": "blocked_external_open_context_judge_monthly_api_budget_exhausted",
        "requires_user_input": True,
        "next_action": "await_additional_v0_275_external_judge_budget_authorization",
        "review_payload_sha256": package["review_payload_sha256"],
        "reserved_month_usd": 28.0,
        "monthly_limit_usd": 28.0,
        "additional_authorization_required_usd": 4.0,
        "participant_content_calls": 0,
        "package_gate_passed": True,
        "required_decision": "批准额外 4 美元 OpenAI 合成开放式长对话独立评审预算，或停止 V0.275 外部评审。",
        "review_package": str(PACKAGE.relative_to(PSM_ROOT)),
        "package_gate": str(PACKAGE_GATE.relative_to(PSM_ROOT)),
    }
    write(CHECKPOINT, checkpoint)
    print(f"items: {len(items)}")
    print(f"families: {len(families)}")
    print(f"review_payload_sha256: {package['review_payload_sha256']}")
    print("external_calls_authorized: 0")
    print("reserved_month_usd: 28.00")
    print("additional_authorization_required_usd: 4.00")


if __name__ == "__main__":
    main()
