from __future__ import annotations

import math
from typing import Iterable


DEFAULT_TEMPERATURE_GRID = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0)


def temperature_scale(probabilities: dict[str, float], temperature: float) -> dict[str, float]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    powered = {label: max(probability, 1e-12) ** (1.0 / temperature) for label, probability in probabilities.items()}
    total = sum(powered.values())
    return {label: value / total for label, value in powered.items()}


def negative_log_likelihood(samples: Iterable[tuple[dict[str, float], str]], temperature: float = 1.0) -> float:
    values = list(samples)
    if not values:
        return 0.0
    total = 0.0
    for probabilities, truth in values:
        calibrated = temperature_scale(probabilities, temperature)
        total -= math.log(max(calibrated.get(truth, 0.0), 1e-12))
    return total / len(values)


def fit_temperature(
    samples: Iterable[tuple[dict[str, float], str]],
    grid: Iterable[float] = DEFAULT_TEMPERATURE_GRID,
) -> dict:
    values = list(samples)
    scores = [
        {"temperature": float(temperature), "nll": negative_log_likelihood(values, float(temperature))}
        for temperature in grid
    ]
    selected = sorted(scores, key=lambda item: (item["nll"], abs(item["temperature"] - 1.0)))[0]
    return {
        "temperature": selected["temperature"],
        "nll_before": round(negative_log_likelihood(values, 1.0), 8),
        "nll_after": round(selected["nll"], 8),
        "samples": len(values),
        "grid": [{"temperature": item["temperature"], "nll": round(item["nll"], 8)} for item in scores],
    }


def expected_calibration_error(
    samples: Iterable[tuple[dict[str, float], str]],
    temperature: float = 1.0,
    bins: int = 5,
) -> float:
    values = list(samples)
    if not values:
        return 0.0
    buckets = [[] for _ in range(bins)]
    for probabilities, truth in values:
        calibrated = temperature_scale(probabilities, temperature)
        label, confidence = sorted(calibrated.items(), key=lambda item: (-item[1], item[0]))[0]
        index = min(bins - 1, int(confidence * bins))
        buckets[index].append((confidence, label == truth))
    error = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        mean_confidence = sum(item[0] for item in bucket) / len(bucket)
        accuracy = sum(item[1] for item in bucket) / len(bucket)
        error += len(bucket) / len(values) * abs(mean_confidence - accuracy)
    return round(error, 8)


def calibrated_prediction(prediction: dict, temperatures: dict[str, float]) -> dict:
    labels: dict[str, str] = {}
    confidence: dict[str, float] = {}
    probabilities: dict[str, dict[str, float]] = {}
    for target, values in prediction["probabilities"].items():
        calibrated = temperature_scale(values, temperatures.get(target, 1.0))
        label, score = sorted(calibrated.items(), key=lambda item: (-item[1], item[0]))[0]
        labels[target] = label
        confidence[target] = round(score, 8)
        probabilities[target] = {key: round(value, 8) for key, value in sorted(calibrated.items())}
    return {"labels": labels, "confidence": confidence, "probabilities": probabilities}


def critical_false_negative(target: str, truth: str, prediction: str) -> bool:
    if target == "omega":
        return truth == "critical" and prediction != "critical"
    if target == "b_sigma":
        return truth == "veto" and prediction != "veto"
    return False


def fit_abstention_threshold(
    samples: Iterable[tuple[str, str, float]],
    *,
    target: str,
    minimum_accuracy: float = 0.8,
) -> dict:
    values = list(samples)
    candidates = sorted({0.0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, *(confidence for _, _, confidence in values)})
    eligible: list[dict] = []
    for threshold in candidates:
        accepted = [sample for sample in values if sample[2] >= threshold]
        if not accepted:
            continue
        correct = sum(truth == prediction for truth, prediction, _ in accepted)
        false_negatives = sum(
            critical_false_negative(target, truth, prediction)
            for truth, prediction, _ in accepted
        )
        accuracy = correct / len(accepted)
        coverage = len(accepted) / len(values) if values else 0.0
        if accuracy >= minimum_accuracy and false_negatives == 0:
            eligible.append(
                {
                    "threshold": float(threshold),
                    "accuracy": accuracy,
                    "coverage": coverage,
                    "accepted": len(accepted),
                    "critical_false_negatives": false_negatives,
                }
            )
    if not eligible:
        return {
            "threshold": 1.0,
            "accuracy": None,
            "coverage": 0.0,
            "accepted": 0,
            "critical_false_negatives": 0,
        }
    # At equal coverage, retain the strictest floor supported by calibration data.
    selected = sorted(eligible, key=lambda item: (-item["coverage"], -item["threshold"]))[0]
    return {
        **selected,
        "accuracy": round(selected["accuracy"], 8),
        "coverage": round(selected["coverage"], 8),
    }


def apply_abstention(prediction: dict, thresholds: dict[str, float]) -> dict:
    labels: dict[str, str | None] = {}
    abstained: dict[str, bool] = {}
    for target, label in prediction["labels"].items():
        abstain = prediction["confidence"][target] < thresholds.get(target, 0.0)
        labels[target] = None if abstain else label
        abstained[target] = abstain
    return {
        **prediction,
        "accepted_labels": labels,
        "abstained": abstained,
    }
