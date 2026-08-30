from __future__ import annotations

import pytest

from optees.application.codecs.scenario_problem_codec import (
    scenario_max_min_reward_model_from_public_dict,
    scenario_min_max_loss_model_from_public_dict,
)
from optees.application.codecs.scenario_result_codec import ScenarioResultCodec
from optees.application.contracts.errors import CodedValidationError
from optees.application.contracts.execution import (
    MathematicalStatus,
    TerminationReason,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.scenario.scenario_value import ScenarioValue
from optees.domain.models.scenario.scenario_result import (
    ScenarioResult,
    ScenarioSolveStatus,
)
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.lp.solver_diagnostics import SolverDiagnostics
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


def _valid_loss_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "minimize_maximum_loss",
        "variables": [
            {
                "name": "x1",
                "label": "First",
                "lower_bound": 0.0,
                "upper_bound": 10.0,
                "integrality": "C",
            },
            {
                "name": "x2",
                "label": "Second",
                "lower_bound": 0.0,
                "upper_bound": None,
                "integrality": "C",
            },
        ],
        "shared_objective": {
            "coefficients": [1.0, 2.0],
            "offset": 3.0,
        },
        "scenarios": [
            {
                "id": "s1",
                "label": "Scenario 1",
                "coefficients": [2.0, -1.0],
                "offset": 5.0,
            },
            {
                "id": "s2",
                "label": "Scenario 2",
                "coefficients": [-1.0, 3.0],
                "offset": 2.0,
            },
        ],
        "shared_constraints": [
            {
                "name": "budget",
                "coefficients": [1.0, 1.0],
                "relation": "<=",
                "rhs": 10.0,
            }
        ],
        "options": {
            "tolerance": 1e-6,
            "binding_tolerance": 1e-5,
            "time_limit_seconds": 30.0,
        },
    }


def _valid_reward_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "maximize_minimum_reward",
        "variables": [
            {"name": "y1", "lower_bound": 0.0, "upper_bound": 5.0},
            {"name": "y2", "lower_bound": 0.0, "upper_bound": 5.0},
        ],
        "scenarios": [
            {"id": "sA", "coefficients": [4.0, -2.0], "offset": -10.0},
            {"id": "sB", "coefficients": [-2.0, 5.0], "offset": -8.0},
        ],
        "shared_constraints": [{"coefficients": [1.0, 1.0], "relation": ">=", "rhs": 2.0}],
    }


def test_problem_codec_valid_loss_payload() -> None:
    payload = _valid_loss_payload()
    model = scenario_min_max_loss_model_from_public_dict(payload)

    assert model.orientation is ScenarioOrientation.MIN_MAX_LOSS
    assert len(model.variables) == 2
    assert model.variables[0].name == "x1"
    assert model.variables[0].bounds.lb == 0.0
    assert model.variables[0].bounds.ub == 10.0
    assert model.variables[0].integrality is Integrality.CONTINUOUS
    assert model.variables[1].bounds.ub is None

    assert model.shared_objective is not None
    assert model.shared_objective.coefficients == (1.0, 2.0)
    assert model.shared_objective.offset == 3.0

    assert len(model.scenarios) == 2
    assert model.scenarios[0].id == "s1"
    assert model.scenarios[0].coefficients == (2.0, -1.0)
    assert model.scenarios[0].offset == 5.0

    assert len(model.shared_constraints) == 1
    assert model.shared_constraints[0].name == "budget"
    assert model.shared_constraints[0].relation is Relation.LE
    assert model.shared_constraints[0].rhs == 10.0

    assert model.options.tolerance == 1e-6
    assert model.options.binding_tolerance == 1e-5
    assert model.options.time_limit_seconds == 30.0


def test_problem_codec_valid_reward_payload() -> None:
    payload = _valid_reward_payload()
    model = scenario_max_min_reward_model_from_public_dict(payload)

    assert model.orientation is ScenarioOrientation.MAX_MIN_REWARD
    assert len(model.variables) == 2
    assert model.variables[0].name == "y1"
    assert model.scenarios[0].id == "sA"
    assert model.shared_constraints[0].relation is Relation.GE


def test_problem_codec_rejects_cross_orientation() -> None:
    loss_payload = _valid_loss_payload()
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_max_min_reward_model_from_public_dict(loss_payload)
    assert exc_info.value.detail_code == "scenario.orientation_mismatch"
    assert exc_info.value.path == "$.orientation"

    reward_payload = _valid_reward_payload()
    with pytest.raises(CodedValidationError) as exc_info2:
        scenario_min_max_loss_model_from_public_dict(reward_payload)
    assert exc_info2.value.detail_code == "scenario.orientation_mismatch"
    assert exc_info2.value.path == "$.orientation"


def test_problem_codec_rejects_unknown_top_level_field() -> None:
    payload = _valid_loss_payload()
    payload["unexpected_field"] = 123
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload)
    assert exc_info.value.detail_code == "scenario.invalid_structure"
    assert exc_info.value.path == "$.unexpected_field"


def test_problem_codec_rejects_missing_required_fields() -> None:
    for req in (
        "version",
        "problem_type",
        "orientation",
        "variables",
        "scenarios",
    ):
        payload = _valid_loss_payload()
        del payload[req]
        with pytest.raises(CodedValidationError) as exc_info:
            scenario_min_max_loss_model_from_public_dict(payload)
        assert exc_info.value.detail_code == "scenario.invalid_structure"
        assert exc_info.value.path == f"$.{req}"


def test_problem_codec_rejects_invalid_version_and_type() -> None:
    payload_v = _valid_loss_payload()
    payload_v["version"] = "2"
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload_v)
    assert exc_info.value.detail_code == "scenario.invalid_version"
    assert exc_info.value.path == "$.version"

    payload_t = _valid_loss_payload()
    payload_t["problem_type"] = "quadratic_scenario"
    with pytest.raises(CodedValidationError) as exc_info2:
        scenario_min_max_loss_model_from_public_dict(payload_t)
    assert exc_info2.value.detail_code == "scenario.invalid_problem_type"
    assert exc_info2.value.path == "$.problem_type"


def test_problem_codec_rejects_boolean_as_number() -> None:
    payload_lb = _valid_loss_payload()
    payload_lb["variables"][0]["lower_bound"] = True
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload_lb)
    assert exc_info.value.detail_code == "scenario.boolean_as_number"
    assert exc_info.value.path == "$.variables[0].lower_bound"

    payload_c = _valid_loss_payload()
    payload_c["scenarios"][0]["coefficients"][0] = False
    with pytest.raises(CodedValidationError) as exc_info2:
        scenario_min_max_loss_model_from_public_dict(payload_c)
    assert exc_info2.value.detail_code == "scenario.boolean_as_number"
    assert exc_info2.value.path == "$.scenarios[0].coefficients[0]"


def test_problem_codec_rejects_non_finite_numbers() -> None:
    payload_nan = _valid_loss_payload()
    payload_nan["shared_constraints"][0]["rhs"] = float("nan")
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload_nan)
    assert exc_info.value.detail_code == "scenario.non_finite_value"
    assert exc_info.value.path == "$.shared_constraints[0].rhs"


def test_problem_codec_rejects_duplicate_names_and_ids() -> None:
    payload_dup_var = _valid_loss_payload()
    payload_dup_var["variables"][1]["name"] = "x1"
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload_dup_var)
    assert exc_info.value.detail_code == "scenario.duplicate_variable_name"
    assert exc_info.value.path == "$.variables[1].name"

    payload_dup_scen = _valid_loss_payload()
    payload_dup_scen["scenarios"][1]["id"] = "s1"
    with pytest.raises(CodedValidationError) as exc_info2:
        scenario_min_max_loss_model_from_public_dict(payload_dup_scen)
    assert exc_info2.value.detail_code == "scenario.duplicate_scenario_id"
    assert exc_info2.value.path == "$.scenarios[1].id"


def test_problem_codec_rejects_invalid_bounds() -> None:
    payload = _valid_loss_payload()
    payload["variables"][0]["lower_bound"] = 10.0
    payload["variables"][0]["upper_bound"] = 5.0
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload)
    assert exc_info.value.detail_code == "scenario.invalid_bounds"
    assert exc_info.value.path == "$.variables[0]"


def test_problem_codec_rejects_dimension_mismatch() -> None:
    payload_scen = _valid_loss_payload()
    payload_scen["scenarios"][0]["coefficients"] = [1.0, 2.0, 3.0]  # 3 vs 2
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload_scen)
    assert exc_info.value.detail_code == "scenario.dimension_mismatch"
    assert exc_info.value.path == "$.scenarios[0].coefficients"

    payload_obj = _valid_loss_payload()
    payload_obj["shared_objective"]["coefficients"] = [1.0]  # 1 vs 2
    with pytest.raises(CodedValidationError) as exc_info2:
        scenario_min_max_loss_model_from_public_dict(payload_obj)
    assert exc_info2.value.detail_code == "scenario.dimension_mismatch"
    assert exc_info2.value.path == "$.shared_objective.coefficients"


def test_problem_codec_rejects_invalid_relation_and_options() -> None:
    payload_rel = _valid_loss_payload()
    payload_rel["shared_constraints"][0]["relation"] = "<"
    with pytest.raises(CodedValidationError) as exc_info:
        scenario_min_max_loss_model_from_public_dict(payload_rel)
    assert exc_info.value.detail_code == "scenario.invalid_relation"
    assert exc_info.value.path == "$.shared_constraints[0].relation"

    payload_opt = _valid_loss_payload()
    payload_opt["options"]["tolerance"] = -0.01
    with pytest.raises(CodedValidationError) as exc_info2:
        scenario_min_max_loss_model_from_public_dict(payload_opt)
    assert exc_info2.value.detail_code == "scenario.invalid_option"
    assert exc_info2.value.path == "$.options.tolerance"


def test_result_codec_optimal_candidate() -> None:
    lp_sol = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=10.857142857142858,
        values={
            "x1": 5.285714285714286,
            "x2": 4.714285714285714,
            "_aux_theta": 10.857142857142858,
        },
        diagnostics=SolverDiagnostics(
            method="highs",
            message="Optimization terminated successfully",
            status_code=0,
            nit=5,
            success=True,
        ),
        extras={"backend": "scipy.highs", "wall_time": 0.003, "solver": "highs"},
    )
    result = ScenarioResult(
        status=ScenarioSolveStatus.OPTIMAL,
        orientation=ScenarioOrientation.MIN_MAX_LOSS,
        original_variable_order=("x1", "x2"),
        scenario_order=("s1", "s2", "s3"),
        guaranteed_value=10.857142857142858,
        variables={"x1": 5.285714285714286, "x2": 4.714285714285714},
        scenario_values=(
            ScenarioValue("s1", 10.857142857142858, True),
            ScenarioValue("s2", 10.857142857142858, True),
            ScenarioValue("s3", 6.0, False),
        ),
        binding_scenario_ids=("s1", "s2"),
        delegated_solution=lp_sol,
        auxiliary_variable_name="_aux_theta",
        auxiliary_value=10.857142857142858,
    )

    codec = ScenarioResultCodec()
    serialized = codec.serialize(result)

    assert serialized.mathematical_status == MathematicalStatus.OPTIMAL
    assert serialized.termination_reason == TerminationReason.COMPLETED
    assert serialized.result["orientation"] == "minimize_maximum_loss"
    assert serialized.result["guaranteed_value"] == pytest.approx(10.857142857142858)
    assert serialized.result["variables"] == [
        {"name": "x1", "value": 5.285714285714286},
        {"name": "x2", "value": 4.714285714285714},
    ]
    assert serialized.result["scenario_values"] == [
        {"scenario_id": "s1", "value": 10.857142857142858, "is_binding": True},
        {"scenario_id": "s2", "value": 10.857142857142858, "is_binding": True},
        {"scenario_id": "s3", "value": 6.0, "is_binding": False},
    ]
    assert serialized.result["binding_scenario_ids"] == ["s1", "s2"]

    # Auxiliary variables and delegated private structures must not be exposed in result DTO
    assert "_aux_theta" not in str(serialized.result)
    assert serialized.diagnostics["backend"] == "scipy.highs"
    assert serialized.diagnostics["wall_time"] == 0.003


def test_result_codec_no_candidate() -> None:
    lp_sol = LPSolution(
        status=SolveStatus.INFEASIBLE,
        objective=None,
        values={},
        diagnostics=SolverDiagnostics(
            method="highs",
            message="The problem is infeasible",
            status_code=3,
            success=False,
        ),
        extras={"backend": "scipy.highs"},
    )
    result = ScenarioResult(
        status=ScenarioSolveStatus.INFEASIBLE,
        orientation=ScenarioOrientation.MAX_MIN_REWARD,
        original_variable_order=("x1", "x2"),
        scenario_order=("s1", "s2"),
        guaranteed_value=None,
        variables=None,
        scenario_values=(),
        binding_scenario_ids=(),
        delegated_solution=lp_sol,
        auxiliary_variable_name="_aux_tau",
        auxiliary_value=None,
    )

    codec = ScenarioResultCodec()
    serialized = codec.serialize(result)

    assert serialized.mathematical_status == MathematicalStatus.INFEASIBLE
    assert serialized.termination_reason == TerminationReason.COMPLETED
    assert serialized.result["orientation"] == "maximize_minimum_reward"
    assert serialized.result["guaranteed_value"] is None
    assert serialized.result["variables"] == []
    assert serialized.result["scenario_values"] == []
    assert serialized.result["binding_scenario_ids"] == []
