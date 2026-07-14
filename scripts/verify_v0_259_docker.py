from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_259_docker_verification.json"
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
    gate = docker_json("/app/outputs/psm_v0/runtime/v0_259_sigma_plus_gate.json")
    status = get_json("/api/status")
    results = post_chat("这轮项目完成了什么，有什么作用？")
    answer = results["chat"]["assistant_message"]
    delivery = results["sigma_plus_delivery"]
    statement_audit = delivery["developer_view"]["statement_audit"]
    shadow = delivery["developer_view"]["calibrated_shadow_observation"]
    checks = {
        "runtime_current": runtime.get("current_version") == "psm_v0.259",
        "status_current": status.get("version") == "PSM V0.259",
        "internal_chat_retained": status.get("ready_for_stable_internal_chat") is True,
        "external_trial_closed": status.get("ready_for_external_user_trial") is False,
        "sigma_plus_gate_present": gate.get("passed") is True and gate.get("decision") == "sigma_plus_delivery_ready",
        "all_frozen_cases_pass": gate.get("summary", {}).get("delivery_passed") == 15,
        "strong_claim_coverage_full": gate.get("summary", {}).get("minimum_strong_claim_coverage") == 1.0,
        "ordinary_debug_leaks_zero": gate.get("summary", {}).get("ordinary_internal_debug_leaks") == 0,
        "candidate_output_authority_zero": gate.get("summary", {}).get("candidate_controlled_outputs") == 0,
        "delivery_api_passed": delivery.get("passed") is True and delivery.get("decision") == "traceable_candidate_delivery",
        "user_view_matches": delivery.get("user_view", {}).get("assistant_message") == answer,
        "runtime_claim_coverage_full": statement_audit.get("strong_claim_coverage") == 1.0,
        "runtime_provenance_present": bool(delivery.get("developer_view", {}).get("provenance")),
        "shadow_observation_only": shadow.get("candidate_controlled_output") is False,
        "deterministic_controller_retained": shadow.get("controller_used") == "deterministic_rule",
        "rule_replacement_closed": delivery.get("release_boundary", {}).get("rule_replacement_allowed") is False,
        "project_answer_grounded": "PSM V0.259" in answer and "22" in answer and "Sigma+" in answer,
        "graph_boundary_retained": results["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_259_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "ready_for_stable_internal_chat": status.get("ready_for_stable_internal_chat"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
        },
        "sigma_plus_gate": gate.get("summary"),
        "delivery": {
            "decision": delivery.get("decision"),
            "statement_audit": statement_audit,
            "provenance_count": len(delivery.get("developer_view", {}).get("provenance") or []),
            "shadow": shadow,
            "release_boundary": delivery.get("release_boundary"),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.259 Docker verification failed: {failed}")


if __name__ == "__main__":
    main()
