from __future__ import annotations

import math
import pytest

from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.scenario.scenario_options import ScenarioOptions
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


def test_scenario_orientation_parsing() -> None:
    assert ScenarioOrientation.from_str("minimize_maximum_loss") == ScenarioOrientation.MIN_MAX_LOSS
    assert ScenarioOrientation.from_str("min_max_loss") == ScenarioOrientation.MIN_MAX_LOSS
    assert ScenarioOrientation.from_str("loss") == ScenarioOrientation.MIN_MAX_LOSS
    assert (
        ScenarioOrientation.from_str("maximize_minimum_reward")
        == ScenarioOrientation.MAX_MIN_REWARD
    )
    assert ScenarioOrientation.from_str("max_min_reward") == ScenarioOrientation.MAX_MIN_REWARD
    assert ScenarioOrientation.from_str("reward") == ScenarioOrientation.MAX_MIN_REWARD

    with pytest.raises(ValueError, match="Unsupported scenario orientation"):
        ScenarioOrientation.from_str("arbitrary_unknown")


def test_scenario_variable_creation_and_mutators() -> None:
    v1 = ScenarioVariable(name="x1", label="First item", bounds=Bounds(0.0, 10.0))
    assert v1.name == "x1"
    assert v1.label == "First item"
    assert v1.bounds.lb == 0.0
    assert v1.bounds.ub == 10.0
    assert v1.integrality == Integrality.CONTINUOUS

    # Binary auto bounds
    v_bin = ScenarioVariable(name="b1", integrality=Integrality.BINARY)
    assert v_bin.bounds.lb == 0.0
    assert v_bin.bounds.ub == 1.0

    # Mutators return new instances
    v2 = v1.rename("x1_renamed")
    assert v2.name == "x1_renamed"
    assert v1.name == "x1"

    v3 = v1.relabel("New label")
    assert v3.label == "New label"
    assert v1.label == "First item"

    v4 = v1.with_bounds(1.0, 5.0)
    assert v4.bounds.lb == 1.0
    assert v4.bounds.ub == 5.0

    v5 = v1.with_integrality(Integrality.INTEGER)
    assert v5.integrality == Integrality.INTEGER


def test_scenario_variable_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="must be a non-empty string"):
        ScenarioVariable(name="   ")


def test_scenario_entity_validation() -> None:
    scen = Scenario(id="s1", label="Regime 1", coefficients=(1.0, 2.0), offset=3.5)
    assert scen.id == "s1"
    assert scen.coefficients == (1.0, 2.0)
    assert scen.offset == 3.5

    # with_size pads or truncates
    scen_padded = scen.with_size(4)
    assert scen_padded.coefficients == (1.0, 2.0, 0.0, 0.0)

    scen_trunc = scen.with_size(1)
    assert scen_trunc.coefficients == (1.0,)

    with pytest.raises(ValueError, match="must be a non-empty string"):
        Scenario(id="")

    with pytest.raises(ValueError, match="finite number"):
        Scenario(id="s2", coefficients=(1.0, float("nan")))

    with pytest.raises(ValueError, match="finite number"):
        Scenario(id="s3", coefficients=(1.0, 2.0), offset=float("inf"))


def test_shared_objective_and_constraint_validation() -> None:
    sh_obj = ScenarioSharedObjective(coefficients=(0.5, -0.5), offset=1.0)
    assert sh_obj.coefficients == (0.5, -0.5)
    assert sh_obj.offset == 1.0

    con = ScenarioConstraint(name="c1", coefficients=(1.0, 1.0), relation=Relation.LE, rhs=10.0)
    assert con.name == "c1"
    assert con.relation == Relation.LE
    assert con.rhs == 10.0

    with pytest.raises(ValueError, match="finite number"):
        ScenarioSharedObjective(coefficients=(1.0, float("nan")))

    with pytest.raises(ValueError, match="finite number"):
        ScenarioConstraint(coefficients=(1.0, 2.0), rhs=float("inf"))


def test_scenario_options_validation() -> None:
    opts = ScenarioOptions(tolerance=1e-8, binding_tolerance=1e-7, time_limit_seconds=10.0)
    assert opts.tolerance == 1e-8
    assert opts.binding_tolerance == 1e-7
    assert opts.time_limit_seconds == 10.0

    with pytest.raises(ValueError, match="tolerance must be a finite positive number"):
        ScenarioOptions(tolerance=-1.0)

    with pytest.raises(ValueError, match="binding_tolerance must be a finite positive number"):
        ScenarioOptions(binding_tolerance=0.0)

    with pytest.raises(ValueError, match="time_limit_seconds must be a finite positive number"):
        ScenarioOptions(time_limit_seconds=-5.0)


def test_scenario_model_valid_creation_and_evaluations() -> None:
    vars_ = (
        ScenarioVariable(name="x1", bounds=Bounds(0.0, None)),
        ScenarioVariable(name="x2", bounds=Bounds(0.0, None)),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(2.0, -1.0), offset=5.0),
        Scenario(id="s2", coefficients=(-1.0, 3.0), offset=2.0),
        Scenario(id="s3", coefficients=(1.0, 1.0), offset=-4.0),
    )
    constraints = (
        ScenarioConstraint(name="budget", coefficients=(1.0, 1.0), relation=Relation.EQ, rhs=10.0),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )

    assert model.n_vars() == 2
    assert model.n_scenarios() == 3
    assert model.n_constraints() == 1
    assert not model.is_discrete()
    assert model.variable_names() == ("x1", "x2")
    assert model.scenario_ids() == ("s1", "s2", "s3")

    # Evaluate at x* = (37/7, 33/7)
    x_star = {"x1": 37.0 / 7.0, "x2": 33.0 / 7.0}
    assert math.isclose(model.evaluate_scenario(0, x_star), 76.0 / 7.0, abs_tol=1e-10)
    assert math.isclose(model.evaluate_scenario(1, x_star), 76.0 / 7.0, abs_tol=1e-10)
    assert math.isclose(model.evaluate_scenario(2, x_star), 6.0, abs_tol=1e-10)

    all_vals = model.evaluate_all_scenarios(x_star)
    assert len(all_vals) == 3
    assert math.isclose(model.evaluate_worst_case(x_star), 76.0 / 7.0, abs_tol=1e-10)

    binding = model.binding_scenario_ids(x_star, tolerance=1e-6)
    assert binding == ("s1", "s2")


def test_scenario_model_rejection_rules() -> None:
    v = ScenarioVariable(name="x1")
    s = Scenario(id="s1", coefficients=(1.0,))

    # Empty variables
    with pytest.raises(ValueError, match="at least one variable"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(),
            scenarios=(s,),
        )

    # Empty scenarios
    with pytest.raises(ValueError, match="at least one scenario"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(v,),
            scenarios=(),
        )

    # Duplicate variable names
    with pytest.raises(ValueError, match="Duplicate variable name"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(ScenarioVariable(name="x1"), ScenarioVariable(name="x1")),
            scenarios=(Scenario(id="s1", coefficients=(1.0, 2.0)),),
        )

    # Duplicate scenario IDs
    with pytest.raises(ValueError, match="Duplicate scenario ID"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(v,),
            scenarios=(
                Scenario(id="s1", coefficients=(1.0,)),
                Scenario(id="s1", coefficients=(2.0,)),
            ),
        )

    # Scenario coefficient dimension mismatch
    with pytest.raises(ValueError, match="coefficients, but model declares"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(v,),
            scenarios=(Scenario(id="s1", coefficients=(1.0, 2.0)),),
        )

    # Shared objective dimension mismatch
    with pytest.raises(ValueError, match="shared_objective has"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(v,),
            scenarios=(s,),
            shared_objective=ScenarioSharedObjective(coefficients=(1.0, 2.0)),
        )

    # Shared constraint dimension mismatch
    with pytest.raises(ValueError, match="shared_constraints\\[0\\] has"):
        ScenarioModel(
            orientation=ScenarioOrientation.MIN_MAX_LOSS,
            variables=(v,),
            scenarios=(s,),
            shared_constraints=(ScenarioConstraint(coefficients=(1.0, 2.0)),),
        )
