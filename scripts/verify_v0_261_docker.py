from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_261_docker_verification.json"
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
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def docker_json(path: str) -> dict:
    completed = subprocess.run(
        ["docker", "compose", "exec", "-T", "psm-chat", "python", "-c", f"import json,pathlib;p=pathlib.Path('{path}');print(json.dumps(json.loads(p.read_text())))"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or "Docker verifier command failed.")
    return json.loads(next(line for line in completed.stdout.splitlines() if line.strip()))


def main() -> None:
    runtime = docker_json("/app/outputs/psm_v0/runtime/current_runtime_snapshot.json")["project_status"]
    initial = docker_json("/app/outputs/psm_v0/runtime/v0_261_openai_external_contract_judge_attempt_1_failed.json")
    repair = docker_json("/app/outputs/psm_v0/runtime/v0_261_annotation_contract_repair_gate.json")
    final = docker_json("/app/outputs/psm_v0/runtime/v0_261_openai_external_contract_judge.json")
    status = get_json("/api/status")
    result = post_chat("这轮项目完成了什么，有什么作用？")
    answer = result["chat"]["assistant_message"]
    delivery = result["sigma_plus_delivery"]
    checks = {
        "runtime_current": runtime.get("current_version") == "psm_v0.261",
        "status_current": status.get("version") == "PSM V0.261",
        "internal_chat_retained": status.get("ready_for_stable_internal_chat") is True,
        "external_trial_closed": status.get("ready_for_external_user_trial") is False,
        "initial_external_failure_retained": initial.get("passed") is False and initial.get("review", {}).get("verdict") == "fail",
        "repair_gate_passed": repair.get("passed") is True and all((repair.get("checks") or {}).values()),
        "final_external_passed": final.get("passed") is True and final.get("review", {}).get("verdict") == "pass",
        "five_questions_passed": len(final.get("review", {}).get("question_reviews") or []) == 5 and all(item.get("verdict") == "pass" for item in final["review"]["question_reviews"]),
        "no_final_findings": not final.get("review", {}).get("failed_checks") and not final.get("review", {}).get("critical_findings") and not final.get("review", {}).get("recommended_repairs"),
        "secret_not_persisted": final.get("api_key_persisted_in_artifact") is False,
        "synthetic_scope_retained": final.get("submission_scope", {}).get("synthetic_only") is True and final.get("submission_scope", {}).get("contains_private_data") is False,
        "external_authorities_closed": all(final.get("release_boundary", {}).get(name) is False for name in ("training_authority", "rule_replacement_authority", "external_user_trial_allowed", "public_service_allowed", "external_release_authority")),
        "next_stage_blocked_for_user_decision": runtime.get("next_stage", {}).get("blocked") is True and runtime.get("next_stage", {}).get("requires_user_input") is True,
        "delivery_api_passed": delivery.get("passed") is True,
        "project_answer_current": "PSM V0.261" in answer and "5/5" in answer and "外部用户" in answer,
        "graph_boundary_retained": result["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_261_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "status": status,
        "external_review": {
            "initial_verdict": initial["review"]["verdict"],
            "repair_decision": repair["decision"],
            "final_verdict": final["review"]["verdict"],
            "question_passes": sum(item["verdict"] == "pass" for item in final["review"]["question_reviews"]),
            "contract_sha256": final["contract_sha256"],
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(f"V0.261 Docker verification failed: {[name for name, value in checks.items() if not value]}")


if __name__ == "__main__":
    main()
