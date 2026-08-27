from __future__ import annotations

import pytest

from optees.application.usecases.solve_qp_usecase import SolveQPUseCase
from optees.data.adapters.qp.osqp_solver_adapter import OSQPSolverAdapter
from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.models.qp.qp_model import QPModel, QPOptions
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus


def test_osqp_solve_interior_optimum() -> None:
    # min 0.5 * (2 x1^2 + 2 x1 x2 + 2 x2^2) - 4 x1 - 6 x2
    # Analytical optimum: x* = (2/3, 8/3), f(x*) = -28/3
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(-4.0, -6.0),
        quadratic_matrix=((2.0, 1.0), (1.0, 2.0)),
        offset=0.0,
    )
    model = QPModel(variables=vars_, objective=obj)
    adapter = OSQPSolverAdapter()
    usecase = SolveQPUseCase(adapter)
    solution = usecase.execute(model)

    assert solution.status == QPSolveStatus.OPTIMAL
    assert solution.objective is not None
    assert pytest.approx(solution.objective, rel=1e-5) == -28.0 / 3.0
    assert pytest.approx(solution.values["x1"], rel=1e-5) == 2.0 / 3.0
    assert pytest.approx(solution.values["x2"], rel=1e-5) == 8.0 / 3.0
    assert solution.diagnostics.backend == "osqp"
    assert solution.diagnostics.backend_version is not None


def test_osqp_solve_boundary_optimum() -> None:
    # min 0.5 * (x1^2 + x2^2) s.t. x1 + x2 >= 2, x1 >= 0, x2 >= 0
    # Analytical optimum: x* = (1, 1), f(x*) = 1.0
    vars_ = (
        QPVariable(name="x1", bounds=Bounds(0.0, None)),
        QPVariable(name="x2", bounds=Bounds(0.0, None)),
    )
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, 0.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
        offset=0.0,
    )
    cons = (QPConstraint(name="c1", coefs=(1.0, 1.0), relation=Relation.GE, rhs=2.0),)
    model = QPModel(variables=vars_, objective=obj, constraints=cons)
    adapter = OSQPSolverAdapter()
    usecase = SolveQPUseCase(adapter)
    solution = usecase.execute(model)

    assert solution.status == QPSolveStatus.OPTIMAL
    assert solution.objective is not None
    assert pytest.approx(solution.objective, rel=1e-5) == 1.0
    assert pytest.approx(solution.values["x1"], rel=1e-5) == 1.0
    assert pytest.approx(solution.values["x2"], rel=1e-5) == 1.0
    assert solution.dual_values is not None
    assert len(solution.dual_values.constraints) == 1


def test_osqp_solve_concave_maximization() -> None:
    # max -(x1 - 2)^2 - (x2 - 3)^2 + 13 = -x1^2 - x2^2 + 4 x1 + 6 x2
    # Q = [[-2, 0], [0, -2]], c = [4, 6]
    # Analytical optimum: x* = (2, 3), f(x*) = 13.0
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MAX,
        linear_coefs=(4.0, 6.0),
        quadratic_matrix=((-2.0, 0.0), (0.0, -2.0)),
        offset=0.0,
    )
    model = QPModel(variables=vars_, objective=obj)
    adapter = OSQPSolverAdapter()
    usecase = SolveQPUseCase(adapter)
    solution = usecase.execute(model)

    assert solution.status == QPSolveStatus.OPTIMAL
    assert solution.objective is not None
    assert pytest.approx(solution.objective, rel=1e-5) == 13.0
    assert pytest.approx(solution.values["x1"], rel=1e-5) == 2.0
    assert pytest.approx(solution.values["x2"], rel=1e-5) == 3.0


def test_osqp_solve_infeasible() -> None:
    # x1 + x2 <= 1 and x1 + x2 >= 3, x >= 0
    vars_ = (
        QPVariable(name="x1", bounds=Bounds(0.0, None)),
        QPVariable(name="x2", bounds=Bounds(0.0, None)),
    )
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, 0.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
    )
    cons = (
        QPConstraint(name="c1", coefs=(1.0, 1.0), relation=Relation.LE, rhs=1.0),
        QPConstraint(name="c2", coefs=(1.0, 1.0), relation=Relation.GE, rhs=3.0),
    )
    model = QPModel(variables=vars_, objective=obj, constraints=cons)
    adapter = OSQPSolverAdapter()
    usecase = SolveQPUseCase(adapter)
    solution = usecase.execute(model)

    assert solution.status == QPSolveStatus.INFEASIBLE
    assert solution.objective is None
    assert solution.values == {}


def test_osqp_solve_unbounded() -> None:
    # min 0.5 * x1^2 - 2 * x2 s.t. x1 >= 0, x2 >= 0
    vars_ = (
        QPVariable(name="x1", bounds=Bounds(0.0, None)),
        QPVariable(name="x2", bounds=Bounds(0.0, None)),
    )
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, -2.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 0.0)),
    )
    model = QPModel(variables=vars_, objective=obj)
    adapter = OSQPSolverAdapter()
    usecase = SolveQPUseCase(adapter)
    solution = usecase.execute(model)

    assert solution.status == QPSolveStatus.UNBOUNDED
    assert solution.objective is None
    assert solution.values == {}


def test_osqp_warm_start() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(-4.0, -6.0),
        quadratic_matrix=((2.0, 1.0), (1.0, 2.0)),
    )
    options = QPOptions(warm_start=True, initial_primal=(0.66, 2.66))
    model = QPModel(variables=vars_, objective=obj, options=options)
    adapter = OSQPSolverAdapter()
    solution = SolveQPUseCase(adapter).execute(model)
    assert solution.status == QPSolveStatus.OPTIMAL
