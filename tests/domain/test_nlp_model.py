from __future__ import annotations

import pytest

from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.models.nlp.nlp_model import NLPModel, NLPOptions
from optees.domain.value_objects.nlp.objective_sense import NLPObjectiveSense
from optees.domain.value_objects.nlp.solve_status import NLPSolveStatus
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.utility.nlp_expression import NLPExpressionSyntaxError


def test_constructs_an_unbounded_model_and_evaluates_its_objective() -> None:
    model = NLPModel.from_parts(
        variables=[
            NLPVariable("x1", initial_value=-1.2),
            NLPVariable("x2", initial_value=1.0),
        ],
        objective=NLPObjective(
            "(1 - x1)**2 + 100 * (x2 - x1**2)**2",
            NLPObjectiveSense.MIN,
        ),
        options=NLPOptions(method=NLPSolverMethod.BFGS),
    )

    assert model.variable_names() == ("x1", "x2")
    assert model.initial_point() == (-1.2, 1.0)
    assert model.bounds() == ((None, None), (None, None))
    assert model.evaluate_objective({"x1": 1.0, "x2": 1.0}) == pytest.approx(0.0)


def test_bounded_model_requires_a_bound_aware_method() -> None:
    variable = NLPVariable("x1", lower_bound=0.0, upper_bound=2.0, initial_value=0.5)

    with pytest.raises(ValueError, match="does not support box bounds"):
        NLPModel.from_parts(
            variables=[variable],
            objective=NLPObjective("(x1 - 2)**2"),
            options=NLPOptions(method=NLPSolverMethod.BFGS),
        )

    model = NLPModel.from_parts(
        variables=[variable],
        objective=NLPObjective("(x1 - 2)**2"),
        options=NLPOptions(method=NLPSolverMethod.L_BFGS_B),
    )
    assert model.has_bounds()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "1x", "initial_value": 0.0},
        {"name": "sin", "initial_value": 0.0},
        {"name": "x1", "lower_bound": 3.0, "upper_bound": 2.0, "initial_value": 2.0},
        {"name": "x1", "lower_bound": 0.0, "initial_value": -1.0},
        {"name": "x1", "upper_bound": 0.0, "initial_value": 1.0},
    ],
)
def test_variable_rejects_invalid_name_bounds_or_initial_point(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        NLPVariable(**kwargs)


def test_model_rejects_unknown_expression_variable_and_duplicate_variables() -> None:
    with pytest.raises(NLPExpressionSyntaxError, match="unknown variable"):
        NLPModel.from_parts(
            variables=[NLPVariable("x1")],
            objective=NLPObjective("x1 + x2"),
        )

    with pytest.raises(ValueError, match="unique"):
        NLPModel.from_parts(
            variables=[NLPVariable("x1"), NLPVariable("x1")],
            objective=NLPObjective("x1**2"),
        )


@pytest.mark.parametrize("value", [0, -1, 1.5, float("inf"), True])
def test_options_reject_invalid_iteration_limits(value: object) -> None:
    with pytest.raises(ValueError):
        NLPOptions(max_iterations=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0.0, -1e-8, float("inf"), True, "invalid"])
def test_options_reject_invalid_tolerances(value: object) -> None:
    with pytest.raises(ValueError):
        NLPOptions(tolerance=value)  # type: ignore[arg-type]


def test_options_accept_a_positive_tolerance_or_none() -> None:
    assert NLPOptions(tolerance=1e-8).tolerance == 1e-8
    assert NLPOptions(tolerance=None).tolerance is None


def test_solution_preserves_only_finite_numerical_diagnostics() -> None:
    solution = NLPSolution.from_solver_result(
        status="Converged",
        objective=3.0,
        values={"x1": 1.5, "x2": float("nan")},
        extras={
            "iterations": 4,
            "evaluations": 7,
            "message": "gradient tolerance reached",
            "convergence_history": [5.0, float("inf"), 3.0],
        },
    )

    assert solution.status is NLPSolveStatus.CONVERGED
    assert solution.values == {"x1": 1.5}
    assert solution.iterations == 4
    assert solution.evaluations == 7
    assert solution.convergence_history == (5.0, 3.0)
    assert solution.converged()
