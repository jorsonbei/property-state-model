from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_254_docker_verification.json"
BASE_URL = "http://127.0.0.1:8766"
EXPECTED_VERSION = os.environ.get("PSM_EXPECT_VERSION", "PSM V0.253")


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    command = ["docker", "compose", "exec", "-T", "psm-chat", "python", "-m", "psm_v0.runtime_verifier"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or "Docker runtime verifier failed.")
    runtime = json.loads(next(line for line in completed.stdout.splitlines() if line.strip()))
    status = get_json("/api/status")
    first = post_json(
        "/api/chat",
        {
            "scenario": "code",
            "messages": [{"role": "user", "content": "请检查当前项目并运行测试。"}],
        },
    )
    first_graph = first["task_state_graph"]
    second = post_json(
        "/api/chat",
        {
            "scenario": "code",
            "messages": [
                {"role": "user", "content": "请检查当前项目并运行测试。"},
                {"role": "assistant", "content": first["chat"]["assistant_message"]},
                {"role": "user", "content": "再读取 `outputs/psm_v0/runtime/current_runtime_snapshot.json` 核验。"},
            ],
            "task_state_graph": first_graph,
        },
    )
    second_graph = second["task_state_graph"]
    graph_checks = {
        "schema": second_graph.get("schema_version") == "psm_task_state_graph_v1",
        "previous_graph_linked": second_graph["delta"].get("previous_graph_id") == first_graph.get("graph_id"),
        "delta_added_nodes": bool(second_graph["delta"].get("added_nodes")),
        "messages_bound": sum(node["kind"] == "message" for node in second_graph["nodes"]) >= 3,
        "file_source_bound": any(node["kind"] == "source" for node in second_graph["nodes"]),
        "dynamic_pi": second["packet"]["pi_cavity"].get("mode") == "task_evidence_graph",
        "dynamic_eta": second["packet"]["eta"].get("mode") == "task_evidence_state",
        "blind_backflow_off": second_graph["boundaries"].get("automatic_blind_set_backflow") is False,
        "training_backflow_off": second_graph["boundaries"].get("automatic_training_truth_backflow") is False,
        "external_release_closed": second_graph["boundaries"].get("external_release_authority") is False,
    }
    report = {
        "schema_version": "psm_v0_254_docker_verification_v1",
        "passed": (
            runtime.get("regression_passed") is True
            and runtime.get("high_risk_external_judge_retained") is True
            and status.get("version") == EXPECTED_VERSION
            and status.get("selected_chat_model") == "qwen3.5:9b"
            and first["route_execution"]["status"] == "success"
            and second["route_execution"]["status"] == "success"
            and all(graph_checks.values())
        ),
        "runtime": runtime,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "core_cases": status.get("core_cases"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
            "expected_version": EXPECTED_VERSION,
        },
        "graph_checks": graph_checks,
        "graph": {
            "first_graph_id": first_graph["graph_id"],
            "second_graph_id": second_graph["graph_id"],
            "nodes": len(second_graph["nodes"]),
            "edges": len(second_graph["edges"]),
            "state_counts": second_graph["state_counts"],
            "next_protocol": second_graph["next_protocol"],
            "delta": second_graph["delta"],
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit("V0.254 Docker verification failed.")


if __name__ == "__main__":
    main()
