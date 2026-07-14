from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_257_docker_verification.json"
BASE_URL = "http://127.0.0.1:8766"


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_chat(text: str) -> dict:
    request = urllib.request.Request(
        BASE_URL + "/api/chat",
        data=json.dumps({"messages": [{"role": "user", "content": text}], "scenario": "review"}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def docker_json(path: str) -> dict:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "psm-chat",
        "python",
        "-c",
        f"import json,pathlib;p=pathlib.Path('{path}');print(json.dumps(json.loads(p.read_text())))",
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or "Docker verifier command failed.")
    return json.loads(next(line for line in completed.stdout.splitlines() if line.strip()))


def main() -> None:
    runtime = docker_json("/app/outputs/psm_v0/runtime/current_runtime_snapshot.json")["project_status"]
    gate = docker_json("/app/outputs/psm_v0/runtime/v0_257_shadow_encoder_gate.json")
    model = docker_json("/app/outputs/psm_v0/runtime/v0_257_shadow_encoder_model.json")
    status = get_json("/api/status")
    results = post_chat("这轮项目完成了什么，有什么作用？")
    answer = results["chat"]["assistant_message"]
    checks = {
        "runtime_current": runtime.get("current_version") == "psm_v0.257",
        "status_current": status.get("version") == "PSM V0.257",
        "internal_chat_retained": status.get("ready_for_stable_internal_chat") is True,
        "external_trial_closed": status.get("ready_for_external_user_trial") is False,
        "shadow_gate_present": gate.get("passed") is True and gate.get("decision") == "shadow_baseline_ready",
        "candidate_validation_exact": gate.get("summary", {}).get("candidate_validation_exact_match") == 0.928571,
        "candidate_test_exact": gate.get("summary", {}).get("candidate_test_exact_match") == 1.0,
        "candidate_critical_false_negatives_zero": gate.get("summary", {}).get("candidate_validation_critical_false_negatives") == 0
        and gate.get("summary", {}).get("candidate_test_critical_false_negatives") == 0,
        "protected_backflow_zero": gate.get("summary", {}).get("protected_backflow") == 0,
        "model_has_seven_heads": len(model.get("targets") or {}) == 7,
        "feature_boundary_retained": model.get("feature_policy", {}).get("source_identity") is False
        and model.get("feature_policy", {}).get("judge_fields") is False,
        "shadow_only": model.get("boundary", {}).get("shadow_only") is True,
        "rule_replacement_closed": model.get("boundary", {}).get("rule_replacement_allowed") is False,
        "project_answer_grounded": "PSM V0.257" in answer and "42" in answer and "shadow" in answer,
        "graph_boundary_retained": results["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_257_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "ready_for_stable_internal_chat": status.get("ready_for_stable_internal_chat"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
        },
        "shadow_gate": gate.get("summary"),
        "model": {
            "model_type": model.get("model_type"),
            "training_rows": model.get("training_rows"),
            "targets": sorted((model.get("targets") or {}).keys()),
            "boundary": model.get("boundary"),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.257 Docker verification failed: {failed}")


if __name__ == "__main__":
    main()
