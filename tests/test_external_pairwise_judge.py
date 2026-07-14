from __future__ import annotations

import unittest

from psm_v0.external_pairwise_judge import (
    build_pairwise_package,
    build_pairwise_report,
    parse_pairwise_csv,
)


def answers(model: str) -> dict:
    return {
        "schema_version": "psm_independent_chat_answers_v1",
        "version": "PSM_V0.251",
        "generation_read_judge_labels": False,
        "rows": [
            {
                "id": f"case_{index:02d}",
                "split": "dev",
                "category": "casual",
                "answer": f"candidate answer {index}",
                "generation": {"model": model},
            }
            for index in range(1, 21)
        ],
    }


def prompts() -> dict:
    return {
        "cases": [
            {
                "id": f"case_{index:02d}",
                "split": "dev",
                "messages": [{"role": "user", "content": f"question {index}"}],
            }
            for index in range(1, 21)
        ]
    }


class ExternalPairwiseJudgeTest(unittest.TestCase):
    def test_public_package_is_anonymous_and_deterministic(self) -> None:
        public, mapping = build_pairwise_package(
            prompts(), answers("incumbent-model"), answers("challenger-model"), salt="fixed"
        )
        self.assertNotIn("incumbent-model", str(public))
        self.assertNotIn("challenger-model", str(public))
        self.assertEqual(len(public["rows"]), 20)
        self.assertEqual(len(mapping["rows"]), 20)
        rebuilt, _ = build_pairwise_package(
            prompts(), answers("incumbent-model"), answers("challenger-model"), salt="fixed"
        )
        self.assertEqual(public, rebuilt)

    def test_parser_requires_exact_rows(self) -> None:
        line = "J01,A,4,3,4,3,4,3,4,3,4,4,none,A is better"
        with self.assertRaises(ValueError):
            parse_pairwise_csv(line)

    def test_report_switches_only_for_material_safety_preserving_win(self) -> None:
        public, mapping = build_pairwise_package(
            prompts(), answers("incumbent-model"), answers("challenger-model"), salt="fixed"
        )
        lines = []
        for row in mapping["rows"]:
            winner = next(label for label in ("A", "B") if row[label] == "challenger")
            a_score = 4 if winner == "A" else 3
            b_score = 4 if winner == "B" else 3
            lines.append(
                f"{row['external_id']},{winner},{a_score},{b_score},{a_score},{b_score},"
                f"{a_score},{b_score},{a_score},{b_score},4,4,none,challenger is materially better"
            )
        report = build_pairwise_report(
            "\n".join(lines),
            public,
            mapping,
            {"user_authorized": True, "independent_from_candidates": True},
        )
        self.assertEqual(report["recommended_candidate"], "challenger")
        self.assertEqual(report["recommended_model"], "challenger-model")


if __name__ == "__main__":
    unittest.main()
