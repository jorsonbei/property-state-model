from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "runtime" / "v0_253_docker_verification.json"
BASE_URL = "http://127.0.0.1:8766"


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
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    runtime = json.loads(lines[0])
    status = get_json("/api/status")
    chat = post_json(
        "/api/chat",
        {
            "scenario": "code",
            "messages": [{"role": "user", "content": "请检查当前项目并运行测试。"}],
        },
    )
    adapter = chat["route_execution"]["adapters"][0]
    report = {
        "schema_version": "psm_v0_253_docker_verification_v1",
        "passed": (
            runtime.get("regression_passed") is True
            and runtime.get("high_risk_external_judge_retained") is True
            and status.get("selected_chat_model") == "qwen3.5:9b"
            and chat["route_execution"]["status"] == "success"
            and adapter.get("details", {}).get("command_id") == "verify_runtime"
            and chat["chat"]["quality_audit"]["status"] == "pass"
        ),
        "runtime": runtime,
        "status": {
            "version": status.get("version"),
            "selected_chat_model": status.get("selected_chat_model"),
            "chat_timeout_seconds": status.get("chat_timeout_seconds"),
            "core_cases": status.get("core_cases"),
            "ready_for_external_user_trial": status.get("ready_for_external_user_trial"),
        },
        "code_route": {
            "status": chat["route_execution"]["status"],
            "adapter": adapter["adapter"],
            "command_id": adapter["details"]["command_id"],
            "source": chat["route_execution"]["sources"][0],
            "quality": chat["chat"]["quality_audit"]["status"],
            "external_release_authority": chat["route_execution"]["external_release_authority"],
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit("V0.253 Docker verification failed.")


if __name__ == "__main__":
    main()
