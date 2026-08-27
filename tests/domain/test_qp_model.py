from __future__ import annotations

import pytest

from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.models.qp.qp_model import QPModel, QPOptions
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


def test_qp_model_valid_construction() -> None:
    vars_ = (
        QPVariable(name="x1", label="X1", bounds=Bounds(0.0, 10.0)),
        QPVariable(name="x2", label="X2", bounds=Bounds(None, None)),
    )
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(-4.0, -6.0),
        quadratic_matrix=((2.0, 1.0), (1.0, 2.0)),
        offset=1.5,
    )
    cons = (
        QPConstraint(name="c1", coefs=(1.0, 1.0), relation=Relation.LE, rhs=5.0),
    )
    options = QPOptions(method="osqp", tolerance=1e-6, max_iterations=2000, time_limit_seconds=30.0)

    model = QPModel(variables=vars_, objective=obj, constraints=cons, options=options)
    assert model.n_vars() == 2
    assert model.n_constraints() == 1
    assert model.variable_names() == ("x1", "x2")
    assert model.objective.offset == 1.5


def test_qp_model_rejects_duplicate_variable_names() -> None:
    vars_ = (
        QPVariable(name="x1"),
        QPVariable(name="x1"),
    )
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(1.0, 1.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
    )
    with pytest.raises(ValueError, match="variable names must be unique"):
        QPModel(variables=vars_, objective=obj)


def test_qp_model_rejects_dimension_mismatch() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(1.0, 2.0, 3.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
    )
    with pytest.raises(ValueError, match="linear coefficients length"):
        QPModel(variables=vars_, objective=obj)


def test_qp_model_rejects_asymmetry_beyond_tolerance() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, 0.0),
        quadratic_matrix=((2.0, 3.0), (1.0, 2.0)),
    )
    with pytest.raises(ValueError, match="asymmetric"):
        QPModel(variables=vars_, objective=obj)


def test_qp_model_canonicalizes_near_symmetric_matrix() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, 0.0),
        quadratic_matrix=((2.0, 1.0 + 1e-10), (1.0 - 1e-10, 2.0)),
    )
    model = QPModel(variables=vars_, objective=obj)
    Q = model.objective.quadratic_matrix
    assert Q[0][1] == Q[1][0] == 1.0


def test_qp_model_rejects_non_psd_matrix_for_min() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(0.0, 0.0),
        quadratic_matrix=((1.0, 2.0), (2.0, 1.0)),
    )
    with pytest.raises(ValueError, match="not positive semi-definite"):
        QPModel(variables=vars_, objective=obj)


def test_qp_model_accepts_concave_max_and_rejects_non_concave() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    # Negative definite: acceptable for max
    obj_concave = QPObjective(
        sense=ObjectiveSense.MAX,
        linear_coefs=(4.0, 6.0),
        quadratic_matrix=((-2.0, 0.0), (0.0, -2.0)),
    )
    model = QPModel(variables=vars_, objective=obj_concave)
    assert model.objective.sense == ObjectiveSense.MAX

    # Positive definite: rejected for max
    obj_convex = QPObjective(
        sense=ObjectiveSense.MAX,
        linear_coefs=(4.0, 6.0),
        quadratic_matrix=((2.0, 0.0), (0.0, 2.0)),
    )
    with pytest.raises(ValueError, match="not negative semi-definite"):
        QPModel(variables=vars_, objective=obj_convex)


def test_qp_model_rejects_non_finite_values() -> None:
    vars_ = (QPVariable(name="x1"), QPVariable(name="x2"))
    obj = QPObjective(
        sense=ObjectiveSense.MIN,
        linear_coefs=(float("nan"), 0.0),
        quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
    )
    with pytest.raises(ValueError, match="non-finite"):
        QPModel(variables=vars_, objective=obj)


def test_qp_options_validation() -> None:
    with pytest.raises(ValueError, match="unsupported QP method"):
        QPOptions(method="clarabel")  # v1 supports osqp only in domain options

    with pytest.raises(ValueError, match="max_iterations"):
        QPOptions(max_iterations=-5)

    with pytest.raises(ValueError, match="tolerance"):
        QPOptions(tolerance=-1e-5)
