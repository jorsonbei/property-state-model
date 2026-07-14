from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.external_semantic_judge import build_external_report, parse_external_csv


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"


class ExternalSemanticJudgeTests(unittest.TestCase):
    def test_checked_in_external_judge_evidence_is_reproducible(self) -> None:
        raw_csv = (PSM_ROOT / "runtime" / "v0_251_external_judge_gemini_pro.csv").read_text(
            encoding="utf-8"
        )
        answers = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_external_judge_input_answers.json").read_text(
                encoding="utf-8"
            )
        )
        prompts = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_251_chat_prompts.json").read_text(encoding="utf-8")
        )
        provenance = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_external_judge_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        report = build_external_report(raw_csv, answers, prompts, provenance)
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["pass_count"], 13)
        self.assertEqual(report["summary"]["fail_count"], 7)
        self.assertEqual(report["summary"]["usefulness_pass_rate"], 0.65)
        self.assertEqual(report["summary"]["dimensions"]["correctness"], 0.8125)
        self.assertEqual(report["summary"]["dimensions"]["relevance"], 0.9625)
        self.assertEqual(report["summary"]["dimensions"]["hallucination_control"], 0.8)
        self.assertEqual(report["summary"]["safety_pass_rate"], 1.0)
        self.assertEqual(report["summary"]["critical_safety_failures"], 0)

    def test_wave_d_cross_provider_judgment_is_reproducible(self) -> None:
        raw_csv = (
            PSM_ROOT / "runtime" / "v0_251_wave_d_external_judge_chatgpt_instant.csv"
        ).read_text(encoding="utf-8")
        answers = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_wave_d_external_judge_input_answers.json").read_text(
                encoding="utf-8"
            )
        )
        prompts = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_251_chat_prompts_wave_d.json").read_text(
                encoding="utf-8"
            )
        )
        provenance = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_wave_d_external_judge_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        report = build_external_report(raw_csv, answers, prompts, provenance)
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["pass_count"], 12)
        self.assertEqual(report["summary"]["usefulness_pass_rate"], 0.6)
        self.assertEqual(report["summary"]["dimensions"]["correctness"], 0.675)
        self.assertEqual(report["summary"]["dimensions"]["relevance"], 0.975)
        self.assertEqual(report["summary"]["dimensions"]["boundary_quality"], 0.8)
        self.assertEqual(report["summary"]["dimensions"]["hallucination_control"], 0.7125)
        self.assertEqual(report["summary"]["safety_pass_rate"], 1.0)
        self.assertTrue(provenance["independent_from_blind_author"])

    def test_wave_e_cross_provider_judgment_is_reproducible(self) -> None:
        raw_csv = (
            PSM_ROOT / "runtime" / "v0_251_wave_e_external_judge_gemini_pro.csv"
        ).read_text(encoding="utf-8")
        answers = json.loads(
            (
                PSM_ROOT
                / "runtime"
                / "v0_251_wave_e_external_judge_input_answers.json"
            ).read_text(encoding="utf-8")
        )
        prompts = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_251_chat_prompts_wave_e.json").read_text(
                encoding="utf-8"
            )
        )
        provenance = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_wave_e_external_judge_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        report = build_external_report(raw_csv, answers, prompts, provenance)
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["pass_count"], 15)
        self.assertEqual(report["summary"]["usefulness_pass_rate"], 0.75)
        self.assertEqual(report["summary"]["dimensions"]["correctness"], 0.8375)
        self.assertEqual(report["summary"]["dimensions"]["relevance"], 0.9375)
        self.assertEqual(report["summary"]["dimensions"]["hallucination_control"], 0.9)
        self.assertEqual(report["summary"]["safety_pass_rate"], 1.0)
        self.assertTrue(provenance["independent_from_blind_author"])

    def test_wave_f_cross_provider_judgment_is_reproducible(self) -> None:
        raw_csv = (
            PSM_ROOT / "runtime" / "v0_251_wave_f_external_judge_chatgpt_instant.csv"
        ).read_text(encoding="utf-8")
        answers = json.loads(
            (
                PSM_ROOT
                / "runtime"
                / "v0_251_wave_f_external_judge_input_answers.json"
            ).read_text(encoding="utf-8")
        )
        prompts = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_251_chat_prompts_wave_f.json").read_text(
                encoding="utf-8"
            )
        )
        provenance = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_wave_f_external_judge_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        report = build_external_report(raw_csv, answers, prompts, provenance)
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["pass_count"], 12)
        self.assertEqual(report["summary"]["usefulness_pass_rate"], 0.6)
        self.assertEqual(report["summary"]["dimensions"]["correctness"], 0.775)
        self.assertEqual(report["summary"]["dimensions"]["relevance"], 1.0)
        self.assertEqual(report["summary"]["dimensions"]["hallucination_control"], 0.8125)
        self.assertEqual(report["summary"]["safety_pass_rate"], 1.0)
        self.assertTrue(provenance["independent_from_blind_author"])

    def test_wave_g_cross_provider_judgment_is_reproducible(self) -> None:
        raw_csv = (
            PSM_ROOT / "runtime" / "v0_251_wave_g_external_judge_gemini_pro.csv"
        ).read_text(encoding="utf-8")
        answers = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_wave_g_answers.json").read_text(
                encoding="utf-8"
            )
        )
        prompts = json.loads(
            (PSM_ROOT / "benchmarks" / "v0_251_chat_prompts_wave_g.json").read_text(
                encoding="utf-8"
            )
        )
        provenance = json.loads(
            (PSM_ROOT / "runtime" / "v0_251_wave_g_external_judge_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        report = build_external_report(raw_csv, answers, prompts, provenance)
        self.assertTrue(report["passed"])
        self.assertEqual(report["summary"]["pass_count"], 20)
        self.assertEqual(report["summary"]["usefulness_pass_rate"], 1.0)
        self.assertEqual(report["summary"]["dimensions"]["correctness"], 1.0)
        self.assertEqual(report["summary"]["dimensions"]["relevance"], 1.0)
        self.assertEqual(report["summary"]["dimensions"]["hallucination_control"], 1.0)
        self.assertEqual(report["summary"]["safety_pass_rate"], 1.0)
        self.assertEqual(report["summary"]["critical_safety_failures"], 0)
        self.assertTrue(provenance["independent_from_blind_author"])

    def test_parser_rejects_verdict_that_contradicts_rubric(self) -> None:
        rows = [
            f"J{index:02d},4,4,4,4,4,4,pass,false,ok"
            for index in range(1, 21)
        ]
        rows[0] = "J01,2,4,4,4,4,4,pass,false,wrong"
        with self.assertRaisesRegex(ValueError, "contradicts"):
            parse_external_csv("\n".join(rows))


if __name__ == "__main__":
    unittest.main()
