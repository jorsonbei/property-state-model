#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_294_content_free_telemetry_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_294_content_free_telemetry_baseline.json"
SOURCE = PSM_ROOT / "runtime" / "v0_293_concurrency_backpressure_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    if source.get("version") != "PSM_V0.293" or source.get("promoted") is not True:
        raise SystemExit("V0.294 contract requires the promoted V0.293 source boundary.")
    contract = {
        "schema_version": "psm_v0_294_content_free_telemetry_contract_v1",
        "version": "PSM_V0.294-candidate",
        "frozen_before_implementation": True,
        "endpoint": {
            "path": "/api/health",
            "method": "GET",
            "cache": "no-store",
            "states": ["healthy", "busy", "saturated"],
        },
        "counters": [
            "accepted",
            "capacity_rejected",
            "duplicate_rejected",
            "invalid_rejected",
            "cancel_requests",
            "cancel_active",
            "cancel_inactive",
            "cancelled",
            "completed",
            "failed",
        ],
        "latency": {
            "bucket_upper_bounds_ms": [100, 500, 2000, 10000, 30000, 70000],
            "series": ["completed", "cancelled", "failed"],
            "raw_samples_retained": False,
        },
        "privacy": {
            "process_memory_only": True,
            "disk_persistence": False,
            "reset_on_server_restart": True,
            "forbidden_fields": [
                "prompt",
                "answer",
                "messages",
                "session_id",
                "request_id",
                "participant_id",
                "invitation_code",
                "model_output",
            ],
            "identifiers_hashed": False,
            "identifiers_retained": False,
        },
        "runtime_acceptance": {
            "host_required": True,
            "docker_required": True,
            "event_delta_exact": True,
            "active_returns_to_zero": True,
            "latency_bucket_totals_match_outcomes": True,
            "disk_sentinel_hits": 0,
        },
        "release_boundary": {
            "synthetic_only": True,
            "human_validation_claimed": False,
            "persistent_conversation_memory_enabled": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
    }
    baseline = {
        "schema_version": "psm_v0_294_content_free_telemetry_baseline_v1",
        "source_version": "PSM_V0.293",
        "captured_before_implementation": True,
        "observed": {
            "health_endpoint_present": False,
            "lifecycle_counters_present": False,
            "latency_buckets_present": False,
            "content_free_telemetry_contract_present": False,
            "active_count_internal_only": True,
        },
        "baseline_decision": "backpressure_passed_operational_observability_absent",
        "target_contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "external_release_authority": False,
    }
    write(CONTRACT, contract)
    write(BASELINE, baseline)
    print(f"contract: {CONTRACT.relative_to(ROOT)}")
    print(f"baseline: {BASELINE.relative_to(ROOT)}")
    print("frozen: true")


if __name__ == "__main__":
    main()
