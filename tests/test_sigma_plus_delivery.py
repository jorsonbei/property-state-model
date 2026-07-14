from __future__ import annotations

import unittest

from psm_v0.sigma_plus_delivery import (
    audit_statements,
    build_sigma_plus_delivery,
    calibrated_shadow_observation,
    repair_user_answer,
)
from psm_v0.shadow_state_encoder import TARGET_HEADS


def minimal_shadow_model() -> dict:
    return {
        "targets": {
            target: {
                "documents": 2,
                "classes": {
                    "accept": {"documents": 1, "total_tokens": 0, "token_counts": {}},
                    "review": {"documents": 1, "total_tokens": 0, "token_counts": {}},
                },
            }
            for target in TARGET_HEADS
        },
        "training_rows": 2,
        "alpha": 1.0,
        "vocabulary": [],
    }


def strict_calibration() -> dict:
    return {
        "temperatures": {target: 1.0 for target in TARGET_HEADS},
        "thresholds": {target: 0.9 for target in TARGET_HEADS},
    }


class SigmaPlusDeliveryTests(unittest.TestCase):
    def test_project_strong_claim_uses_structured_provenance(self) -> None:
        result = audit_statements(
            "当前版本是 PSM V0.258，评估覆盖率为 95.92%。",
            intent="project_results",
            grounding_facts=["PSM V0.258"],
            grounding_sources=["project_status_out/psm_v0.258_project_status.json"],
            route_execution={"allowed_statement_level": "C2", "sources": []},
        )
        self.assertEqual(result["unsupported_strong_claims"], 0)
        self.assertEqual(result["supported_strong_claims"], 1)

    def test_ungrounded_strong_claim_requires_downgrade_in_answer(self) -> None:
        downgraded = audit_statements(
            "没有原始证据，不能确认这项研究已经被证明。",
            intent="general",
            grounding_facts=[],
            grounding_sources=[],
            route_execution={"allowed_statement_level": "C1", "sources": []},
        )
        unsupported = audit_statements(
            "这项研究已经被正式证明。",
            intent="general",
            grounding_facts=[],
            grounding_sources=[],
            route_execution={"allowed_statement_level": "C1", "sources": []},
        )
        self.assertEqual(downgraded["downgraded_strong_claims"], 1)
        self.assertEqual(unsupported["unsupported_strong_claims"], 1)

        repaired = repair_user_answer("这项研究已经被正式证明。", unsupported, [])
        self.assertIn("不能确认", repaired)
        self.assertNotEqual(repaired, "这项研究已经被正式证明。")

    def test_calibrated_shadow_never_controls_output(self) -> None:
        model = minimal_shadow_model()
        calibration = strict_calibration()
        observation = calibrated_shadow_observation("普通问题", {"status": "not_executed", "sources": []}, model, calibration)
        self.assertEqual(set(observation["fallback_targets"]), set(TARGET_HEADS))
        self.assertEqual(observation["controller_used"], "deterministic_rule")
        self.assertFalse(observation["candidate_controlled_output"])

    def test_delivery_separates_user_and_developer_views(self) -> None:
        answer = "目前没有足够证据，不能确认该结论。"
        pipeline = {
            "packet": {
                "q_core": {}, "omega": {}, "phi_state": {}, "delta_sigma": {},
                "pi_cavity": {}, "eta": {}, "statement_level": "C1",
            },
            "bsigma_audit": {"status": "review"},
        }
        model = minimal_shadow_model()
        delivery = build_sigma_plus_delivery(
            request="结论成立吗？",
            answer=answer,
            intent="general",
            pipeline_result=pipeline,
            route_execution={"status": "not_executed", "sources": [], "external_release_authority": False},
            task_state_graph={"graph_id": "g1", "state_counts": {}, "next_protocol": {}},
            grounding_facts=[],
            grounding_sources=[],
            quality_audit={"status": "pass"},
            shadow_model=model,
            calibration=strict_calibration(),
        )
        self.assertTrue(delivery["passed"])
        self.assertEqual(delivery["user_view"], {"assistant_message": answer})
        self.assertNotIn("state_chain", delivery["user_view"])
        self.assertIn("state_chain", delivery["developer_view"])


if __name__ == "__main__":
    unittest.main()
