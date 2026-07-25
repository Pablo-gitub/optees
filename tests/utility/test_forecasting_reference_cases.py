from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.capability_ids import FORECASTING_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import create_local_optimization_service


REFERENCE_CASES = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "forecasting"
    / "reference_cases.json"
)


def _cases() -> list[dict[str, object]]:
    return json.loads(REFERENCE_CASES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["id"]))
def test_forecasting_reference_case(case: dict[str, object]) -> None:
    service = create_local_optimization_service()
    outcome = service.solve(FORECASTING_CAPABILITY_ID, case["problem"])

    assert isinstance(outcome, ExecutionEnvelope)
    expected = case["expected"]
    assert isinstance(expected, dict)
    assert outcome.result["evaluation"]["status"] == expected["evaluation_status"]
    assert outcome.validation is not None
    assert outcome.validation.status.value == expected["validation_status"]

    future_values = [
        point["predicted"]
        for point in outcome.result["points"]
        if point["segment"] == "future"
    ]
    assert future_values == pytest.approx(expected["future_values"])

    metrics = outcome.result["metrics"]
    expected_metrics = expected["metrics"]
    assert isinstance(metrics, dict)
    assert isinstance(expected_metrics, dict)
    for name, expected_value in expected_metrics.items():
        if expected_value is None:
            assert metrics[name] is None
        else:
            assert metrics[name] == pytest.approx(expected_value)


def test_forecasting_reference_fixture_contains_required_edge_cases() -> None:
    assert {case["id"] for case in _cases()} == {
        "constant_series",
        "linear_trend_naive_baseline",
        "seasonal_cycle",
        "short_history",
        "zero_actual_in_holdout",
        "noisy_deterministic",
    }
