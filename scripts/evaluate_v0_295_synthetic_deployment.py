#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_295_synthetic_deployment_contract.json"
AMENDMENT = PSM_ROOT / "runtime" / "v0_295_no_human_decision_amendment.json"
BASELINE = PSM_ROOT / "runtime" / "v0_295_synthetic_deployment_baseline.json"
REPORT = PSM_ROOT / "runtime" / "v0_295_synthetic_deployment_report.json"
GATE = PSM_ROOT / "runtime" / "v0_295_synthetic_deployment_gate.json"
RUNTIMES = (
    {"runtime_id": "host", "base_url": "http://127.0.0.1:8765"},
    {"runtime_id": "docker", "base_url": "http://127.0.0.1:8766"},
)
RETIRED_GET_PATHS = (
    "/api/trial-notice",
    "/api/trial-enrollment",
    "/api/trial-enrollment/operator-cards",
    "/trial-enrollment",
    "/trial-enrollment.html",
    "/trial-enrollment.js",
    "/trial-enrollment.css",
)
RETIRED_POST_PATHS = (
    "/api/trial-enrollment/action",
    "/api/trial-chat",
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request(base_url: str, path: str, payload: dict | None = None) -> tuple[int, bytes, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def parse_json(body: bytes) -> dict:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def evaluate_runtime(runtime: dict) -> dict:
    base_url = runtime["base_url"]
    root_status, root_body, _ = request(base_url, "/")
    status_code, status_body, _ = request(base_url, "/api/status")
    health_code, health_body, health_headers = request(base_url, "/api/health")
    status = parse_json(status_body)
    health = parse_json(health_body)
    retired_get = []
    for path in RETIRED_GET_PATHS:
        code, body, headers = request(base_url, path)
        retired_get.append(
            {
                "path": path,
                "status": code,
                "error": parse_json(body).get("error"),
                "cache_control": headers.get("Cache-Control"),
            }
        )
    retired_post = []
    for path in RETIRED_POST_PATHS:
        code, body, headers = request(base_url, path, {})
        retired_post.append(
            {
                "path": path,
                "status": code,
                "error": parse_json(body).get("error"),
                "cache_control": headers.get("Cache-Control"),
            }
        )
    checks = {
        "root_chat_200_without_enrollment_link": root_status == 200
        and b'id="enrollment-link"' not in root_body
        and b'href="/trial-enrollment"' not in root_body,
        "status_200_synthetic_only": status_code == 200
        and status.get("human_participant_workflow_enabled") is False
        and status.get("synthetic_validation_only") is True
        and status.get("ready_for_external_user_trial") is False
        and status.get("ready_for_invite_only_external_trial_protocol") is False
        and status.get("ready_for_supervised_invite_only_trial") is False
        and status.get("external_trial_participant_enrollment_completed") is False
        and status.get("external_trial_participant_minimum") == 0
        and status.get("external_trial_participant_maximum") == 0
        and status.get("v0_263_enrollment_interface_ready") is False,
        "health_200_no_store": health_code == 200
        and health.get("schema_version") == "psm_v0_294_content_free_health_v1"
        and health_headers.get("Cache-Control") == "no-store",
        "all_retired_get_paths_410": all(item["status"] == 410 for item in retired_get),
        "all_retired_post_paths_410_json_no_store": all(
            item["status"] == 410
            and item["error"] == "human_trial_workflow_retired"
            and item["cache_control"] == "no-store"
            for item in retired_post
        ),
    }
    return {
        "runtime_id": runtime["runtime_id"],
        "base_url": base_url,
        "version": status.get("version"),
        "retired_get": retired_get,
        "retired_post": retired_post,
        "checks": checks,
        "passed": all(checks.values()),
    }


def command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def main() -> None:
    contract = read(CONTRACT)
    amendment = read(AMENDMENT)
    baseline = read(BASELINE)
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package = read(ROOT / "package.json")
    runtimes = [evaluate_runtime(runtime) for runtime in RUNTIMES]
    uid = command("docker", "compose", "exec", "-T", "psm-chat", "id", "-u")
    notice = command(
        "docker",
        "compose",
        "exec",
        "-T",
        "psm-chat",
        "test",
        "!",
        "-e",
        "/app/outputs/psm_v0/V0_262_INVITE_ONLY_TRIAL_NOTICE.md",
    )
    checks = {
        "contract_frozen": contract.get("frozen_before_implementation") is True,
        "user_decision_recorded": amendment.get("user_decision") == "omit_invite_only_adult_participant_step",
        "zero_human_participants": contract.get("human_boundary", {}).get("human_participants") == 0,
        "baseline_retained": baseline.get("captured_before_implementation") is True,
        "host_passed": runtimes[0]["passed"],
        "docker_passed": runtimes[1]["passed"],
        "docker_non_root_uid_10001": uid.returncode == 0 and uid.stdout.strip() == "10001",
        "invite_notice_absent_from_container": notice.returncode == 0,
        "docker_healthcheck_content_free": "/api/health" in dockerfile and "/api/status" not in dockerfile.split("HEALTHCHECK", 1)[1],
        "docker_default_bind_loopback": '${PSM_DOCKER_BIND:-127.0.0.1}' in compose,
        "ci_python_matrix_and_container": all(
            marker in workflow
            for marker in ('python-version: ["3.11", "3.12"]', "make check", "docker build", "/api/health", "id -u")
        ),
        "ci_has_no_secret_or_external_call": all(
            marker not in workflow for marker in ("OPENAI_API_KEY", "secrets.", "api.openai.com")
        ),
        "package_versions_v0_295": 'version = "0.295.0"' in pyproject and package.get("version") == "0.295.0",
        "human_and_release_claims_closed": amendment.get("real_user_validation_claimed") is False
        and contract.get("release_boundary", {}).get("external_release_authority") is False,
    }
    report = {
        "schema_version": "psm_v0_295_synthetic_deployment_report_v1",
        "version": "PSM_V0.295-candidate",
        "contract": str(CONTRACT.relative_to(PSM_ROOT)),
        "amendment": str(AMENDMENT.relative_to(PSM_ROOT)),
        "runtimes": runtimes,
        "container_uid": uid.stdout.strip(),
        "invite_notice_in_container": notice.returncode != 0,
        "checks": checks,
        "passed": all(checks.values()),
        "human_participants": 0,
        "synthetic_only": True,
        "human_validation_claimed": False,
        "external_release_authority": False,
    }
    gate = {
        "schema_version": "psm_v0_295_synthetic_deployment_gate_v1",
        "decision": "synthetic_deployment_gate_passed" if report["passed"] else "synthetic_deployment_gate_failed",
        "passed": report["passed"],
        "checks": checks,
        "retired_endpoint_count_per_runtime": len(RETIRED_GET_PATHS) + len(RETIRED_POST_PATHS),
        "human_participants": 0,
        "external_release_authority": False,
    }
    write(REPORT, report)
    write(GATE, gate)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
