from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from psm_v0.pipeline import run_pipeline
from psm_v0.route_executor import (
    AdapterResult,
    CodeCheckAdapter,
    RouteContext,
    aggregate_route_results,
    execute_route,
)


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class RouteExecutorTests(unittest.TestCase):
    def execute(self, question: str, *, intent: str = "general", ledger_path: Path | None = None) -> dict:
        return execute_route(
            question,
            intent=intent,
            pipeline_result=run_pipeline(question),
            project_root=ROOT,
            psm_root=PSM_ROOT,
            ledger_path=ledger_path,
        )

    def test_project_status_route_reads_structured_local_evidence(self) -> None:
        result = self.execute("项目现在做到哪里？", intent="project_status")

        self.assertEqual(result["status"], "success")
        self.assertIn("local_project_status", [item["adapter"] for item in result["adapters"]])
        self.assertIn("source_or_tool_check", result["satisfied_judges"])
        self.assertFalse(result["external_release_authority"])
        self.assertTrue(result["provenance"][0]["sha256"])

    def test_verified_source_satisfies_source_check(self) -> None:
        pipeline = run_pipeline("请解释密封气体压力差。")
        result = execute_route(
            "请解释密封气体压力差。",
            intent="general",
            pipeline_result=pipeline,
            project_root=ROOT,
            psm_root=PSM_ROOT,
            verified_facts=("外压增加时，密封气体受压缩。",),
            verified_sources=("verified_kernel:sealed_gas_external_pressure",),
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("source_or_tool_check", result["satisfied_judges"])
        self.assertIn("verified_kernel:sealed_gas_external_pressure", result["sources"])

    def test_explicit_unknown_source_route_fails_without_fabricating_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "route_failures.jsonl"
            result = self.execute("请核验这个说法并给出来源：月球由奶酪组成。", ledger_path=ledger)

            self.assertEqual(result["status"], "not_executed")
            self.assertFalse(result["can_support_answer"])
            self.assertIn("source_or_tool_check", result["unresolved_judges"])
            self.assertEqual(result["failure_events"][0]["code"], "route_not_executed")
            self.assertTrue(ledger.exists())

    def test_file_route_reads_only_allowed_project_files(self) -> None:
        result = self.execute("请读取 `outputs/psm_v0/CURRENT_STATUS.md` 并说明版本。")

        self.assertEqual(result["status"], "success")
        self.assertIn("outputs/psm_v0/CURRENT_STATUS.md", result["sources"])
        self.assertTrue(result["provenance"][0]["read_only"])

    def test_file_route_blocks_path_outside_project_and_writes_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "route_failures.jsonl"
            result = self.execute("请读取 `/etc/hosts.txt`。", ledger_path=ledger)

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failures"][0]["code"], "path_outside_project")
            event = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(event["event_type"], "route_execution_failure")
            self.assertFalse(event["external_release_authority"])

    def test_python_snippet_is_parsed_without_execution(self) -> None:
        context = RouteContext(
            question="请检查：\n```python\nvalue = max([])\n```",
            intent="general",
            domain="code_engineering",
            route="retrieval_or_tool_check",
            allowed_statement_level="C2",
            required_judges=("source_or_tool_check",),
            project_root=ROOT,
            psm_root=PSM_ROOT,
        )
        result = CodeCheckAdapter().execute(context)

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["details"]["executed_user_code"])
        self.assertEqual(result["claims"]["code.python_syntax"], "passed")

    def test_allowlisted_project_check_timeout_is_not_hidden(self) -> None:
        context = RouteContext(
            question="请检查当前项目并运行测试。",
            intent="general",
            domain="code_engineering",
            route="retrieval_or_tool_check",
            allowed_statement_level="C2",
            required_judges=("source_or_tool_check",),
            project_root=ROOT,
            psm_root=PSM_ROOT,
            timeout_seconds=0.01,
        )
        with patch("psm_v0.route_executor._run_allowed_command", side_effect=__import__("subprocess").TimeoutExpired("verify", 0.01)):
            result = CodeCheckAdapter().execute(context)

        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["failures"][0]["code"], "tool_timeout")

    def test_conflicting_claims_fail_closed(self) -> None:
        context = RouteContext(
            question="status",
            intent="project_status",
            domain="general",
            route="retrieval_or_tool_check",
            allowed_statement_level="C2",
            required_judges=("source_or_tool_check",),
            project_root=ROOT,
            psm_root=PSM_ROOT,
        )
        results = [
            AdapterResult("a", "success", sources=["a"], claims={"project.current_version": "A"}),
            AdapterResult("b", "success", sources=["b"], claims={"project.current_version": "B"}),
        ]

        aggregate = aggregate_route_results(context, results)

        self.assertEqual(aggregate["status"], "conflict")
        self.assertFalse(aggregate["can_support_answer"])
        self.assertIn("project.current_version", aggregate["conflicts"])


if __name__ == "__main__":
    unittest.main()
