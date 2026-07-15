from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "runtime" / "v0_262_docker_verification.json"
BASE_URL = "http://127.0.0.1:8766"
PROTOCOL = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_chat(text: str) -> dict:
    request = urllib.request.Request(
        BASE_URL + "/api/chat",
        data=json.dumps(
            {"messages": [{"role": "user", "content": text}], "scenario": "review"},
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def docker_json(path: str) -> dict:
    code = (
        "import json,pathlib;"
        f"p=pathlib.Path({path!r});"
        "print(json.dumps(json.loads(p.read_text())))"
    )
    completed = subprocess.run(
        ["docker", "compose", "exec", "-T", "psm-chat", "python", "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or "Docker verifier command failed.")
    return json.loads(next(line for line in completed.stdout.splitlines() if line.strip()))


def published_port() -> str:
    completed = subprocess.run(
        ["docker", "compose", "port", "psm-chat", "8765"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr or "Docker port inspection failed.")
    return completed.stdout.strip()


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    protocol_sha = canonical_sha256(protocol)
    runtime = docker_json("/app/outputs/psm_v0/runtime/current_runtime_snapshot.json")[
        "project_status"
    ]
    local = docker_json(
        "/app/outputs/psm_v0/runtime/v0_262_external_trial_protocol_gate.json"
    )
    initial = docker_json(
        "/app/outputs/psm_v0/runtime/"
        "v0_262_openai_external_trial_protocol_judge_attempt_1_failed.json"
    )
    final = docker_json(
        "/app/outputs/psm_v0/runtime/v0_262_openai_external_trial_protocol_judge.json"
    )
    budget = docker_json("/app/outputs/psm_v0/runtime/v0_262_api_budget_ledger.json")
    checkpoint = docker_json(
        "/app/outputs/psm_v0/runtime/v0_262_external_trial_protocol_checkpoint.json"
    )
    status = get_json("/api/status")
    notice = get_json("/api/trial-notice")
    result = post_chat("这轮项目完成了什么，有什么作用？")
    answer = result["chat"]["assistant_message"]
    delivery = result["sigma_plus_delivery"]
    port = published_port()
    checks = {
        "localhost_only_publishing": port in {"127.0.0.1:8766", "[::1]:8766"},
        "runtime_current": runtime.get("current_version") == "psm_v0.262",
        "status_current": status.get("version") == "PSM V0.262",
        "internal_chat_retained": status.get("ready_for_stable_internal_chat") is True,
        "protocol_ready": status.get("ready_for_invite_only_external_trial_protocol") is True,
        "participant_range_is_three_to_five": (
            status.get("external_trial_participant_minimum") == 3
            and status.get("external_trial_participant_maximum") == 5
        ),
        "seven_day_metadata_retention": status.get("external_trial_metadata_retention_days") == 7,
        "twenty_dollar_monthly_cap": status.get("external_trial_monthly_api_budget_usd") == 20,
        "real_enrollment_not_claimed": status.get("external_trial_participant_enrollment_completed") is False,
        "external_trial_inactive": status.get("ready_for_external_user_trial") is False,
        "local_gate_passed": local.get("passed") is True and all((local.get("checks") or {}).values()),
        "local_twenty_of_twenty": sum((local.get("checks") or {}).values()) == 20,
        "eight_attacks_rejected": local.get("metrics", {}).get("attack_prompts_rejected") == 8,
        "initial_external_failure_retained": (
            initial.get("passed") is False
            and initial.get("review", {}).get("verdict") == "fail"
            and len(initial.get("review", {}).get("failed_checks") or []) == 2
        ),
        "final_external_passed": (
            final.get("passed") is True and final.get("review", {}).get("verdict") == "pass"
        ),
        "seven_questions_passed": (
            len(final.get("review", {}).get("question_reviews") or []) == 7
            and all(
                item.get("verdict") == "pass"
                for item in final.get("review", {}).get("question_reviews") or []
            )
        ),
        "no_final_findings": (
            not final.get("review", {}).get("failed_checks")
            and not final.get("review", {}).get("critical_findings")
            and not final.get("review", {}).get("recommended_repairs")
        ),
        "frozen_protocol_hash_matches": (
            local.get("protocol_sha256") == protocol_sha
            and final.get("protocol_sha256") == protocol_sha
        ),
        "participant_content_not_externalized": (
            final.get("submission_scope", {}).get("contains_participant_content") is False
            and budget.get("participant_content_calls") == 0
        ),
        "budget_within_cap": (
            float(budget.get("reserved_usd", 0)) == 4.0
            and float(budget.get("reserved_usd", 0)) <= float(budget.get("limit_usd", 0)) == 20.0
        ),
        "trial_notice_served_but_inactive": (
            notice.get("version") == "PSM V0.262"
            and "3 至 5" in notice.get("content", "")
            and notice.get("participant_enrollment_completed") is False
            and notice.get("trial_active") is False
            and notice.get("public_service_allowed") is False
        ),
        "v0_263_requires_real_participants": (
            runtime.get("next_stage", {}).get("version") == "PSM_V0.263"
            and runtime.get("next_stage", {}).get("blocked") is True
            and runtime.get("next_stage", {}).get("requires_user_input") is True
            and checkpoint.get("requires_user_input") is True
            and checkpoint.get("release_boundary", {}).get("external_user_trial_active") is False
        ),
        "delivery_api_passed": delivery.get("passed") is True,
        "project_answer_current": (
            "PSM V0.262" in answer
            and "20/20" in answer
            and "7/7" in answer
            and "V0.263" in answer
        ),
        "graph_boundary_retained": (
            result["task_state_graph"]["boundaries"]["external_release_authority"] is False
        ),
    }
    report = {
        "schema_version": "psm_v0_262_docker_verification_v1",
        "passed": all(checks.values()),
        "checks": checks,
        "published_port": port,
        "status": status,
        "protocol": {
            "sha256": protocol_sha,
            "local_checks_passed": sum((local.get("checks") or {}).values()),
            "attacks_rejected": local.get("metrics", {}).get("attack_prompts_rejected"),
            "initial_external_verdict": initial.get("review", {}).get("verdict"),
            "final_external_verdict": final.get("review", {}).get("verdict"),
            "final_question_passes": sum(
                item.get("verdict") == "pass"
                for item in final.get("review", {}).get("question_reviews") or []
            ),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, value in checks.items() if not value]
        raise SystemExit(f"V0.262 Docker verification failed: {failed}")


if __name__ == "__main__":
    main()
