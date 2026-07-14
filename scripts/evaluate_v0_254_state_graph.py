from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
REPORT_PATH = PSM_ROOT / "runtime" / "v0_254_task_state_graph_report.json"
QUEUE_PATH = PSM_ROOT / "runtime" / "v0_254_failure_learning_queue.json"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.pipeline import run_pipeline  # noqa: E402
from psm_v0.route_executor import execute_route  # noqa: E402
from psm_v0.task_state_graph import (  # noqa: E402
    build_failure_learning_queue,
    build_task_state_graph,
)


def execute(question: str, intent: str = "general") -> tuple[dict, dict]:
    result = run_pipeline(question)
    route = execute_route(
        question,
        intent=intent,
        pipeline_result=result,
        project_root=ROOT,
        psm_root=PSM_ROOT,
    )
    return result, route


def main() -> None:
    project_result, project_route = execute("项目现在做到哪里了？", "project_status")
    project_graph = build_task_state_graph(
        [{"role": "user", "content": "项目现在做到哪里了？"}],
        project_result,
        project_route,
    )

    file_question = "请读取 `outputs/psm_v0/CURRENT_STATUS.md`。"
    file_result, file_route = execute(file_question)
    file_graph = build_task_state_graph(
        [{"role": "user", "content": file_question}],
        file_result,
        file_route,
        previous_graph=project_graph,
    )

    code_question = "请静态检查：\n```python\nvalue = max([])\n```"
    code_result, code_route = execute(code_question)
    code_graph = build_task_state_graph(
        [{"role": "user", "content": code_question}],
        code_result,
        code_route,
        previous_graph=file_graph,
    )

    failure_event = {
        "code": "tool_timeout",
        "reason": "The fixed project verification command timed out.",
        "route": "retrieval_or_tool_check",
        "status": "timeout",
    }
    conflict_route = {
        "status": "conflict",
        "route": "retrieval_or_tool_check",
        "adapters": [],
        "facts": [],
        "sources": [],
        "conflicts": {"fixture.claim": ["A", "B"]},
        "required_judges": ["source_or_tool_check"],
        "satisfied_judges": [],
        "unresolved_judges": ["source_or_tool_check"],
        "failure_events": [
            {
                "code": "evidence_conflict",
                "reason": "Conflicting values for fixture.claim",
                "route": "retrieval_or_tool_check",
            }
        ],
        "can_support_strong_claim": False,
    }
    conflict_result = run_pipeline("请核验冲突证据。")
    conflict_graph = build_task_state_graph(
        [{"role": "user", "content": "请核验冲突证据。"}],
        conflict_result,
        conflict_route,
        previous_graph=code_graph,
    )

    initial_queue = build_failure_learning_queue([failure_event])
    candidate_id = initial_queue["candidates"][0]["candidate_id"]
    screened_queue = build_failure_learning_queue(
        [failure_event],
        independent_screening={
            candidate_id: {
                "decision": "approved",
                "reviewer_independent": True,
                "reviewer_id": "v0_254_independent_fixture",
            }
        },
    )
    candidate = screened_queue["candidates"][0]

    graphs = [project_graph, file_graph, code_graph, conflict_graph]
    observed_kinds = sorted({node["kind"] for graph in graphs for node in graph["nodes"]})
    observed_states = sorted({node["state"] for graph in graphs for node in graph["nodes"]})
    checks = {
        "messages_bound": "message" in observed_kinds,
        "files_bound": any(node["kind"] == "source" for node in file_graph["nodes"]),
        "tools_bound": any(node["kind"] == "adapter" for node in code_graph["nodes"]),
        "judges_bound": "judge" in observed_kinds,
        "all_claim_states_present": set(observed_states)
        == {"known", "inferred", "unknown", "conflicting", "pending"},
        "file_route_real": file_route["status"] == "success" and bool(file_route["sources"]),
        "code_route_real": code_route["status"] == "success"
        and any(item["adapter"] == "sandboxed_code_check" for item in code_route["adapters"]),
        "delta_explained": bool(file_graph["delta"]["added_nodes"])
        and "Task state changed" in file_graph["delta"]["explanation"],
        "conflict_changes_protocol": conflict_graph["next_protocol"]["action"]
        == "resolve_evidence_conflicts",
        "independent_screening_required": candidate["independent_screening_required"] is True,
        "screened_regression_candidate": candidate["eligible_for_regression"] is True,
        "blind_backflow_zero": candidate["eligible_for_blind_set"] is False
        and screened_queue["blind_set_backflow_count"] == 0,
        "training_backflow_zero": candidate["eligible_for_training_truth"] is False
        and screened_queue["training_truth_backflow_count"] == 0,
        "external_release_closed": all(
            graph["boundaries"]["external_release_authority"] is False for graph in graphs
        ),
    }
    report = {
        "schema_version": "psm_v0_254_task_state_graph_report_v1",
        "version": "PSM_V0.254-candidate",
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {
            "graphs": len(graphs),
            "observed_node_kinds": observed_kinds,
            "observed_claim_states": observed_states,
            "real_route_adapters": sorted(
                {
                    item["adapter"]
                    for route in (project_route, file_route, code_route)
                    for item in route["adapters"]
                }
            ),
            "graph_deltas": sum(graph["delta"]["previous_graph_id"] is not None for graph in graphs),
            "failure_candidates": screened_queue["candidate_count"],
            "independently_screened": screened_queue["screened_count"],
            "blind_set_backflow": screened_queue["blind_set_backflow_count"],
            "training_truth_backflow": screened_queue["training_truth_backflow_count"],
            "external_release_authority": False,
            "rule_replacement_allowed": False,
        },
        "graphs": [
            {
                "graph_id": graph["graph_id"],
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
                "state_counts": graph["state_counts"],
                "next_protocol": graph["next_protocol"],
                "delta": graph["delta"],
            }
            for graph in graphs
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    QUEUE_PATH.write_text(json.dumps(screened_queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if not report["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"V0.254 task-state graph evaluation failed: {failed}")


if __name__ == "__main__":
    main()
