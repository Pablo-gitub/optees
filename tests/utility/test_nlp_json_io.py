from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.domain.value_objects.nlp.objective_sense import NLPObjectiveSense
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.utility.nlp_json_io import (
    nlp_model_from_dict,
    nlp_model_from_file,
    nlp_model_to_dict,
    nlp_model_to_file,
)


ROSENBROCK = {
    "version": "1",
    "problem_type": "nonlinear_programming",
    "variables": [
        {"name": "x1", "label": "first", "lb": None, "ub": None, "initial": -1.2},
        {"name": "x2", "label": "second", "lb": None, "ub": None, "initial": 1.0},
    ],
    "objective": {
        "sense": "min",
        "expression": "(1 - x1)**2 + 100 * (x2 - x1**2)**2",
    },
    "solver_options": {
        "method": "Nelder-Mead",
        "max_iterations": 5000,
        "tolerance": 1e-8,
    },
}


def test_imports_nlp_json_through_the_domain_model() -> None:
    model = nlp_model_from_dict(ROSENBROCK)

    assert model.variable_names() == ("x1", "x2")
    assert model.initial_point() == (-1.2, 1.0)
    assert model.objective.sense is NLPObjectiveSense.MIN
    assert model.options.method is NLPSolverMethod.NELDER_MEAD
    assert model.evaluate_objective({"x1": 1.0, "x2": 1.0}) == pytest.approx(0.0)


def test_round_trip_preserves_bounds_expression_and_options() -> None:
    original = nlp_model_from_dict(
        {
            **ROSENBROCK,
            "variables": [
                {"name": "x1", "label": "bounded", "lb": 0, "ub": 2, "initial": 0.5}
            ],
            "objective": {"sense": "max", "expression": "10 - (x1 - 1)**2"},
            "solver_options": {"method": "L-BFGS-B", "max_iterations": 50, "tolerance": None},
        }
    )

    restored = nlp_model_from_dict(nlp_model_to_dict(original))

    assert restored == original
    assert nlp_model_to_dict(restored)["problem_type"] == "nonlinear_programming"


def test_file_round_trip(tmp_path: Path) -> None:
    model = nlp_model_from_dict(ROSENBROCK)
    path = tmp_path / "rosenbrock.json"

    nlp_model_to_file(model, path)
    restored = nlp_model_from_file(path)

    assert restored == model
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == "1"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({**ROSENBROCK, "version": "2"}, "version"),
        ({**ROSENBROCK, "problem_type": "lp"}, "problem_type"),
        ({**ROSENBROCK, "solver_options": {"method": "SLSQP"}}, "method"),
        (
            {
                **ROSENBROCK,
                "variables": [
                    {"name": "x1", "lb": 0, "ub": 1, "initial": 2}
                ],
                "objective": {"sense": "min", "expression": "x1**2"},
                "solver_options": {"method": "L-BFGS-B"},
            },
            "initial",
        ),
        (
            {
                **ROSENBROCK,
                "variables": [
                    {"name": "x1", "initial": 0}
                ],
                "objective": {"sense": "min", "expression": "__import__('os')"},
            },
            "unsupported function",
        ),
    ],
)
def test_rejects_invalid_nlp_json(data: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        nlp_model_from_dict(data)


def test_rejects_invalid_json_file(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid NLP JSON"):
        nlp_model_from_file(path)
