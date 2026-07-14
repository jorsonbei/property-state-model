from __future__ import annotations

import unittest

from psm_v0.shadow_state_encoder import (
    TARGET_HEADS,
    annotation_target_heads,
    build_training_rows,
    fit_naive_bayes,
    predict_naive_bayes,
    request_features,
    transparent_rule_prediction,
)


def consensus(labels: dict[str, dict]) -> dict:
    return {
        target: {"status": "resolved", "resolved_value": value}
        for target, value in labels.items()
    }


def target_values(kind: str) -> dict:
    options = {
        "casual": ("proceed_bounded", "low", [], [], [], [], [], [], "pass"),
        "critical": (
            "veto_and_escalate",
            "critical",
            ["synthetic fact"],
            ["professional outcome"],
            ["urgent harm"],
            ["deadline"],
            ["external_judge"],
            ["tail event"],
            "veto",
        ),
    }
    objective, risk, facts, unknowns, pressures, missing, dependencies, tail, status = options[kind]
    return {
        "q_core": {"objective": objective},
        "omega": {"risk_level": risk},
        "phi": {"facts": facts, "unknowns": unknowns},
        "delta_sigma": {"pressures": pressures, "missing_pressure_data": missing},
        "pi": {"dependencies": dependencies},
        "eta": {"uncertainties": unknowns, "tail_events": tail},
        "b_sigma": {"status": status},
    }


def record(record_id: str, request: str, kind: str, split: str = "train") -> dict:
    return {
        "record_id": record_id,
        "split": split,
        "training_eligible": True,
        "source": {
            "source_family": "must_not_be_feature",
            "source_id": "must_not_be_feature",
            "source_created_at": "2099-01-01T00:00:00Z",
        },
        "input": {"request": request, "evidence": [{"status": "available"}]},
        "consensus": consensus(target_values(kind)),
    }


class ShadowStateEncoderTests(unittest.TestCase):
    def test_feature_encoder_excludes_source_split_and_target_fields(self) -> None:
        item = record("r1", "医疗症状需要医生判断", "critical")
        encoded = request_features(item)
        text = " ".join(encoded)
        self.assertNotIn("must_not_be_feature", text)
        self.assertNotIn("2099", text)
        self.assertNotIn("critical", text)

    def test_training_loader_only_reads_eligible_train_rows(self) -> None:
        train = record("train", "医疗症状", "critical")
        validation = record("validation", "法院传票", "critical", split="validation")
        unresolved = record("unresolved", "普通问题", "casual")
        unresolved["consensus"]["omega"] = {"status": "unresolved", "resolved_value": None}
        rows = build_training_rows([train, validation, unresolved])
        self.assertEqual([row["record_id"] for row in rows], ["train"])

    def test_trainable_model_learns_distinct_state_heads(self) -> None:
        records = [
            record("casual_1", "请帮我整理一个日常清单", "casual"),
            record("casual_2", "写一句普通问候", "casual"),
            record("critical_1", "医疗症状和用药需要医生判断", "critical"),
            record("critical_2", "法院传票需要律师处理", "critical"),
        ]
        model = fit_naive_bayes(build_training_rows(records))
        prediction = predict_naive_bayes(model, record("probe", "医疗用药请医生判断", "critical"))
        self.assertEqual(set(prediction["labels"]), set(TARGET_HEADS))
        self.assertEqual(prediction["labels"]["omega"], "critical")
        self.assertEqual(prediction["labels"]["b_sigma"], "veto")
        self.assertTrue(model["boundary"]["shadow_only"])
        self.assertFalse(model["feature_policy"]["source_identity"])

    def test_unseen_probe_tokens_do_not_distort_known_evidence(self) -> None:
        records = [
            record("casual", "普通问候", "casual"),
            record("critical", "医疗药物需要医生判断", "critical"),
        ]
        model = fit_naive_bayes(build_training_rows(records))
        probe = record("probe", "医疗药物需要医生判断外加训练词表从未出现的冗长新描述", "critical")
        prediction = predict_naive_bayes(model, probe)
        self.assertEqual(prediction["labels"]["omega"], "critical")
        self.assertEqual(prediction["labels"]["b_sigma"], "veto")

    def test_transparent_rule_retains_critical_professional_boundary(self) -> None:
        prediction = transparent_rule_prediction(record("probe", "法院传票应该怎么办", "critical"))
        self.assertEqual(prediction["labels"]["omega"], "critical")
        self.assertEqual(prediction["labels"]["pi"], "external_judge")
        self.assertEqual(prediction["labels"]["b_sigma"], "veto")

    def test_target_projection_preserves_all_seven_heads(self) -> None:
        labels = annotation_target_heads(consensus(target_values("critical")))
        self.assertEqual(set(labels), set(TARGET_HEADS))
        self.assertEqual(labels["phi"], "partial")
        self.assertEqual(labels["delta_sigma"], "pressured")
        self.assertEqual(labels["eta"], "tail_risk")


if __name__ == "__main__":
    unittest.main()
