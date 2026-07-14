from __future__ import annotations

import unittest

from psm_v0.confidence_calibration import (
    apply_abstention,
    calibrated_prediction,
    expected_calibration_error,
    fit_abstention_threshold,
    fit_temperature,
    temperature_scale,
)


class ConfidenceCalibrationTests(unittest.TestCase):
    def test_temperature_scaling_preserves_class_order(self) -> None:
        original = {"low": 0.7, "critical": 0.3}
        scaled = temperature_scale(original, 2.0)
        self.assertGreater(scaled["low"], scaled["critical"])
        self.assertAlmostEqual(sum(scaled.values()), 1.0)
        self.assertLess(scaled["low"], original["low"])

    def test_temperature_fit_never_worsens_calibration_nll(self) -> None:
        samples = [
            ({"pass": 0.9, "veto": 0.1}, "pass"),
            ({"pass": 0.8, "veto": 0.2}, "pass"),
            ({"pass": 0.7, "veto": 0.3}, "veto"),
        ]
        result = fit_temperature(samples)
        self.assertLessEqual(result["nll_after"], result["nll_before"])
        self.assertGreaterEqual(result["samples"], 3)

    def test_abstention_threshold_removes_accepted_critical_false_negative(self) -> None:
        samples = [
            ("critical", "critical", 0.95),
            ("critical", "high", 0.55),
            ("medium", "medium", 0.8),
        ]
        result = fit_abstention_threshold(samples, target="omega", minimum_accuracy=0.8)
        self.assertGreater(result["threshold"], 0.55)
        self.assertEqual(result["critical_false_negatives"], 0)

    def test_apply_abstention_uses_confidence_only(self) -> None:
        prediction = {
            "labels": {"omega": "medium", "b_sigma": "review"},
            "confidence": {"omega": 0.51, "b_sigma": 0.9},
            "probabilities": {
                "omega": {"medium": 0.51, "critical": 0.49},
                "b_sigma": {"review": 0.9, "veto": 0.1},
            },
        }
        result = apply_abstention(prediction, {"omega": 0.6, "b_sigma": 0.6})
        self.assertIsNone(result["accepted_labels"]["omega"])
        self.assertEqual(result["accepted_labels"]["b_sigma"], "review")

    def test_threshold_prefers_stricter_floor_at_equal_coverage(self) -> None:
        samples = [
            ("medium", "medium", 0.72),
            ("critical", "critical", 0.91),
        ]
        result = fit_abstention_threshold(samples, target="omega", minimum_accuracy=0.8)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["threshold"], 0.72)

    def test_calibration_metrics_and_prediction_are_well_formed(self) -> None:
        raw = {
            "labels": {"omega": "critical"},
            "confidence": {"omega": 0.8},
            "probabilities": {"omega": {"critical": 0.8, "medium": 0.2}},
        }
        calibrated = calibrated_prediction(raw, {"omega": 2.0})
        self.assertEqual(calibrated["labels"]["omega"], "critical")
        self.assertLess(calibrated["confidence"]["omega"], 0.8)
        error = expected_calibration_error([({"critical": 0.8, "medium": 0.2}, "critical")])
        self.assertGreaterEqual(error, 0.0)


if __name__ == "__main__":
    unittest.main()
