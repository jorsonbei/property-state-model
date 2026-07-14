from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.253_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.254_project_status.json"
GRAPH_REPORT = PSM_ROOT / "runtime" / "v0_254_task_state_graph_report.json"
QUEUE_REPORT = PSM_ROOT / "runtime" / "v0_254_failure_learning_queue.json"
BROWSER_REPORT = PSM_ROOT / "runtime" / "v0_254_browser_regression" / "report.json"
DOCKER_REPORT = PSM_ROOT / "runtime" / "v0_254_docker_verification.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_254_state_checkpoint.json"
MANIFEST = PSM_ROOT / "runtime" / "v0_254_state_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(graph: dict, queue: dict, browser: dict, docker: dict) -> None:
    checks = graph.get("checks") or {}
    if graph.get("passed") is not True or not all(checks.values()):
        raise SystemExit("V0.254 task-state graph report is not passing.")
    expected_states = {"known", "inferred", "unknown", "conflicting", "pending"}
    if set(graph.get("summary", {}).get("observed_claim_states") or []) != expected_states:
        raise SystemExit("V0.254 did not exercise every required claim state.")
    if queue.get("screened_count") != 1:
        raise SystemExit("V0.254 independent failure screening fixture did not pass.")
    if queue.get("blind_set_backflow_count") != 0 or queue.get("training_truth_backflow_count") != 0:
        raise SystemExit("V0.254 failure candidates crossed a protected backflow boundary.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.254 real browser regression is not passing.")
    route = browser.get("route_evidence") or {}
    if route.get("task_graph_visible_in_debug") is not True:
        raise SystemExit("V0.254 task graph is not visible in the debug panel.")
    if route.get("task_graph_delta_visible_after_new_evidence") is not True:
        raise SystemExit("V0.254 browser did not expose a multi-turn graph delta.")
    if docker.get("passed") is not True or not all((docker.get("graph_checks") or {}).values()):
        raise SystemExit("V0.254 Docker task graph verification is not passing.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    graph = read_json(GRAPH_REPORT)
    queue = read_json(QUEUE_REPORT)
    browser = read_json(BROWSER_REPORT)
    docker = read_json(DOCKER_REPORT)
    validate(graph, queue, browser, docker)

    state_gate = {
        "graph_report": "runtime/v0_254_task_state_graph_report.json",
        "failure_queue": "runtime/v0_254_failure_learning_queue.json",
        "browser_report": "runtime/v0_254_browser_regression/report.json",
        "docker_report": "runtime/v0_254_docker_verification.json",
        "graphs": graph["summary"]["graphs"],
        "claim_states": graph["summary"]["observed_claim_states"],
        "node_kinds": graph["summary"]["observed_node_kinds"],
        "graph_deltas": graph["summary"]["graph_deltas"],
        "independently_screened_failure_candidates": queue["screened_count"],
        "blind_set_backflow": queue["blind_set_backflow_count"],
        "training_truth_backflow": queue["training_truth_backflow_count"],
    }
    checkpoint = {
        "schema_version": "psm_v0_254_state_checkpoint_v1",
        "current_promoted_version": "PSM_V0.254",
        "target_version": "PSM_V0.254",
        "target_promoted": True,
        "status": "promoted_v0_255_internal_chat_alpha_gate_in_progress",
        "requires_user_input": False,
        "state_gate": state_gate,
        "completed_engineering": [
            "task-level Pi graph for messages, sources, adapters, facts, claims, unknowns, failures, and judges",
            "known, inferred, unknown, conflicting, and pending node states",
            "stable graph identity and explainable multi-turn graph delta",
            "dynamic Pi and eta packet projection from current task evidence",
            "next-protocol selection for conflicts, failures, pending judges, unknowns, and bounded output",
            "independently screened failure-learning queue with blind/training backflow sealed",
            "debug-only graph metrics and multi-turn browser continuity",
            "host and Docker task-graph evaluation",
        ],
        "release_boundary": {
            "external_user_trial_allowed": False,
            "arbitrary_high_risk_external_judge_satisfied": False,
            "automatic_blind_set_backflow": False,
            "automatic_training_truth_backflow": False,
            "rule_replacement_allowed": False,
            "internal_local_demo_only": True,
            "v0_254_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.255 内部聊天 Alpha 总门：复核冻结盲集与失败账本、"
            "多轮状态连续性、项目接地、高风险帮助式边界、关键幻觉与浏览器/API 回归；外部试用继续关闭。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.254"
    target["previous_formal_version"] = "psm_v0.253"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "dynamic_pi_eta_and_screened_failure_learning"
    target["task_state_gate"] = state_gate
    target["next_stage"] = {
        "version": "PSM_V0.255",
        "objective": (
            "Run the internal chat Alpha gate across the frozen blind-chat evidence, multi-turn task-state continuity, "
            "project grounding, ordinary chat, high-risk helpful boundaries, browser/API regression, and zero critical "
            "fact-hallucination or safety false-negative thresholds while external-user trial remains closed."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "task_state_gate": "runtime/v0_254_task_state_graph_report.json",
            "failure_learning_queue": "runtime/v0_254_failure_learning_queue.json",
            "task_state_browser_gate": "runtime/v0_254_browser_regression/report.json",
            "task_state_docker_gate": "runtime/v0_254_docker_verification.json",
            "task_state_checkpoint": "runtime/v0_254_state_checkpoint.json",
            "project_status": "project_status_out/psm_v0.254_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_254_state_promotion_manifest_v1",
        "version": "PSM_V0.254",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "state_gate": state_gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
