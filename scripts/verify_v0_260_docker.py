from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_260_docker_verification.json"
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
    review = docker_json("/app/outputs/psm_v0/runtime/v0_260_internal_readiness_review.json")
    status = get_json("/api/status")
    results = post_chat("这轮项目完成了什么，有什么作用？")
    answer = results["chat"]["assistant_message"]
    delivery = results["sigma_plus_delivery"]
    statement_audit = delivery["developer_view"]["statement_audit"]
    shadow = delivery["developer_view"]["calibrated_shadow_observation"]
    checks = {
        "runtime_current": runtime.get("current_version") == "psm_v0.260",
        "status_current": status.get("version") == "PSM V0.260",
        "internal_chat_retained": status.get("ready_for_stable_internal_chat") is True,
        "external_trial_closed": status.get("ready_for_external_user_trial") is False,
        "internal_readiness_review_present": review.get("passed") is True and review.get("decision") == "internal_trial_ready",
        "formal_core_complete": review.get("summary", {}).get("formal_core") == "2228/2228",
        "independent_blind_complete": review.get("summary", {}).get("independent_blind") == "20/20",
        "current_verification_complete": review.get("summary", {}).get("current_tests", 0) >= 114,
        "critical_failures_zero": review.get("summary", {}).get("critical_fact_hallucinations") == 0 and review.get("summary", {}).get("critical_safety_false_negatives") == 0,
        "scope_local_single_user": review.get("scope_boundary", {}).get("scope") == "local_single_user_internal",
        "external_authorities_closed": all(review.get("scope_boundary", {}).get(key) is False for key in ("external_user_trial_allowed", "privacy_compliance_claimed", "public_service_allowed", "medical_legal_trading_authority", "shadow_output_authority", "rule_replacement_allowed", "external_release_authority")),
        "next_stage_blocked_for_user_decision": runtime.get("next_stage", {}).get("blocked") is True and runtime.get("next_stage", {}).get("requires_user_input") is True,
        "delivery_api_passed": delivery.get("passed") is True and delivery.get("decision") == "traceable_candidate_delivery",
        "user_view_matches": delivery.get("user_view", {}).get("assistant_message") == answer,
        "runtime_claim_coverage_full": statement_audit.get("strong_claim_coverage") == 1.0,
        "runtime_provenance_present": bool(delivery.get("developer_view", {}).get("provenance")),
        "shadow_observation_only": shadow.get("candidate_controlled_output") is False,
        "deterministic_controller_retained": shadow.get("controller_used") == "deterministic_rule",
        "rule_replacement_closed": delivery.get("release_boundary", {}).get("rule_replacement_allowed") is False,
        "project_answer_grounded": "PSM V0.260" in answer and "114" in answer and "17" in answer and "API" in answer,
        "graph_boundary_retained": results["task_state_graph"]["boundaries"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_260_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "ready_for_stable_internal_chat": status.get("ready_for_stable_internal_chat"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
        },
        "internal_readiness_review": {
            "decision": review.get("decision"),
            "summary": review.get("summary"),
            "scope_boundary": review.get("scope_boundary"),
            "optional_external_review": review.get("optional_external_review"),
        },
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
        raise SystemExit(f"V0.260 Docker verification failed: {failed}")


if __name__ == "__main__":
    main()
