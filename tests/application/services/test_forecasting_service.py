from __future__ import annotations

from optees.application.contracts.capability_ids import FORECASTING_CAPABILITY_ID
from optees.application.contracts.errors import StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.contracts.solution_validation import (
    SolutionValidationStatus,
)
from optees.composition.local_agent import create_local_optimization_service


def _descriptor() -> dict:
    service = create_local_optimization_service()
    return next(
        item
        for item in service.list_capabilities()
        if item["id"] == FORECASTING_CAPABILITY_ID
    )


def test_forecasting_descriptor_exposes_complete_versioned_examples() -> None:
    descriptor = _descriptor()

    assert descriptor["problem_schema_version"] == "1"
    assert descriptor["result_schema_version"] == "1"
    assert descriptor["supports_cancellation"] is True
    assert descriptor["backend_candidates"] == [
        "internal.naive",
        "internal.seasonal_naive",
        "statsmodels.holt_winters_additive",
    ]
    assert descriptor["example_problem"]["observations"]
    assert descriptor["example_result"]["evaluation"]["folds"]


def test_forecasting_example_validates_and_solves_with_independent_checks() -> None:
    service = create_local_optimization_service()
    payload = _descriptor()["example_problem"]

    validation = service.validate(FORECASTING_CAPABILITY_ID, payload)
    assert not isinstance(validation, StructuredError)
    assert validation.available is True

    outcome = service.solve(FORECASTING_CAPABILITY_ID, payload)
    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result == _descriptor()["example_result"]
    assert outcome.result["forecast_available"] is True
    assert outcome.result["points"][-1]["predicted"] == 16.0
    assert outcome.validation is not None
    assert outcome.validation.status is SolutionValidationStatus.VERIFIED


def test_forecasting_rejects_unknown_fields_with_stable_context() -> None:
    service = create_local_optimization_service()
    payload = dict(_descriptor()["example_problem"])
    payload["future_actual"] = 20

    outcome = service.validate(FORECASTING_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.details[0].message.startswith("forecast.unknown_field")
