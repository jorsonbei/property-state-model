#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_283_restart_recovery_contract.json"


def main() -> None:
    cases = [
        {"case_id": "C01", "event": "active", "expected_state": "active"},
        {"case_id": "C02", "event": "reset", "expected_state": "reset"},
        {"case_id": "C03", "event": "reload", "expected_state": "reload"},
        {"case_id": "C04", "event": "expired", "expected_state": "expired"},
        {"case_id": "C05", "event": "restarted", "expected_state": "restarted"},
    ]
    canonical = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    contract = {
        "schema_version": "psm_v0_283_restart_recovery_contract_v1",
        "version": "PSM_V0.283-candidate",
        "source_version": "PSM_V0.282",
        "synthetic_only": True,
        "frozen": True,
        "case_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "cases": cases,
        "requirements": {
            "states_distinguishable": ["active", "reset", "reload", "expired", "restarted"],
            "memory_loss_states": ["reset", "reload", "expired", "restarted"],
            "archived_fact_fabrication_allowed": False,
            "recovery_action": "restate_context",
            "raw_conversation_disk_persistence": False,
            "cross_session_leaks_allowed": 0,
            "host_and_docker_required": True,
            "desktop_and_mobile_required": True,
            "external_release_authority": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"contract: {OUT.relative_to(ROOT)}")
    print(f"cases: {len(cases)}")


if __name__ == "__main__":
    main()
