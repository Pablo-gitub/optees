from __future__ import annotations

from optees.application.services.scenario_reduction_service import (
    ScenarioReductionService,
    reduce_scenario_model,
)
from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.scenario.scenario_options import ScenarioOptions
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


def test_example1_min_max_loss_lp_reduction() -> None:
    """Verify exact epigraph reduction of Example 1 to LPModel."""
    vars_ = (
        ScenarioVariable(name="x1", label="Resource 1", bounds=Bounds(0.0, None)),
        ScenarioVariable(name="x2", label="Resource 2", bounds=Bounds(0.0, None)),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(2.0, -1.0), offset=5.0),
        Scenario(id="s2", coefficients=(-1.0, 3.0), offset=2.0),
        Scenario(id="s3", coefficients=(1.0, 1.0), offset=-4.0),
    )
    constraints = (
        ScenarioConstraint(name="budget", coefficients=(1.0, 1.0), relation=Relation.EQ, rhs=10.0),
    )
    scenario_model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )

    result = ScenarioReductionService.reduce(scenario_model)
    assert not result.is_discrete
    assert result.orientation == ScenarioOrientation.MIN_MAX_LOSS
    assert result.auxiliary_variable_name == "_aux_theta"
    assert result.auxiliary_variable_index == 2

    lp_model = result.model
    assert isinstance(lp_model, LPModel)

    # 1. Variables check: n + 1 = 3 variables
    assert lp_model.n_vars() == 3
    assert lp_model.variables[0].name == "x1"
    assert lp_model.variables[0].label == "Resource 1"
    assert lp_model.variables[0].bounds.lb == 0.0
    assert lp_model.variables[0].bounds.ub is None

    assert lp_model.variables[1].name == "x2"
    assert lp_model.variables[1].label == "Resource 2"
    assert lp_model.variables[1].bounds.lb == 0.0
    assert lp_model.variables[1].bounds.ub is None

    assert lp_model.variables[2].name == "_aux_theta"
    assert lp_model.variables[2].bounds.lb is None
    assert lp_model.variables[2].bounds.ub is None

    # 2. Objective check: min 0*x1 + 0*x2 + 1*_aux_theta
    assert lp_model.objective.sense == ObjectiveSense.MIN
    assert lp_model.objective.coefs == (0.0, 0.0, 1.0)
    assert lp_model.objective.offset == 0.0

    # 3. Constraints check: 1 shared + 3 scenario = 4 constraints
    assert lp_model.n_constraints() == 4

    # Shared constraint: x1 + x2 + 0*_aux_theta = 10.0
    assert lp_model.constraints[0].coefs == (1.0, 1.0, 0.0)
    assert lp_model.constraints[0].relation == Relation.EQ
    assert lp_model.constraints[0].rhs == 10.0

    # Scenario 1 constraint: 2*x1 - 1*x2 - 1*_aux_theta <= -5.0
    assert lp_model.constraints[1].coefs == (2.0, -1.0, -1.0)
    assert lp_model.constraints[1].relation == Relation.LE
    assert lp_model.constraints[1].rhs == -5.0

    # Scenario 2 constraint: -1*x1 + 3*x2 - 1*_aux_theta <= -2.0
    assert lp_model.constraints[2].coefs == (-1.0, 3.0, -1.0)
    assert lp_model.constraints[2].relation == Relation.LE
    assert lp_model.constraints[2].rhs == -2.0

    # Scenario 3 constraint: 1*x1 + 1*x2 - 1*_aux_theta <= 4.0
    assert lp_model.constraints[3].coefs == (1.0, 1.0, -1.0)
    assert lp_model.constraints[3].relation == Relation.LE
    assert lp_model.constraints[3].rhs == 4.0


def test_example2_max_min_reward_lp_reduction() -> None:
    """Verify exact hypograph reduction of Example 2 (negative values) to LPModel."""
    vars_ = (
        ScenarioVariable(name="x1", bounds=Bounds(0.0, 4.0)),
        ScenarioVariable(name="x2", bounds=Bounds(0.0, 4.0)),
    )
    scenarios = (
        Scenario(id="sA", coefficients=(4.0, -2.0), offset=-10.0),
        Scenario(id="sB", coefficients=(-2.0, 5.0), offset=-8.0),
        Scenario(id="sC", coefficients=(1.0, 1.0), offset=-5.0),
    )
    constraints = (
        ScenarioConstraint(name="budget", coefficients=(1.0, 1.0), relation=Relation.LE, rhs=6.0),
    )
    scenario_model = ScenarioModel(
        orientation=ScenarioOrientation.MAX_MIN_REWARD,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
    )

    lp_model = reduce_scenario_model(scenario_model)
    assert isinstance(lp_model, LPModel)

    # Variables check
    assert lp_model.n_vars() == 3
    assert lp_model.variables[0].name == "x1"
    assert lp_model.variables[1].name == "x2"
    assert lp_model.variables[2].name == "_aux_tau"
    assert lp_model.variables[2].bounds.lb is None
    assert lp_model.variables[2].bounds.ub is None

    # Objective check: max 0*x1 + 0*x2 + 1*_aux_tau
    assert lp_model.objective.sense == ObjectiveSense.MAX
    assert lp_model.objective.coefs == (0.0, 0.0, 1.0)
    assert lp_model.objective.offset == 0.0

    # Constraints check: 1 shared + 3 scenario = 4 constraints
    assert lp_model.n_constraints() == 4

    # Shared constraint: x1 + x2 + 0*_aux_tau <= 6.0
    assert lp_model.constraints[0].coefs == (1.0, 1.0, 0.0)
    assert lp_model.constraints[0].relation == Relation.LE
    assert lp_model.constraints[0].rhs == 6.0

    # Scenario A constraint: -4*x1 + 2*x2 + 1*_aux_tau <= -10.0
    assert lp_model.constraints[1].coefs == (-4.0, 2.0, 1.0)
    assert lp_model.constraints[1].relation == Relation.LE
    assert lp_model.constraints[1].rhs == -10.0

    # Scenario B constraint: 2*x1 - 5*x2 + 1*_aux_tau <= -8.0
    assert lp_model.constraints[2].coefs == (2.0, -5.0, 1.0)
    assert lp_model.constraints[2].relation == Relation.LE
    assert lp_model.constraints[2].rhs == -8.0

    # Scenario C constraint: -1*x1 - 1*x2 + 1*_aux_tau <= -5.0
    assert lp_model.constraints[3].coefs == (-1.0, -1.0, 1.0)
    assert lp_model.constraints[3].relation == Relation.LE
    assert lp_model.constraints[3].rhs == -5.0


def test_example3_discrete_binary_milp_reduction() -> None:
    """Verify exact reduction of Example 3 (binary selection) to MILPModel."""
    vars_ = (
        ScenarioVariable(name="x1", integrality=Integrality.BINARY),
        ScenarioVariable(name="x2", integrality=Integrality.BINARY),
        ScenarioVariable(name="x3", integrality=Integrality.BINARY),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(10.0, 2.0, 8.0), offset=0.0),
        Scenario(id="s2", coefficients=(3.0, 12.0, 4.0), offset=0.0),
        Scenario(id="s3", coefficients=(6.0, 5.0, 9.0), offset=0.0),
    )
    constraints = (
        ScenarioConstraint(
            name="cardinality", coefficients=(1.0, 1.0, 1.0), relation=Relation.EQ, rhs=2.0
        ),
    )
    scenario_model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_constraints=constraints,
        options=ScenarioOptions(time_limit_seconds=15.0),
    )

    result = ScenarioReductionService.reduce(scenario_model)
    assert result.is_discrete
    assert result.auxiliary_variable_name == "_aux_theta"

    milp_model = result.model
    assert isinstance(milp_model, MILPModel)
    assert milp_model.time_limit == 15.0

    # 1. Variables check: binary variables retain BINARY domain and bounds [0, 1]
    assert milp_model.n_vars() == 4
    for i in range(3):
        assert milp_model.variables[i].integrality == Integrality.BINARY
        assert milp_model.variables[i].bounds.lb == 0.0
        assert milp_model.variables[i].bounds.ub == 1.0

    # Auxiliary variable must be CONTINUOUS and unbounded
    aux_var = milp_model.variables[3]
    assert aux_var.name == "_aux_theta"
    assert aux_var.integrality == Integrality.CONTINUOUS
    assert aux_var.bounds.lb is None
    assert aux_var.bounds.ub is None

    # 2. Objective check
    assert milp_model.objective.sense == ObjectiveSense.MIN
    assert milp_model.objective.coefs == (0.0, 0.0, 0.0, 1.0)
    assert milp_model.objective.offset == 0.0

    # 3. Constraints check
    assert milp_model.n_constraints() == 4
    # Shared constraint
    assert milp_model.constraints[0].coefs == (1.0, 1.0, 1.0, 0.0)
    assert milp_model.constraints[0].relation == Relation.EQ
    assert milp_model.constraints[0].rhs == 2.0

    # Scenario constraints
    assert milp_model.constraints[1].coefs == (10.0, 2.0, 8.0, -1.0)
    assert milp_model.constraints[1].relation == Relation.LE
    assert milp_model.constraints[1].rhs == 0.0

    assert milp_model.constraints[2].coefs == (3.0, 12.0, 4.0, -1.0)
    assert milp_model.constraints[2].relation == Relation.LE
    assert milp_model.constraints[2].rhs == 0.0

    assert milp_model.constraints[3].coefs == (6.0, 5.0, 9.0, -1.0)
    assert milp_model.constraints[3].relation == Relation.LE
    assert milp_model.constraints[3].rhs == 0.0


def test_auxiliary_variable_name_collision_handling() -> None:
    """Verify deterministic collision avoidance for auxiliary variable names without renaming user variables."""
    vars_ = (
        ScenarioVariable(name="_aux_theta", bounds=Bounds(0.0, 1.0)),
        ScenarioVariable(name="_aux_theta_1", bounds=Bounds(0.0, 1.0)),
    )
    scenarios = (Scenario(id="s1", coefficients=(1.0, 2.0), offset=3.0),)
    scenario_model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
    )

    result = ScenarioReductionService.reduce(scenario_model)
    # The auxiliary name should increment to _aux_theta_2
    assert result.auxiliary_variable_name == "_aux_theta_2"
    assert result.auxiliary_variable_index == 2

    # User variables are not renamed
    assert result.model.variables[0].name == "_aux_theta"
    assert result.model.variables[1].name == "_aux_theta_1"
    assert result.model.variables[2].name == "_aux_theta_2"


def test_shared_objective_and_offset_combination() -> None:
    """Verify that non-zero base coefficients and base offset combine correctly into scenario constraints."""
    vars_ = (
        ScenarioVariable(name="x1"),
        ScenarioVariable(name="x2"),
    )
    base_obj = ScenarioSharedObjective(coefficients=(10.0, 20.0), offset=100.0)
    scenarios = (Scenario(id="s1", coefficients=(1.0, 2.0), offset=5.0),)
    scenario_model = ScenarioModel(
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        variables=vars_,
        scenarios=scenarios,
        shared_objective=base_obj,
    )

    result = ScenarioReductionService.reduce(scenario_model)
    lp = result.model
    # Combined: d = (11, 22), delta = 105
    # Epigraph constraint: 11*x1 + 22*x2 - theta <= -105
    assert lp.constraints[0].coefs == (11.0, 22.0, -1.0)
    assert lp.constraints[0].relation == Relation.LE
    assert lp.constraints[0].rhs == -105.0


def test_reduction_idempotence_and_input_immutability() -> None:
    """Verify that reduction is pure, does not mutate inputs, and produces consistent models on repeated calls."""
    vars_ = (
        ScenarioVariable(name="x1", bounds=Bounds(0.0, 5.0)),
        ScenarioVariable(name="x2", bounds=Bounds(1.0, 4.0)),
    )
    scenarios = (
        Scenario(id="s1", coefficients=(2.0, 3.0), offset=1.0),
        Scenario(id="s2", coefficients=(-1.0, 4.0), offset=-2.0),
    )
    model = ScenarioModel(
        orientation=ScenarioOrientation.MAX_MIN_REWARD,
        variables=vars_,
        scenarios=scenarios,
    )

    res1 = ScenarioReductionService.reduce(model)
    res2 = ScenarioReductionService.reduce(model)

    assert res1.auxiliary_variable_name == res2.auxiliary_variable_name
    assert res1.model.objective.coefs == res2.model.objective.coefs
    assert len(res1.model.constraints) == len(res2.model.constraints)

    # Input model is completely unchanged
    assert model.variables[0].name == "x1"
    assert model.variables[0].bounds.lb == 0.0
    assert model.scenarios[0].coefficients == (2.0, 3.0)
