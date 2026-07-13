from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.utility.regression_utils import solve_regression


REFERENCE_PATH = Path(__file__).parents[1] / "data" / "regression" / "reference_cases.json"


@pytest.mark.parametrize("case", json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))["cases"])
def test_analytic_reference_case(case: dict[str, object]) -> None:
    result = solve_regression(case["problem"])
    expected = case["expected"]

    assert result["status"] == "Trained"
    assert result["intercept"] == pytest.approx(expected["intercept"])
    for feature, coefficient in expected["coefficients"].items():
        assert result["coefficients"][feature] == pytest.approx(coefficient)
    assert result["test_metrics"]["rmse"] == pytest.approx(expected["test_rmse"])
    assert result["test_metrics"]["r_squared"] == pytest.approx(expected["test_r_squared"])
