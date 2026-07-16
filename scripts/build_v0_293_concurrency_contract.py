#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_293_concurrency_backpressure_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_293_concurrency_backpressure_baseline.json"
SOURCE = PSM_ROOT / "runtime" / "v0_292_server_cancel_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    if source.get("version") != "PSM_V0.292" or source.get("promoted") is not True:
        raise SystemExit("V0.293 contract requires the promoted V0.292 source boundary.")
    contract = {
        "schema_version": "psm_v0_293_concurrency_backpressure_contract_v1",
        "version": "PSM_V0.293-candidate",
        "frozen_before_implementation": True,
        "admission": {
            "max_active_chat_requests": 4,
            "queue_enabled": False,
            "capacity_status": 503,
            "capacity_error": "chat_capacity_reached",
            "capacity_retry_after_seconds": 1,
            "capacity_response_limit_ms": 500,
            "active_request_eviction_allowed": False,
            "missing_client_request_id": "server_generated_bounded_id",
        },
        "identity": {
            "duplicate_active_request_status": 409,
            "duplicate_active_request_error": "duplicate_request_id",
            "invalid_request_status": 400,
            "invalid_request_error": "invalid_request_id",
            "request_id_contains_prompt_or_private_data": False,
        },
        "cancel_storm": {
            "all_four_active_requests_cancellable": True,
            "cancel_endpoint_idempotent_for_unknown_or_completed_id": True,
            "cancelled_chat_status": 499,
            "partial_answer_released": False,
            "cancel_to_worker_stop_limit_ms": 2000,
            "registry_empty_after_cleanup": True,
        },
        "runtime": {
            "host_required": True,
            "docker_required": True,
            "waves_per_runtime": 2,
            "active_requests_per_wave": 4,
            "capacity_probes_per_wave": 1,
            "duplicate_probes_per_wave": 1,
        },
        "release_boundary": {
            "synthetic_only": True,
            "human_validation_claimed": False,
            "persistent_conversation_memory_enabled": False,
            "model_compute_stop_directly_instrumented": False,
            "network_token_streaming_claimed": False,
            "public_service_allowed": False,
            "external_release_authority": False,
        },
    }
    baseline = {
        "schema_version": "psm_v0_293_concurrency_backpressure_baseline_v1",
        "source_version": "PSM_V0.292",
        "captured_before_implementation": True,
        "observed": {
            "server_owned_cancel_available": True,
            "registry_hard_max_entries": 128,
            "operational_active_chat_limit": None,
            "capacity_error_code_frozen": False,
            "duplicate_error_code_frozen": False,
            "missing_request_id_participates_in_admission": False,
            "concurrent_cancel_storm_runtime_evidence": False,
        },
        "baseline_decision": "single_request_cancel_passed_concurrent_admission_unbounded",
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
