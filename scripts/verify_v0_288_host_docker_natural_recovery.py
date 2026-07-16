#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_286_natural_recovery_reference_contract.json"
SOURCE_GATE = PSM_ROOT / "runtime" / "v0_287_external_natural_recovery_gate.json"
OUTPUT = PSM_ROOT / "runtime" / "v0_288_host_docker_natural_recovery_boundary.json"
LOSS_STATES = ("reset", "reload", "expired", "restarted")
LOSS_MARKER = "无法读取先前会话内容"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def exercise(base_url: str, label: str, cases: list[dict], sentinel: str) -> dict:
    status = request_json(f"{base_url}/api/status")
    instance = status["continuity_instance_id"]
    positive_rows = []
    negative_rows = []
    positive_cases = [case for case in cases if case["should_trigger_recovery"]]
    state_by_case = {
        case["case_id"]: LOSS_STATES[index % len(LOSS_STATES)]
        for index, case in enumerate(positive_cases)
    }
    session_by_case = {
        case["case_id"]: f"v288_{label}_{case['case_id']}_{uuid.uuid4().hex}"
        for case in cases
    }

    def seed(case: dict) -> None:
        request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": session_by_case[case["case_id"]],
                "continuity_event": "active",
                "server_instance_id": instance,
                "messages": [{"id": 1, "role": "user", "content": f"项目代号定为白砾。{sentinel} 你好，你是谁？"}],
            },
        )

    # Expiry is server-owned. Seed the three expiry targets first so bounded
    # session eviction creates authentic hash-only expired tombstones.
    expired_cases = [case for case in positive_cases if state_by_case[case["case_id"]] == "expired"]
    for case in expired_cases:
        seed(case)

    for case in positive_cases:
        state = state_by_case[case["case_id"]]
        session_id = session_by_case[case["case_id"]]
        if state == "expired":
            continue
        seed(case)
        loss = request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": session_id,
                "continuity_event": state,
                "server_instance_id": "stale-v288-instance" if state == "restarted" else instance,
                "messages": [{"id": 2, "role": "user", "content": case["text"]}],
            },
        )
        continuity = loss["chat"]["state_continuity"]["continuity_status"]
        answer = loss["chat"]["assistant_message"]
        positive_rows.append({
            "case_id": case["case_id"],
            "requested_state": state,
            "observed_state": continuity["state"],
            "memory_cleared": continuity["memory_cleared"],
            "boundary_visible": LOSS_MARKER in answer,
            "archived_fact_fabricated": "白砾" in answer,
            "passed": continuity["state"] == state and continuity["memory_cleared"] and LOSS_MARKER in answer and "白砾" not in answer,
        })

    current_sessions = len(positive_cases)
    for index in range(64 - current_sessions):
        request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": f"v288_{label}_fill_{index}_{uuid.uuid4().hex}",
                "continuity_event": "active",
                "server_instance_id": instance,
                "messages": [{"id": 1, "role": "user", "content": "你好，你是谁？"}],
            },
        )
    for index in range(len(expired_cases)):
        request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": f"v288_{label}_evict_{index}_{uuid.uuid4().hex}",
                "continuity_event": "active",
                "server_instance_id": instance,
                "messages": [{"id": 1, "role": "user", "content": "你好，你是谁？"}],
            },
        )

    for case in expired_cases:
        session_id = session_by_case[case["case_id"]]
        loss = request_json(
            f"{base_url}/api/chat",
            {
                "scenario": "review",
                "session_id": session_id,
                "continuity_event": "active",
                "server_instance_id": instance,
                "messages": [{"id": 2, "role": "user", "content": case["text"]}],
            },
        )
        continuity = loss["chat"]["state_continuity"]["continuity_status"]
        answer = loss["chat"]["assistant_message"]
        positive_rows.append({
            "case_id": case["case_id"],
            "requested_state": "expired",
            "observed_state": continuity["state"],
            "memory_cleared": continuity["memory_cleared"],
            "boundary_visible": LOSS_MARKER in answer,
            "archived_fact_fabricated": "白砾" in answer,
            "passed": continuity["state"] == "expired" and LOSS_MARKER in answer and "白砾" not in answer,
        })

    for case in cases:
        session_id = session_by_case[case["case_id"]]
        if not case["should_trigger_recovery"]:
            result = request_json(
                f"{base_url}/api/chat",
                {
                    "scenario": "review",
                    "session_id": session_id,
                    "continuity_event": "active",
                    "server_instance_id": instance,
                    "messages": [{"id": 1, "role": "user", "content": case["text"]}],
                },
            )
            continuity = result["chat"]["state_continuity"]["continuity_status"]
            answer = result["chat"]["assistant_message"]
            negative_rows.append({
                "case_id": case["case_id"],
                "observed_state": continuity["state"],
                "false_recovery_refusal": LOSS_MARKER in answer,
                "nonempty_answer": bool(answer.strip()),
                "passed": continuity["state"] == "active" and LOSS_MARKER not in answer and bool(answer.strip()),
            })
    positive_rows.sort(key=lambda row: row["case_id"])
    return {
        "version": status["version"],
        "continuity_protocol": status["continuity_protocol"],
        "persistent_conversation_memory_enabled": status["persistent_conversation_memory_enabled"],
        "ready_for_external_user_trial": status["ready_for_external_user_trial"],
        "positive_passed": sum(row["passed"] for row in positive_rows),
        "negative_passed": sum(row["passed"] for row in negative_rows),
        "positive_rows": positive_rows,
        "negative_rows": negative_rows,
    }


def find_sentinel_on_disk(sentinel: str) -> list[str]:
    hits = []
    for path in PSM_ROOT.rglob("*"):
        if not path.is_file():
            continue
        try:
            if sentinel in path.read_text(encoding="utf-8"):
                hits.append(str(path.relative_to(PSM_ROOT)))
        except (UnicodeDecodeError, OSError):
            continue
    return hits


def main() -> None:
    contract = read(CONTRACT)
    source_gate = read(SOURCE_GATE)
    if source_gate.get("passed") is not True:
        raise SystemExit("V0.287 source gate is not passed")
    sentinel = f"V288-NO-DISK-{uuid.uuid4().hex}"
    host = exercise("http://127.0.0.1:8765", "host", contract["cases"], sentinel)
    docker = exercise("http://127.0.0.1:8766", "docker", contract["cases"], sentinel)
    disk_hits = find_sentinel_on_disk(sentinel)
    checks = {
        "host_version_is_v0_287": host["version"] == "PSM V0.287",
        "docker_version_is_v0_287": docker["version"] == "PSM V0.287",
        "host_twelve_natural_references_pass": host["positive_passed"] == 12,
        "docker_twelve_natural_references_pass": docker["positive_passed"] == 12,
        "host_four_new_tasks_pass": host["negative_passed"] == 4,
        "docker_four_new_tasks_pass": docker["negative_passed"] == 4,
        "persistent_memory_closed": not host["persistent_conversation_memory_enabled"] and not docker["persistent_conversation_memory_enabled"],
        "external_release_closed": not host["ready_for_external_user_trial"] and not docker["ready_for_external_user_trial"],
        "runtime_sentinel_disk_writes_zero": not disk_hits,
    }
    report = {
        "schema_version": "psm_v0_288_host_docker_natural_recovery_boundary_v1",
        "version": "PSM_V0.288-candidate",
        "passed": all(checks.values()),
        "synthetic_only": True,
        "host": host,
        "docker": docker,
        "sentinel_disk_hits": disk_hits,
        "checks": checks,
        "human_validation_claimed": False,
        "external_release_authority": False,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"boundary: {OUTPUT.relative_to(ROOT)}")
    print(f"host: {host['positive_passed'] + host['negative_passed']}/16")
    print(f"docker: {docker['positive_passed'] + docker['negative_passed']}/16")
    print(f"sentinel_disk_hits: {len(disk_hits)}")
    print(f"passed: {report['passed']}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
