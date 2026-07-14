from __future__ import annotations

import unittest

from psm_v0.pipeline import run_pipeline
from psm_v0.task_state_graph import (
    GRAPH_SCHEMA,
    build_failure_learning_queue,
    build_task_state_graph,
)


def route_execution(**overrides) -> dict:
    payload = {
        "status": "success",
        "route": "retrieval_or_tool_check",
        "adapters": [],
        "facts": [],
        "sources": [],
        "conflicts": {},
        "required_judges": ["source_or_tool_check", "external_judge"],
        "satisfied_judges": ["source_or_tool_check"],
        "unresolved_judges": ["external_judge"],
        "failure_events": [],
        "can_support_strong_claim": False,
    }
    payload.update(overrides)
    return payload


class TaskStateGraphTests(unittest.TestCase):
    def test_graph_binds_messages_sources_facts_and_pending_judges(self) -> None:
        result = run_pipeline("请查证当前项目状态")
        execution = route_execution(
            adapters=[
                {
                    "adapter": "local_project_status",
                    "status": "success",
                    "claims": {"project.current_version": "PSM V0.253"},
                }
            ],
            facts=["PSM V0.253"],
            sources=["outputs/psm_v0/CURRENT_STATUS.md"],
        )
        graph = build_task_state_graph(
            [{"role": "user", "content": "请查证当前项目状态"}],
            result,
            execution,
        )

        self.assertEqual(graph["schema_version"], GRAPH_SCHEMA)
        kinds = {node["kind"] for node in graph["nodes"]}
        self.assertTrue({"message", "task", "adapter", "source", "fact", "claim", "judge"} <= kinds)
        pending_judges = [
            node for node in graph["nodes"] if node["kind"] == "judge" and node["state"] == "pending"
        ]
        self.assertEqual([node["label"] for node in pending_judges], ["external_judge"])
        self.assertEqual(graph["next_protocol"]["action"], "obtain_required_judges")
        self.assertFalse(graph["boundaries"]["prior_client_graph_is_evidence"])

    def test_new_evidence_produces_explainable_delta(self) -> None:
        result = run_pipeline("读取 README.md 并说明项目状态")
        first = build_task_state_graph(
            [{"role": "user", "content": "读取 README.md 并说明项目状态"}],
            result,
            route_execution(status="not_executed", satisfied_judges=[]),
        )
        second = build_task_state_graph(
            [
                {"role": "user", "content": "读取 README.md 并说明项目状态"},
                {"role": "assistant", "content": "我需要先读取文件。"},
                {"role": "user", "content": "继续读取。"},
            ],
            result,
            route_execution(
                facts=["README.md: Property-State Model"],
                sources=["README.md"],
                adapters=[{"adapter": "local_file_evidence", "status": "success", "claims": {}}],
            ),
            previous_graph=first,
        )

        delta = second["delta"]
        self.assertEqual(delta["previous_graph_id"], first["graph_id"])
        self.assertGreater(len(delta["added_nodes"]), 0)
        self.assertIn("Task state changed", delta["explanation"])
        self.assertNotEqual(second["graph_id"], first["graph_id"])

    def test_conflict_becomes_graph_state_and_changes_protocol(self) -> None:
        result = run_pipeline("核验两个来源是否冲突")
        graph = build_task_state_graph(
            [{"role": "user", "content": "核验两个来源是否冲突"}],
            result,
            route_execution(
                status="conflict",
                conflicts={"project.current_version": ["PSM V0.252", "PSM V0.253"]},
                failure_events=[
                    {
                        "code": "evidence_conflict",
                        "reason": "Conflicting versions",
                        "route": "retrieval_or_tool_check",
                    }
                ],
            ),
        )

        self.assertGreater(graph["state_counts"]["conflicting"], 0)
        self.assertEqual(graph["next_protocol"]["action"], "resolve_evidence_conflicts")

    def test_failure_candidates_require_independent_screening_and_never_backflow(self) -> None:
        event = {
            "code": "tool_timeout",
            "reason": "The fixed tool timed out.",
            "route": "retrieval_or_tool_check",
        }
        initial = build_failure_learning_queue([event])
        candidate = initial["candidates"][0]
        self.assertFalse(candidate["eligible_for_regression"])
        self.assertFalse(candidate["eligible_for_blind_set"])
        self.assertFalse(candidate["eligible_for_training_truth"])

        screened = build_failure_learning_queue(
            [event],
            independent_screening={
                candidate["candidate_id"]: {
                    "decision": "approved",
                    "reviewer_independent": True,
                    "reviewer_id": "external_reviewer_1",
                }
            },
        )
        screened_candidate = screened["candidates"][0]
        self.assertTrue(screened_candidate["eligible_for_regression"])
        self.assertFalse(screened_candidate["eligible_for_blind_set"])
        self.assertFalse(screened_candidate["eligible_for_training_truth"])
        self.assertEqual(screened["blind_set_backflow_count"], 0)
        self.assertEqual(screened["training_truth_backflow_count"], 0)


if __name__ == "__main__":
    unittest.main()
