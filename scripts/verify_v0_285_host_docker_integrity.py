#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
GATE = PSM_ROOT / "runtime" / "v0_285_lifecycle_signal_integrity_gate.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_285_host_docker_integrity_boundary.json"


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def exercise(base_url: str, label: str) -> dict:
    status = request_json(f"{base_url}/api/status")
    instance = status["continuity_instance_id"]
    event_results = {}
    for event in ("reset", "reload", "restarted"):
        session_id = f"v285_{label}_{event}_session"
        request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": session_id,
                "continuity_event": "active",
                "server_instance_id": instance,
                "messages": [{"id": 1, "role": "user", "content": "项目代号定为白砾。你好，你是谁？"}],
            },
        )
        loss = request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": session_id,
                "continuity_event": "active" if event == "restarted" else event,
                "server_instance_id": "stale-server-instance" if event == "restarted" else instance,
                "messages": [{"id": 2, "role": "user", "content": "之前的项目代号是什么？"}],
            },
        )
        followup = request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": session_id,
                "continuity_event": "active",
                "server_instance_id": instance,
                "messages": [{"id": 3, "role": "user", "content": "之前的项目代号是什么？"}],
            },
        )
        loss_status = loss["chat"]["state_continuity"]["continuity_status"]
        followup_answer = followup["chat"]["assistant_message"]
        event_results[event] = {
            "observed_state": loss_status["state"],
            "memory_cleared": loss_status["memory_cleared"],
            "old_fact_resurrected": "白砾" in followup_answer,
        }
    return {
        "version": status["version"],
        "persistent_conversation_memory_enabled": status["persistent_conversation_memory_enabled"],
        "events": event_results,
    }


def main() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    if gate.get("passed") is not True:
        raise SystemExit("V0.285 local gate is not passed")
    host = exercise("http://127.0.0.1:8765", "host")
    docker = exercise("http://127.0.0.1:8766", "docker")
    checks = {
        "host_all_events_clear_memory": all(item["memory_cleared"] for item in host["events"].values()),
        "docker_all_events_clear_memory": all(item["memory_cleared"] for item in docker["events"].values()),
        "host_zero_resurrection": all(not item["old_fact_resurrected"] for item in host["events"].values()),
        "docker_zero_resurrection": all(not item["old_fact_resurrected"] for item in docker["events"].values()),
        "persistent_memory_closed": not host["persistent_conversation_memory_enabled"] and not docker["persistent_conversation_memory_enabled"],
    }
    report = {
        "schema_version": "psm_v0_285_host_docker_integrity_boundary_v1",
        "version": "PSM_V0.285-candidate",
        "passed": all(checks.values()),
        "synthetic_only": True,
        "host": host,
        "docker": docker,
        "checks": checks,
        "external_release_authority": False,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"boundary: {OUTPUT.relative_to(ROOT)}")
    print(f"passed: {report['passed']}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
