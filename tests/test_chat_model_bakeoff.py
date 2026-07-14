from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.chat_model_bakeoff import (
    chinese_ratio,
    contains_any,
    eligible_fallback_model,
    summarize_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_250_chat_model_bakeoff.json"


class ChatModelBakeoffTests(unittest.TestCase):
    def test_benchmark_is_frozen_and_covers_required_domains(self) -> None:
        benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        ids = {case["id"] for case in benchmark["cases"]}
        self.assertEqual(benchmark["version"], "PSM_V0.250")
        self.assertTrue(benchmark["blind_scoring"])
        self.assertEqual(len(ids), 10)
        self.assertIn("medical_emergency_helpful_boundary", ids)
        self.assertIn("assistant_history_stage_reference", ids)

    def test_marker_and_language_scoring_are_model_independent(self) -> None:
        self.assertTrue(contains_any("成熟香蕉通常更甜", ["香蕉", "banana"]))
        self.assertAlmostEqual(chinese_ratio("这是中文回答 with detail"), 0.375)

    def test_summary_reports_latency_and_failure_separately(self) -> None:
        rows = [
            {
                "score": 1.0,
                "quality_status": "pass",
                "expected_coverage": 1.0,
                "boundary_coverage": 1.0,
                "transport_status": "success",
                "duration_ms": 1000,
                "reasoning_leak_removed": False,
                "answer": "可见回答",
            },
            {
                "score": 0.2,
                "quality_status": "fail",
                "expected_coverage": 0.0,
                "boundary_coverage": 0.0,
                "transport_status": "timeout",
                "duration_ms": 6000,
                "reasoning_leak_removed": True,
                "answer": "",
            },
        ]
        summary = summarize_candidate(rows, latency_target_ms=5000)
        self.assertEqual(summary["failure_rate"], 0.5)
        self.assertEqual(summary["median_latency_ms"], 3500)
        self.assertTrue(summary["median_latency_target_passed"])
        self.assertEqual(summary["reasoning_leak_rows"], 1)
        self.assertEqual(summary["empty_visible_answers"], 1)

    def test_slow_reasoning_model_is_not_selected_as_fallback(self) -> None:
        summaries = {
            "candidate_b": {
                "failure_rate": 0.0,
                "median_latency_target_passed": False,
                "reasoning_leak_rows": 10,
            }
        }
        fallback = eligible_fallback_model(
            ["candidate_b"], summaries, {"candidate_b": "reasoning:8b"}
        )
        self.assertIsNone(fallback)


if __name__ == "__main__":
    unittest.main()
