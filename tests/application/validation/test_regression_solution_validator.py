from __future__ import annotations

from copy import deepcopy

from optees.application.codecs.regression_result_codec import RegressionResultCodec
from optees.application.contracts.solution_validation import SolutionValidationStatus
from optees.application.usecases.train_regression_usecase import TrainRegressionUseCase
from optees.application.validation.regression_solution_validator import (
    RegressionIndependentSolutionValidator,
)
from optees.data.adapters.regression.numpy_regression_adapter import (
    NumpyRegressionAdapter,
)
from optees.utility.regression_json_io import regression_model_from_dict


def _model():
    return regression_model_from_dict(
        {
            "version": "1",
            "problem_type": "regression",
            "dataset": {
                "feature_names": ["x"],
                "target_name": "y",
                "rows": [
                    {"features": [0], "target": 2},
                    {"features": [1], "target": 5},
                    {"features": [2], "target": 8},
                    {"features": [3], "target": 11},
                    {"features": [4], "target": 14},
                    {"features": [5], "target": 17},
                ],
            },
            "training_options": {
                "method": "OLS",
                "test_fraction": 0.34,
                "random_seed": 7,
                "ridge_alpha": 1,
            },
        }
    )


def _serialized():
    solution = TrainRegressionUseCase(NumpyRegressionAdapter()).execute(_model())
    return RegressionResultCodec().serialize(solution)


def _violation_codes(report) -> set[str]:
    return {violation.code for violation in report.violations}


def test_consistent_regression_result_is_verified_independently():
    report = RegressionIndependentSolutionValidator()(_model(), _serialized())

    assert report.status is SolutionValidationStatus.VERIFIED
    assert [check.code for check in report.checks] == [
        "regression.parameters",
        "regression.predictions",
        "regression.split",
        "regression.metrics",
    ]
    assert report.limitations


def test_parameter_or_prediction_tampering_fails_validation():
    serialized = _serialized()
    changed = deepcopy(serialized.result)
    changed["predictions"][0]["predicted"] += 1
    tampered = type(serialized)(
        mathematical_status=serialized.mathematical_status,
        result=changed,
        diagnostics=serialized.diagnostics,
        warnings=serialized.warnings,
    )

    report = RegressionIndependentSolutionValidator()(_model(), tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert _violation_codes(report) == {"invalid_regression_predictions"}


def test_metric_tampering_fails_validation():
    serialized = _serialized()
    changed = deepcopy(serialized.result)
    changed["test_metrics"]["rmse"] = 10
    tampered = type(serialized)(
        mathematical_status=serialized.mathematical_status,
        result=changed,
        diagnostics=serialized.diagnostics,
        warnings=serialized.warnings,
    )

    report = RegressionIndependentSolutionValidator()(_model(), tampered)

    assert report.status is SolutionValidationStatus.FAILED
    assert _violation_codes(report) == {"regression_metric_mismatch"}
