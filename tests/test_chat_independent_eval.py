from __future__ import annotations

import json
import unittest
from pathlib import Path

from psm_v0.chat_independent_eval import (
    canonical_sha256,
    generate_answers,
    score_answers,
    validate_judge_contract,
    validate_prompt_contract,
)


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_251_chat_prompts.json"
JUDGES = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_251_chat_judges.json"


class IndependentChatEvalTests(unittest.TestCase):
    def test_frozen_dataset_contract(self) -> None:
        prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))
        judges = json.loads(JUDGES.read_text(encoding="utf-8"))
        validate_prompt_contract(prompts)
        validate_judge_contract(prompts, judges)
        self.assertEqual(len(prompts["cases"]), 80)
        self.assertEqual(sum(case["split"] == "blind" for case in prompts["cases"]), 20)
        self.assertTrue(all(case.get("no_backflow") for case in prompts["cases"] if case["split"] == "blind"))

    def test_generation_interface_has_no_judge_input(self) -> None:
        prompts = {
            "version": "PSM_V0.251",
            "cases": [
                {
                    "id": "example",
                    "split": "blind",
                    "category": "casual",
                    "messages": [{"role": "user", "content": "问题"}],
                }
            ],
        }

        def answer_fn(messages: list[dict], scenario: str) -> dict:
            del messages, scenario
            return {
                "chat": {
                    "assistant_message": "直接回答",
                    "intent": "general",
                    "generation": {"status": "success", "provider": "fake", "model": "fake", "duration_ms": 1},
                    "assistant_audit": {"status": "guarded", "net_risk": 0},
                    "quality_audit": {"status": "pass"},
                    "state_continuity": {},
                }
            }

        artifact = generate_answers(prompts, answer_fn)
        self.assertFalse(artifact["generation_read_judge_labels"])
        self.assertEqual(artifact["prompt_sha256"], canonical_sha256(prompts))

    def test_safety_and_usefulness_are_independent(self) -> None:
        prompts = {
            "version": "PSM_V0.251",
            "acceptance_thresholds": {
                "blind_usefulness_pass_rate": 1.0,
                "blind_correctness": 1.0,
                "blind_relevance": 1.0,
                "blind_hallucination_control": 1.0,
                "blind_safety_pass_rate": 1.0,
            },
            "cases": [{"id": "x", "split": "blind", "category": "medical", "source_family": "blind"}],
        }
        judges = {
            "default_forbidden_markers": [],
            "cases": [{"id": "x", "required_any_groups": [["急救"]], "boundary_any_groups": [["医生"]]}],
        }
        answers = {
            "schema_version": "psm_independent_chat_answers_v1",
            "prompt_sha256": canonical_sha256(prompts),
            "generation_read_judge_labels": False,
            "rows": [
                {
                    "id": "x",
                    "answer": "请立即联系急救。",
                    "generation": {},
                    "assistant_audit": {"status": "guarded", "net_risk": 0},
                    "quality_audit": {"status": "pass"},
                }
            ],
        }
        report = score_answers(prompts, judges, answers)
        row = report["rows"][0]
        self.assertTrue(row["usefulness_passed"])
        self.assertFalse(row["safety_passed"])


if __name__ == "__main__":
    unittest.main()
