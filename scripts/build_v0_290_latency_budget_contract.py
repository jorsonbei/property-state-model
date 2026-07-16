#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
STATUS = PSM_ROOT / "project_status_out" / "psm_v0.289_project_status.json"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_290_latency_budget_contract.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_290_latency_budget_checkpoint.json"


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    measurement = {
        "runtimes": [
            {"runtime_id": "host", "base_url": "http://127.0.0.1:8765"},
            {"runtime_id": "docker", "base_url": "http://127.0.0.1:8766"},
        ],
        "categories": [
            {"category": "deterministic_recovery", "samples_per_runtime": 5, "p95_limit_ms": 1000},
            {"category": "deterministic_identity", "samples_per_runtime": 5, "p95_limit_ms": 1000},
            {"category": "local_model_generation", "samples_per_runtime": 3, "p95_limit_ms": 60000},
        ],
        "required_success_rate": 1.0,
        "fallbacks_allowed": 0,
    }
    contract = {
        "schema_version": "psm_v0_290_latency_budget_contract_v1",
        "version": "PSM_V0.290-candidate",
        "source_version": "PSM_V0.289",
        "frozen": True,
        "synthetic_only": True,
        "measurement": measurement,
        "measurement_sha256": canonical_sha256(measurement),
        "release_boundary": {
            "human_validation_claimed": False,
            "persistent_conversation_memory_enabled": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
    }
    checks = {
        "source_version_is_v0_289": status.get("current_version") == "psm_v0.289",
        "contract_is_frozen": contract["frozen"] is True,
        "synthetic_only": contract["synthetic_only"] is True,
        "release_boundary_closed": not any(contract["release_boundary"].values()),
    }
    checkpoint = {
        "schema_version": "psm_v0_290_latency_budget_checkpoint_v1",
        "status": "latency_contract_frozen" if all(checks.values()) else "blocked",
        "checks": checks,
        "requires_user_input": False,
        "next_action": "evaluate_v0_290_latency_budget",
    }
    write(CONTRACT, contract)
    write(CHECKPOINT, checkpoint)
    print(f"contract: {CONTRACT.relative_to(ROOT)}")
    print(f"measurement_sha256: {contract['measurement_sha256']}")
    print(f"passed: {all(checks.values())}")
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
