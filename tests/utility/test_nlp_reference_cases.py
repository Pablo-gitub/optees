from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.utility.nlp_utils import solve_nlp


_REFERENCE_CASES_PATH = Path(__file__).parents[1] / "data" / "nlp" / "reference_cases.json"


@pytest.mark.parametrize("case", json.loads(_REFERENCE_CASES_PATH.read_text())["cases"], ids=lambda case: case["id"])
def test_analytic_nlp_reference_case(case: dict[str, object]) -> None:
    status, objective, values, extras = solve_nlp(case["problem"])  # type: ignore[arg-type]
    expected = case["expected"]  # type: ignore[assignment]
    tolerance = expected["absolute_tolerance"]  # type: ignore[index]

    assert case["kind"] == "analytic_reference_case"
    assert status == expected["status"]  # type: ignore[index]
    assert objective == pytest.approx(expected["objective"], abs=tolerance)  # type: ignore[index]
    for variable, expected_value in expected["values"].items():  # type: ignore[index,union-attr]
        assert values[variable] == pytest.approx(expected_value, abs=tolerance)
    assert extras["convergence_history"]
