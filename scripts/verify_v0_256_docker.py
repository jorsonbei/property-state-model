from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_256_docker_verification.json"
BASE_URL = "http://127.0.0.1:8766"


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_chat(messages: list[dict]) -> dict:
    request = urllib.request.Request(
        BASE_URL + "/api/chat",
        data=json.dumps({"messages": messages, "scenario": "review"}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def docker_json(command: list[str]) -> dict:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or "Docker verifier command failed.")
    return json.loads(next(line for line in completed.stdout.splitlines() if line.strip()))


def main() -> None:
    runtime = docker_json(
        ["docker", "compose", "exec", "-T", "psm-chat", "python", "-m", "psm_v0.runtime_verifier"]
    )
    gate = docker_json(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "psm-chat",
            "python",
            "-c",
            (
                "import json,pathlib;"
                "p=pathlib.Path('/app/outputs/psm_v0/runtime/v0_256_annotation_contract_gate.json');"
                "print(json.dumps(json.loads(p.read_text())))"
            ),
        ]
    )
    status = get_json("/api/status")
    project = post_chat([{"role": "user", "content": "这轮项目完成了什么，有什么作用？"}])
    answer = project["chat"]["assistant_message"]
    checks = {
        "runtime_current": runtime.get("current_version") == "psm_v0.256",
        "runtime_regression": runtime.get("regression_passed") is True,
        "high_risk_judge_retained": runtime.get("high_risk_external_judge_retained") is True,
        "status_current": status.get("version") == "PSM V0.256",
        "internal_alpha_retained": status.get("ready_for_stable_internal_chat") is True,
        "external_trial_closed": status.get("ready_for_external_user_trial") is False,
        "contract_gate_present": gate.get("passed") is True
        and gate.get("decision") == "contract_ready_training_not_started",
        "contract_no_leakage": gate.get("metrics", {}).get("candidate_input_leaks") == 0,
        "contract_no_backflow": gate.get("metrics", {}).get("protected_backflow") == 0,
        "training_not_started": gate.get("boundaries", {}).get("training_started") is False,
        "rule_replacement_closed": gate.get("boundaries", {}).get("rule_replacement_allowed") is False,
        "project_answer_grounded": "PSM V0.256" in answer
        and "8" in answer
        and any(marker in answer for marker in ("来源", "來源"))
        and "shadow" in answer,
        "graph_boundary_retained": project["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_256_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "runtime": runtime,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "ready_for_stable_internal_chat": status.get("ready_for_stable_internal_chat"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
        },
        "contract": {
            "decision": gate.get("decision"),
            "metrics": gate.get("metrics"),
            "boundaries": gate.get("boundaries"),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.256 Docker verification failed: {failed}")


if __name__ == "__main__":
    main()
