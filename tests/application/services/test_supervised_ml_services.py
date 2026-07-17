from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    CLASSIFICATION_BACKEND_ID,
    CLASSIFICATION_CAPABILITY_ID,
    REGRESSION_BACKEND_ID,
    REGRESSION_CAPABILITY_ID,
    create_classification_optimization_service,
    create_local_optimization_service,
    create_regression_optimization_service,
)


ROOT = Path(__file__).resolve().parents[3]


class RecordingSolver:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return self.response


def _regression_payload() -> dict:
    case = json.loads(
        (ROOT / "tests" / "data" / "regression" / "reference_cases.json").read_text()
    )["cases"][0]
    problem = case["problem"]
    return {
        "version": "1",
        "problem_type": "regression",
        "dataset": {
            "feature_names": problem["feature_names"],
            "target_name": problem["target_name"],
            "rows": [
                {"features": features, "target": target}
                for features, target in zip(
                    problem["feature_rows"], problem["target_values"], strict=True
                )
            ],
        },
        "training_options": {
            key: problem[key]
            for key in ("method", "test_fraction", "random_seed", "ridge_alpha")
        },
    }


def _classification_payload() -> dict:
    case = json.loads(
        (ROOT / "tests" / "data" / "classification" / "reference_cases.json").read_text()
    )["linearly_separable_2d"]
    return {
        "version": "1",
        "problem_type": "binary_classification",
        "dataset": {
            "feature_names": case["feature_names"],
            "target_name": case["target_name"],
            "rows": case["rows"],
        },
        "training_options": {
            "method": "LogisticRegression",
            **case["training_options"],
        },
    }


def test_regression_service_maps_public_dataset_through_solver_port():
    solver = RecordingSolver(
        {
            "status": "Trained",
            "intercept": 2,
            "coefficients": {"size": 3},
            "extras": {"method": "OLS"},
        }
    )
    service = create_regression_optimization_service(solver_port=solver)

    outcome = service.solve(REGRESSION_CAPABILITY_ID, _regression_payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "feasible"
    assert solver.problem["feature_names"] == ["size"]
    assert solver.problem["target_values"][:3] == [5.0, 8.0, 11.0]
    assert solver.problem["random_seed"] == 17
    assert outcome.diagnostics["backend_id"] == REGRESSION_BACKEND_ID


def test_classification_service_maps_public_dataset_through_solver_port():
    solver = RecordingSolver(
        {
            "status": "Trained",
            "negative_label": "no",
            "positive_label": "yes",
            "intercept": 0,
            "coefficients": {"x1": 1, "x2": 1},
        }
    )
    service = create_classification_optimization_service(solver_port=solver)

    outcome = service.solve(
        CLASSIFICATION_CAPABILITY_ID, _classification_payload()
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "feasible"
    assert solver.problem["target_values"] == ["no"] * 4 + ["yes"] * 4
    assert solver.problem["random_seed"] == 17
    assert outcome.diagnostics["backend_id"] == CLASSIFICATION_BACKEND_ID


@pytest.mark.parametrize(
    ("factory", "capability_id", "payload"),
    [
        (
            create_regression_optimization_service,
            REGRESSION_CAPABILITY_ID,
            _regression_payload(),
        ),
        (
            create_classification_optimization_service,
            CLASSIFICATION_CAPABILITY_ID,
            _classification_payload(),
        ),
    ],
)
def test_invalid_payload_is_rejected_before_solver_call(
    factory, capability_id, payload
):
    solver = RecordingSolver({"status": "Trained"})
    payload["dataset"]["rows"][0]["features"][0] = float("nan")

    outcome = factory(solver_port=solver).solve(capability_id, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.INVALID_REQUEST
    assert solver.problem is None


@pytest.mark.parametrize(
    ("factory", "capability_id", "payload"),
    [
        (
            create_regression_optimization_service,
            REGRESSION_CAPABILITY_ID,
            _regression_payload(),
        ),
        (
            create_classification_optimization_service,
            CLASSIFICATION_CAPABILITY_ID,
            _classification_payload(),
        ),
    ],
)
def test_unavailable_numpy_is_reported_before_solver_call(
    factory, capability_id, payload
):
    solver = RecordingSolver({"status": "Trained"})

    outcome = factory(
        solver_port=solver,
        dependency_available=False,
    ).solve(capability_id, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert solver.problem is None


def test_production_service_matches_regression_reference_case():
    outcome = create_local_optimization_service().solve(
        REGRESSION_CAPABILITY_ID, _regression_payload()
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["intercept"] == pytest.approx(2.0)
    assert outcome.result["coefficients"] == [
        {"feature": "size", "value": pytest.approx(3.0)}
    ]
    assert outcome.result["test_metrics"]["rmse"] == pytest.approx(0.0, abs=1e-10)


def test_production_service_matches_classification_reference_case():
    outcome = create_local_optimization_service().solve(
        CLASSIFICATION_CAPABILITY_ID, _classification_payload()
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["negative_label"] == "no"
    assert outcome.result["positive_label"] == "yes"
    assert outcome.result["train_metrics"]["accuracy"] == pytest.approx(1.0)
    assert outcome.result["test_metrics"]["accuracy"] == pytest.approx(1.0)
    assert [item["feature"] for item in outcome.result["feature_scaling"]] == [
        "x1",
        "x2",
    ]
    assert all(item["scale"] > 0 for item in outcome.result["feature_scaling"])


def test_registry_documents_both_supervised_ml_capabilities():
    descriptors = {
        item["id"]: item
        for item in create_local_optimization_service().list_capabilities()
    }

    assert descriptors[REGRESSION_CAPABILITY_ID]["backend_candidates"] == [
        REGRESSION_BACKEND_ID
    ]
    assert descriptors[CLASSIFICATION_CAPABILITY_ID]["backend_candidates"] == [
        CLASSIFICATION_BACKEND_ID
    ]
