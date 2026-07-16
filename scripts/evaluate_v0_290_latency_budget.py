#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import time
import uuid
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
CONTRACT = PSM_ROOT / "benchmarks" / "v0_290_latency_budget_contract.json"
REPORT = PSM_ROOT / "runtime" / "v0_290_latency_budget_report.json"
GATE = PSM_ROOT / "runtime" / "v0_290_latency_budget_gate.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_290_latency_budget_checkpoint.json"
LOSS_MARKER = "无法读取先前会话内容"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def timed_chat(base_url: str, runtime_id: str, case_id: str, text: str, event: str) -> dict:
    status = request_json(f"{base_url}/api/status")
    started = time.perf_counter()
    response = request_json(
        f"{base_url}/api/chat",
        {
            "scenario": "review",
            "session_id": f"v290_{runtime_id}_{case_id}_{uuid.uuid4().hex}",
            "continuity_event": event,
            "server_instance_id": status["continuity_instance_id"],
            "messages": [{"id": 1, "role": "user", "content": text}],
        },
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    generation = response["chat"]["generation"]
    continuity = response["chat"]["state_continuity"]["continuity_status"]
    answer = response["chat"]["assistant_message"]
    return {
        "case_id": case_id,
        "duration_ms": elapsed_ms,
        "generation_status": generation["status"],
        "provider": generation["provider"],
        "attempted_provider": generation.get("attempted_provider"),
        "fallback_used": generation["status"] != "success",
        "continuity_state": continuity["state"],
        "answer_nonempty": bool(answer.strip()),
        "recovery_boundary_visible": LOSS_MARKER in answer,
    }


def summarize(rows: list[dict], limit_ms: int) -> dict:
    durations = [row["duration_ms"] for row in rows]
    success = [row for row in rows if row["generation_status"] == "success" and row["answer_nonempty"]]
    fallbacks = [row for row in rows if row["fallback_used"]]
    return {
        "samples": len(rows),
        "successes": len(success),
        "success_rate": len(success) / len(rows),
        "fallbacks": len(fallbacks),
        "p50_ms": round(statistics.median(durations), 2),
        "p95_ms": round(max(durations), 2),
        "minimum_ms": round(min(durations), 2),
        "maximum_ms": round(max(durations), 2),
        "limit_ms": limit_ms,
        "passed": len(success) == len(rows) and not fallbacks and max(durations) <= limit_ms,
    }


def evaluate_runtime(runtime: dict, contract: dict) -> dict:
    base_url = runtime["base_url"]
    runtime_id = runtime["runtime_id"]
    status = request_json(f"{base_url}/api/status")
    rows = {
        "deterministic_recovery": [
            timed_chat(base_url, runtime_id, f"R{index + 1:02d}", "那个项目代号来着？", "reset")
            for index in range(5)
        ],
        "deterministic_identity": [
            timed_chat(base_url, runtime_id, f"I{index + 1:02d}", "你好，你是谁？", "active")
            for index in range(5)
        ],
        "local_model_generation": [
            timed_chat(base_url, runtime_id, f"G{index + 1:02d}", text, "active")
            for index, text in enumerate((
                "请给这个新项目起个代号。",
                "新文件应该叫什么？",
                "安排一个新的会议时间。",
            ))
        ],
    }
    limits = {item["category"]: item["p95_limit_ms"] for item in contract["measurement"]["categories"]}
    summaries = {category: summarize(values, limits[category]) for category, values in rows.items()}
    semantic_checks = {
        "recovery_answers_show_boundary": all(row["recovery_boundary_visible"] for row in rows["deterministic_recovery"]),
        "identity_uses_deterministic_provider": all(row["provider"] == "deterministic" for row in rows["deterministic_identity"]),
        "normal_generation_uses_model_provider": all(row["provider"] != "deterministic" for row in rows["local_model_generation"]),
    }
    return {
        "runtime_id": runtime_id,
        "base_url": base_url,
        "version": status["version"],
        "summaries": summaries,
        "semantic_checks": semantic_checks,
        "rows": rows,
        "passed": status["version"] == "PSM V0.289" and all(item["passed"] for item in summaries.values()) and all(semantic_checks.values()),
    }


def main() -> None:
    contract = read(CONTRACT)
    runtimes = [evaluate_runtime(runtime, contract) for runtime in contract["measurement"]["runtimes"]]
    checks = {
        "host_all_latency_categories_pass": runtimes[0]["passed"],
        "docker_all_latency_categories_pass": runtimes[1]["passed"],
        "both_versions_are_v0_289": all(runtime["version"] == "PSM V0.289" for runtime in runtimes),
        "all_success_rates_exact": all(
            summary["success_rate"] == 1.0
            for runtime in runtimes
            for summary in runtime["summaries"].values()
        ),
        "fallbacks_zero": all(
            summary["fallbacks"] == 0
            for runtime in runtimes
            for summary in runtime["summaries"].values()
        ),
        "external_release_closed": contract["release_boundary"]["external_release_authority"] is False,
    }
    report = {
        "schema_version": "psm_v0_290_latency_budget_report_v1",
        "version": "PSM_V0.290-candidate",
        "synthetic_only": True,
        "runtimes": runtimes,
        "checks": checks,
        "passed": all(checks.values()),
        "human_validation_claimed": False,
        "persistent_conversation_memory_enabled": False,
        "external_release_authority": False,
    }
    gate = {
        "schema_version": "psm_v0_290_latency_budget_gate_v1",
        "decision": "latency_budget_gate_passed" if report["passed"] else "latency_budget_gate_failed",
        "passed": report["passed"],
        "checks": checks,
        "host": runtimes[0]["summaries"],
        "docker": runtimes[1]["summaries"],
        "external_release_authority": False,
    }
    checkpoint = {
        "schema_version": "psm_v0_290_latency_budget_checkpoint_v1",
        "status": "latency_gate_passed" if report["passed"] else "latency_gate_failed",
        "requires_user_input": False,
        "next_action": "promote_v0_290_latency_budget" if report["passed"] else "repair_latency_bottleneck",
    }
    write(REPORT, report)
    write(GATE, gate)
    write(CHECKPOINT, checkpoint)
    for runtime in runtimes:
        print(runtime["runtime_id"], json.dumps(runtime["summaries"], ensure_ascii=False))
    print(f"passed: {report['passed']}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
