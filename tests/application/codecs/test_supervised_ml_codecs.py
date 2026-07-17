from __future__ import annotations

import json

import pytest

from optees.application.codecs.classification_problem_codec import (
    classification_model_from_public_dict,
)
from optees.application.codecs.classification_result_codec import (
    ClassificationResultCodec,
)
from optees.application.codecs.regression_problem_codec import (
    regression_model_from_public_dict,
)
from optees.application.codecs.regression_result_codec import RegressionResultCodec
from optees.domain.entities.classification.solution import ClassificationSolution
from optees.domain.entities.regression.solution import RegressionSolution


def _regression_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "regression",
        "dataset": {
            "feature_names": ["size"],
            "target_name": "price",
            "rows": [
                {"features": [value], "target": 2 + 3 * value}
                for value in range(1, 9)
            ],
        },
        "training_options": {
            "method": "OLS",
            "test_fraction": 0.25,
            "random_seed": 17,
            "ridge_alpha": 1,
        },
    }


def _classification_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "binary_classification",
        "dataset": {
            "feature_names": ["score"],
            "target_name": "approved",
            "rows": [
                {"features": [0], "target": "no"},
                {"features": [1], "target": "no"},
                {"features": [2], "target": "no"},
                {"features": [3], "target": "no"},
                {"features": [7], "target": "yes"},
                {"features": [8], "target": "yes"},
                {"features": [9], "target": "yes"},
                {"features": [10], "target": "yes"},
            ],
        },
        "training_options": {
            "method": "LogisticRegression",
            "test_fraction": 0.25,
            "random_seed": 17,
            "learning_rate": 0.1,
            "max_iterations": 2000,
            "l2_alpha": 0,
        },
    }


def test_problem_codecs_preserve_datasets_and_reproducible_options():
    regression = regression_model_from_public_dict(_regression_payload())
    classification = classification_model_from_public_dict(
        _classification_payload()
    )

    assert regression.dataset.feature_names == ("size",)
    assert regression.dataset.target_values[0] == pytest.approx(5.0)
    assert regression.options.random_seed == 17
    assert classification.dataset.labels == ("no", "yes")
    assert classification.options.random_seed == 17
    assert classification.options.max_iterations == 2000


@pytest.mark.parametrize(
    ("parser", "payload"),
    [
        (regression_model_from_public_dict, _regression_payload()),
        (classification_model_from_public_dict, _classification_payload()),
    ],
)
def test_problem_codecs_require_explicit_dataset(parser, payload):
    del payload["dataset"]

    with pytest.raises(ValueError, match="missing required fields: dataset"):
        parser(payload)


def test_problem_codecs_reject_non_finite_features_and_non_binary_targets():
    regression = _regression_payload()
    regression["dataset"]["rows"][0]["features"][0] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        regression_model_from_public_dict(regression)

    classification = _classification_payload()
    classification["dataset"]["rows"][0]["target"] = "maybe"
    with pytest.raises(ValueError, match="exactly two target labels"):
        classification_model_from_public_dict(classification)


def test_regression_result_codec_exposes_metrics_and_predictions():
    solution = RegressionSolution.from_solver_result(
        {
            "status": "Trained",
            "intercept": 2,
            "coefficients": {"size": 3},
            "train_metrics": {"mae": 0, "mse": 0, "rmse": 0, "r_squared": 1},
            "test_metrics": {"mae": 0, "mse": 0, "rmse": 0, "r_squared": 1},
            "predictions": [
                {
                    "row_index": 0,
                    "actual": 5,
                    "predicted": 5,
                    "residual": 0,
                    "partition": "train",
                }
            ],
            "extras": {"method": "OLS", "train_count": 6, "test_count": 2},
        }
    )

    serialized = RegressionResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "feasible"
    assert serialized.result["trained_model"] is True
    assert serialized.result["coefficients"] == [
        {"feature": "size", "value": 3.0}
    ]
    assert serialized.result["test_metrics"]["r_squared"] == pytest.approx(1.0)
    assert "do not establish causality" in serialized.warnings[0]
    json.dumps(serialized.result, allow_nan=False)


def test_classification_result_codec_exposes_metrics_confusion_and_probabilities():
    solution = ClassificationSolution.from_solver_result(
        {
            "status": "Trained",
            "negative_label": "no",
            "positive_label": "yes",
            "intercept": 0,
            "coefficients": {"score": 2},
            "train_metrics": {"accuracy": 1, "precision": 1, "recall": 1, "f1": 1},
            "test_metrics": {"accuracy": 1, "precision": 1, "recall": 1, "f1": 1},
            "train_confusion": {
                "true_negative": 3,
                "false_positive": 0,
                "false_negative": 0,
                "true_positive": 3,
            },
            "test_confusion": {
                "true_negative": 1,
                "false_positive": 0,
                "false_negative": 0,
                "true_positive": 1,
            },
            "predictions": [
                {
                    "row_index": 0,
                    "actual": "no",
                    "predicted": "no",
                    "probability_positive": 0.1,
                    "partition": "test",
                }
            ],
            "extras": {
                "converged": False,
                "iterations": 2000,
                "feature_means": {"score": 5},
                "feature_scales": {"score": 2},
            },
        }
    )

    serialized = ClassificationResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "feasible"
    assert serialized.result["positive_label"] == "yes"
    assert serialized.result["test_confusion"]["true_positive"] == 1
    assert serialized.result["predictions"][0]["probability_positive"] == pytest.approx(0.1)
    assert serialized.result["feature_scaling"] == [
        {"feature": "score", "mean": 5.0, "scale": 2.0}
    ]
    assert serialized.result["decision_threshold"] == pytest.approx(0.5)
    assert len(serialized.warnings) == 2
    json.dumps(serialized.result, allow_nan=False)


@pytest.mark.parametrize(
    ("codec", "solution"),
    [
        (
            RegressionResultCodec(),
            RegressionSolution.from_solver_result({"status": "Failed"}),
        ),
        (
            ClassificationResultCodec(),
            ClassificationSolution.from_solver_result({"status": "Failed"}),
        ),
    ],
)
def test_failed_training_maps_to_not_solved(codec, solution):
    serialized = codec.serialize(solution)

    assert serialized.mathematical_status.value == "not_solved"
    assert serialized.result["trained_model"] is False
