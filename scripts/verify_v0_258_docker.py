from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_258_docker_verification.json"
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
    gate = docker_json("/app/outputs/psm_v0/runtime/v0_258_calibrated_shadow_gate.json")
    calibration = docker_json("/app/outputs/psm_v0/runtime/v0_258_confidence_calibration.json")
    status = get_json("/api/status")
    results = post_chat("这轮项目完成了什么，有什么作用？")
    answer = results["chat"]["assistant_message"]
    checks = {
        "runtime_current": runtime.get("current_version") == "psm_v0.258",
        "status_current": status.get("version") == "PSM V0.258",
        "internal_chat_retained": status.get("ready_for_stable_internal_chat") is True,
        "external_trial_closed": status.get("ready_for_external_user_trial") is False,
        "calibrated_gate_present": gate.get("passed") is True and gate.get("decision") == "calibrated_shadow_ready",
        "evaluation_coverage": gate.get("summary", {}).get("average_evaluation_coverage") == 0.95918367,
        "selective_accuracy": gate.get("summary", {}).get("minimum_evaluation_selective_accuracy") == 0.92857143,
        "critical_false_negatives_zero": gate.get("summary", {}).get("accepted_critical_false_negatives") == 0,
        "low_confidence_abstentions": gate.get("summary", {}).get("evaluation_low_confidence_abstentions") == 4,
        "unresolved_fail_closed": gate.get("summary", {}).get("unresolved_consensus_forced_abstentions") == 7,
        "protected_backflow_zero": gate.get("summary", {}).get("protected_feedback_to_base_training") == 0,
        "seven_calibrated_heads": len(calibration.get("temperatures") or {}) == 7 and len(calibration.get("thresholds") or {}) == 7,
        "base_weights_frozen": calibration.get("boundary", {}).get("base_weights_changed") is False,
        "shadow_only": gate.get("boundaries", {}).get("candidate_shadow_only") is True,
        "rule_replacement_closed": gate.get("boundaries", {}).get("rule_replacement_allowed") is False,
        "project_answer_grounded": "PSM V0.258" in answer and "95.92" in answer and "shadow" in answer,
        "graph_boundary_retained": results["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_258_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "ready_for_stable_internal_chat": status.get("ready_for_stable_internal_chat"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
        },
        "calibrated_shadow_gate": gate.get("summary"),
        "calibration": {
            "temperatures": calibration.get("temperatures"),
            "thresholds": calibration.get("thresholds"),
            "boundary": calibration.get("boundary"),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.258 Docker verification failed: {failed}")


if __name__ == "__main__":
    main()
