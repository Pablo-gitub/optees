from __future__ import annotations

import pytest

from optees.utility.nlp_utils import solve_nlp


def test_solves_a_convex_unbounded_quadratic_with_bfgs() -> None:
    status, objective, values, extras = solve_nlp(
        {
            "sense": "min",
            "expression": "(x1 - 2)**2 + (x2 + 1)**2",
            "variables": ["x1", "x2"],
            "initial_point": [0.0, 0.0],
            "bounds": [(None, None), (None, None)],
            "method": "BFGS",
            "max_iterations": 200,
            "tolerance": 1e-9,
        }
    )

    assert status == "Converged"
    assert objective == pytest.approx(0.0, abs=1e-10)
    assert values["x1"] == pytest.approx(2.0, abs=1e-6)
    assert values["x2"] == pytest.approx(-1.0, abs=1e-6)
    assert extras["method"] == "BFGS"
    assert extras["convergence_history"]


def test_solves_a_bounded_minimum_at_the_boundary_with_lbfgsb() -> None:
    status, objective, values, _ = solve_nlp(
        {
            "sense": "min",
            "expression": "(x1 - 5)**2",
            "variables": ["x1"],
            "initial_point": [0.0],
            "bounds": [(0.0, 2.0)],
            "method": "L-BFGS-B",
            "max_iterations": 100,
            "tolerance": 1e-10,
        }
    )

    assert status == "Converged"
    assert objective == pytest.approx(9.0, abs=1e-8)
    assert values == {"x1": pytest.approx(2.0, abs=1e-6)}


def test_restores_the_original_maximization_objective_value() -> None:
    status, objective, values, _ = solve_nlp(
        {
            "sense": "max",
            "expression": "10 - (x1 - 3)**2",
            "variables": ["x1"],
            "initial_point": [0.0],
            "bounds": None,
            "method": "BFGS",
            "max_iterations": 100,
            "tolerance": 1e-9,
        }
    )

    assert status == "Converged"
    assert objective == pytest.approx(10.0, abs=1e-8)
    assert values["x1"] == pytest.approx(3.0, abs=1e-6)


def test_rejects_bound_incompatible_method_before_calling_scipy() -> None:
    with pytest.raises(ValueError, match="does not support box bounds"):
        solve_nlp(
            {
                "sense": "min",
                "expression": "x1**2",
                "variables": ["x1"],
                "initial_point": [0.0],
                "bounds": [(0.0, None)],
                "method": "BFGS",
            }
        )


def test_reports_a_non_finite_initial_objective_as_failed() -> None:
    status, objective, values, extras = solve_nlp(
        {
            "sense": "min",
            "expression": "log(x1)",
            "variables": ["x1"],
            "initial_point": [-1.0],
            "bounds": None,
            "method": "BFGS",
        }
    )

    assert status == "Failed"
    assert objective is None
    assert values == {}
    assert extras["success"] is False


def test_reports_iteration_limit_with_the_best_candidate() -> None:
    status, objective, values, extras = solve_nlp(
        {
            "sense": "min",
            "expression": "(1 - x1)**2 + 100 * (x2 - x1**2)**2",
            "variables": ["x1", "x2"],
            "initial_point": [-1.2, 1.0],
            "bounds": None,
            "method": "BFGS",
            "max_iterations": 1,
            "tolerance": 1e-12,
        }
    )

    assert status == "IterationLimit"
    assert objective is not None
    assert set(values) == {"x1", "x2"}
    assert extras["iterations"] == 1
