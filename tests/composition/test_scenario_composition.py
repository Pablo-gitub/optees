from __future__ import annotations

from typing import Any

import pytest

from optees.application.contracts.capability_ids import (
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
)
from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    JobStatus,
    MathematicalStatus,
)
from optees.application.contracts.solution_validation import (
    SolutionValidationStatus,
)
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.application.ports.milp_solver_port import MILPSolverPort
from optees.application.services.capability_registry import (
    RegisteredCapability,
)
from optees.composition.local_agent import (
    create_local_optimization_service,
    create_scenario_max_min_reward_optimization_service,
    create_scenario_min_max_loss_optimization_service,
    create_scenario_min_max_loss_registration,
)


class RecordingLPSolverPort(LPSolverPort):
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response or {
            "status": "Optimal",
            "objective": 0.0,
            "x": {},
            "extras": {},
        }

    def solve(self, problem: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(problem)
        return self._response


class RecordingMILPSolverPort(MILPSolverPort):
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response or {
            "status": "Optimal",
            "objective": 0.0,
            "x": {},
            "extras": {},
        }

    def solve(self, problem: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(problem)
        return self._response


def _valid_continuous_loss_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "minimize_maximum_loss",
        "variables": [
            {
                "name": "x1",
                "label": "X1",
                "lower_bound": 0.0,
                "upper_bound": 10.0,
            },
            {
                "name": "x2",
                "label": "X2",
                "lower_bound": 0.0,
                "upper_bound": 10.0,
            },
        ],
        "scenarios": [
            {"id": "s1", "coefficients": [2.0, -1.0], "offset": 5.0},
            {"id": "s2", "coefficients": [-1.0, 3.0], "offset": 2.0},
            {"id": "s3", "coefficients": [1.0, 1.0], "offset": -4.0},
        ],
        "shared_constraints": [
            {
                "name": "budget",
                "coefficients": [1.0, 1.0],
                "relation": "=",
                "rhs": 10.0,
            }
        ],
        "options": {"tolerance": 1e-7, "binding_tolerance": 1e-6},
    }


def _valid_discrete_reward_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "maximize_minimum_reward",
        "variables": [
            {"name": "b1", "integrality": "B"},
            {"name": "b2", "integrality": "B"},
        ],
        "scenarios": [
            {"id": "s1", "coefficients": [10.0, -5.0], "offset": 0.0},
            {"id": "s2", "coefficients": [-2.0, 8.0], "offset": 0.0},
        ],
        "shared_constraints": [{"coefficients": [1.0, 1.0], "relation": "<=", "rhs": 1.0}],
    }


def test_scenario_composition_continuous_loss_solve_end_to_end() -> None:
    lp_port = RecordingLPSolverPort(
        response={
            "status": "Optimal",
            "objective": 76.0 / 7.0,
            "x": {
                "x1": 37.0 / 7.0,
                "x2": 33.0 / 7.0,
                "_aux_theta": 76.0 / 7.0,
            },
            "extras": {"method": "highs", "iterations": 4},
        }
    )
    milp_port = RecordingMILPSolverPort()
    service = create_scenario_min_max_loss_optimization_service(
        lp_solver_port=lp_port,
        milp_solver_port=milp_port,
    )

    payload = _valid_continuous_loss_payload()
    outcome = service.solve(SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.job_status is JobStatus.COMPLETED
    assert outcome.mathematical_status is MathematicalStatus.OPTIMAL
    assert outcome.result["orientation"] == "minimize_maximum_loss"
    assert outcome.result["guaranteed_value"] == pytest.approx(76.0 / 7.0)
    assert outcome.result["variables"] == [
        {"name": "x1", "value": pytest.approx(37.0 / 7.0)},
        {"name": "x2", "value": pytest.approx(33.0 / 7.0)},
    ]
    assert outcome.result["binding_scenario_ids"] == ["s1", "s2"]

    # Exact once validation via domain callback
    assert outcome.validation is not None
    assert outcome.validation.status is SolutionValidationStatus.VERIFIED
    assert len(outcome.validation.violations) == 0

    assert len(lp_port.calls) == 1
    assert len(milp_port.calls) == 0


def test_scenario_composition_discrete_reward_solve_end_to_end() -> None:
    lp_port = RecordingLPSolverPort()
    milp_port = RecordingMILPSolverPort(
        response={
            "status": "Optimal",
            "objective": 0.0,
            "x": {"b1": 0.0, "b2": 0.0, "_aux_tau": 0.0},
            "extras": {"backend": "ortools.cbc"},
        }
    )
    service = create_scenario_max_min_reward_optimization_service(
        lp_solver_port=lp_port,
        milp_solver_port=milp_port,
    )

    payload = _valid_discrete_reward_payload()
    outcome = service.solve(SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status is MathematicalStatus.OPTIMAL
    assert outcome.result["orientation"] == "maximize_minimum_reward"
    assert outcome.result["guaranteed_value"] == 0.0
    assert outcome.result["variables"] == [
        {"name": "b1", "value": 0.0},
        {"name": "b2", "value": 0.0},
    ]

    assert outcome.validation.status is SolutionValidationStatus.VERIFIED
    assert len(lp_port.calls) == 0
    assert len(milp_port.calls) == 1


def test_scenario_composition_no_candidate_status() -> None:
    lp_port = RecordingLPSolverPort(
        response={
            "status": "Infeasible",
            "objective": None,
            "x": {},
            "extras": {"message": "Infeasible"},
        }
    )
    milp_port = RecordingMILPSolverPort()
    service = create_scenario_min_max_loss_optimization_service(
        lp_solver_port=lp_port,
        milp_solver_port=milp_port,
    )

    payload = _valid_continuous_loss_payload()
    outcome = service.solve(SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status is MathematicalStatus.INFEASIBLE
    assert outcome.result["guaranteed_value"] is None
    assert outcome.result["variables"] == []
    assert outcome.result["scenario_values"] == []
    assert outcome.result["binding_scenario_ids"] == []
    assert outcome.validation.status is SolutionValidationStatus.NOT_AVAILABLE


def test_scenario_composition_unavailable_dependency() -> None:
    lp_port = RecordingLPSolverPort()
    milp_port = RecordingMILPSolverPort()
    service = create_scenario_min_max_loss_optimization_service(
        lp_solver_port=lp_port,
        milp_solver_port=milp_port,
        dependency_available=False,
    )

    payload = _valid_continuous_loss_payload()
    outcome = service.solve(SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_scenario_composition_validate_mutual_exclusion_in_registered_capability() -> None:
    reg = create_scenario_min_max_loss_registration(
        lp_solver_port=RecordingLPSolverPort(),
        milp_solver_port=RecordingMILPSolverPort(),
    )

    with pytest.raises(
        ValueError,
        match="validate_result and validate_domain_result are mutually exclusive",
    ):
        RegisteredCapability(
            descriptor=reg.descriptor,
            parse_problem=reg.parse_problem,
            execute=reg.execute,
            serialize_result=reg.serialize_result,
            backend_id=reg.backend_id,
            validate_result=lambda _m, _s: None,  # type: ignore[return-value]
            validate_domain_result=lambda _m, _r: None,  # type: ignore[return-value]
        )


def test_scenario_composition_validator_internal_failure_containment() -> None:
    def crashing_validator(_model: Any, _result: Any) -> Any:
        raise RuntimeError("Validator memory error")

    reg = create_scenario_min_max_loss_registration(
        lp_solver_port=RecordingLPSolverPort(
            response={
                "status": "Optimal",
                "objective": 76.0 / 7.0,
                "x": {
                    "x1": 37.0 / 7.0,
                    "x2": 33.0 / 7.0,
                    "_aux_theta": 76.0 / 7.0,
                },
                "extras": {},
            }
        ),
        milp_solver_port=RecordingMILPSolverPort(),
    )
    reg_with_crashing_val = RegisteredCapability(
        descriptor=reg.descriptor,
        parse_problem=reg.parse_problem,
        execute=reg.execute,
        serialize_result=reg.serialize_result,
        backend_id=reg.backend_id,
        validate_domain_result=crashing_validator,
    )

    from optees.application.services.capability_registry import (
        CapabilityRegistry,
    )
    from optees.application.services.optimization_service import (
        OptimizationService,
    )

    registry = CapabilityRegistry()
    registry.register(reg_with_crashing_val)
    service = OptimizationService(registry)

    payload = _valid_continuous_loss_payload()
    outcome = service.solve(SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    # Mathematical result remains intact
    assert outcome.mathematical_status is MathematicalStatus.OPTIMAL
    assert outcome.result["guaranteed_value"] == pytest.approx(76.0 / 7.0)
    # Validation gracefully degrades to not_available
    assert outcome.validation.status is SolutionValidationStatus.NOT_AVAILABLE
    assert "The independent validator failed internally." in outcome.validation.limitations


def test_scenario_composition_local_optimization_service_discovery() -> None:
    service = create_local_optimization_service()
    caps = {c["id"]: c for c in service.list_capabilities()}

    assert SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID in caps
    assert SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID in caps

    loss_cap = caps[SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID]
    assert loss_cap["problem_type"] == "linear_scenario"
    assert loss_cap["problem_schema_version"] == "1"
    assert loss_cap["result_schema_version"] == "1"
