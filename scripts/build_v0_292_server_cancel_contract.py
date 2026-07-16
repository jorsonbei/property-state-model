#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_292_server_cancel_contract.json"
BASELINE = PSM_ROOT / "runtime" / "v0_292_server_cancel_baseline.json"
SOURCE = PSM_ROOT / "runtime" / "v0_291_cancel_retry_promotion_manifest.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = read(SOURCE)
    if source.get("version") != "PSM_V0.291" or source.get("promoted") is not True:
        raise SystemExit("V0.292 contract requires the promoted V0.291 source boundary.")

    contract = {
        "schema_version": "psm_v0_292_server_cancel_contract_v1",
        "version": "PSM_V0.292-candidate",
        "frozen_before_implementation": True,
        "objective": "Cancel active Ollama generation on the server while retaining full-answer Sigma+ review before display.",
        "request_protocol": {
            "request_id": {
                "required_for_cancellable_chat": True,
                "pattern": "^[A-Za-z0-9_-]{16,80}$",
                "contains_prompt_or_private_data": False,
            },
            "cancel_endpoint": "/api/chat-cancel",
            "cancel_body_fields": ["request_id"],
            "cancel_response_fields": ["request_id", "accepted", "active"],
            "cancelled_chat_status": 499,
            "cancelled_chat_error": "chat_cancelled",
        },
        "server_resource_contract": {
            "registry_storage": "bounded_in_memory_only",
            "registry_max_entries": 128,
            "registry_ttl_seconds": 300,
            "disk_persistence": False,
            "raw_prompt_retained_in_registry": False,
            "provider_transport": "ollama_ndjson_internal_stream",
            "provider_cancel_status": "cancelled",
            "cancelled_candidate_released": False,
        },
        "delivery_contract": {
            "raw_model_chunks_user_visible": False,
            "complete_candidate_required_before_audit": True,
            "sigma_plus_review_before_user_display": True,
            "browser_progressive_display_scope": "accepted_answer_buffer_only",
            "network_token_streaming_claimed": False,
        },
        "acceptance": {
            "provider_stream_chunks_join_exactly": True,
            "provider_cancel_discards_partial_answer": True,
            "server_cancel_acknowledged_for_active_request": True,
            "cancelled_chat_returns_499_without_fallback_answer": True,
            "cancel_to_server_stop_limit_ms": 2000,
            "retry_after_cancel_succeeds": True,
            "host_and_docker_required": True,
            "browser_desktop_and_mobile_required": True,
            "full_regression_required": True,
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
        "schema_version": "psm_v0_292_server_cancel_baseline_v1",
        "source_version": "PSM_V0.291",
        "captured_before_implementation": True,
        "observed": {
            "browser_abort_controller_present": True,
            "client_cancel_observed_ms": source["cancel_retry_interaction"]["observed_cancel_ms"],
            "request_id_sent_to_server": False,
            "server_cancel_endpoint_present": False,
            "server_cancel_registry_present": False,
            "ollama_stream_mode": False,
            "ollama_generation_cooperatively_cancelled": False,
            "network_token_streaming_present": False,
        },
        "baseline_decision": "client_wait_cancel_only_server_generation_continues",
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
