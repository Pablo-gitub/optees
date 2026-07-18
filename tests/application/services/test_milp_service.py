from __future__ import annotations

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    MILP_BACKEND_IDS,
    MILP_CAPABILITY_ID,
    MILP_ROUTER_ID,
    create_local_optimization_service,
    create_milp_optimization_service,
)


class RecordingMilpSolver:
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Feasible",
            "objective": 11,
            "x": {"x": 4, "open": 1},
            "extras": {
                "backend": "fake",
                "best_bound": 12,
                "relative_gap": 1 / 12,
                "success": True,
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "variables": [
            {"name": "x", "label": "units", "lb": 0, "ub": 4, "integrality": "I"},
            {"name": "open", "label": "setup", "lb": 0, "ub": 1, "integrality": "B"},
        ],
        "objective": {"sense": "max", "coefficients": [3, -1], "offset": 0},
        "constraints": [
            {"coefficients": [1, -4], "relation": "<=", "rhs": 0},
        ],
        "solver": {"time_limit": 10, "mip_gap": 0.01},
    }


def test_milp_capability_maps_public_contract_through_solver_port():
    solver = RecordingMilpSolver()
    service = create_milp_optimization_service(solver_port=solver)

    outcome = service.solve(MILP_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "feasible"
    assert outcome.result["objective"] == pytest.approx(11.0)
    assert outcome.validation.status.value == "verified"
    assert [check.code for check in outcome.validation.checks] == [
        "milp.variable_vector",
        "milp.bounds",
        "milp.integrality",
        "milp.constraints",
        "milp.objective",
    ]
    assert solver.problem["sense"] == "max"
    assert solver.problem["integrality"] == ["I", "B"]
    assert solver.problem["bounds"] == [(0.0, 4.0), (0.0, 1.0)]
    assert solver.problem["time_limit"] == pytest.approx(10.0)
    assert solver.problem["mip_gap"] == pytest.approx(0.01)
    assert outcome.diagnostics["backend_id"] == MILP_ROUTER_ID


def test_invalid_payload_is_rejected_before_solver_call():
    solver = RecordingMilpSolver()
    service = create_milp_optimization_service(solver_port=solver)
    payload = _payload()
    payload["objective"]["coefficients"] = [1]

    outcome = service.solve(MILP_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert solver.problem is None


def test_unavailable_dependency_is_reported_without_solver_call():
    solver = RecordingMilpSolver()
    service = create_milp_optimization_service(
        solver_port=solver,
        dependency_available=False,
    )

    outcome = service.solve(MILP_CAPABILITY_ID, _payload())

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert solver.problem is None


def test_production_service_solves_binary_assignment():
    pytest.importorskip("ortools")
    payload = {
        "version": "1",
        "variables": [
            {"name": "x11", "lb": 0, "ub": 1, "integrality": "B"},
            {"name": "x12", "lb": 0, "ub": 1, "integrality": "B"},
            {"name": "x21", "lb": 0, "ub": 1, "integrality": "B"},
            {"name": "x22", "lb": 0, "ub": 1, "integrality": "B"},
        ],
        "objective": {"sense": "min", "coefficients": [1, 2, 2, 1]},
        "constraints": [
            {"coefficients": [1, 1, 0, 0], "relation": "=", "rhs": 1},
            {"coefficients": [0, 0, 1, 1], "relation": "=", "rhs": 1},
            {"coefficients": [1, 0, 1, 0], "relation": "=", "rhs": 1},
            {"coefficients": [0, 1, 0, 1], "relation": "=", "rhs": 1},
        ],
    }

    outcome = create_local_optimization_service().solve(MILP_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["objective"] == pytest.approx(2.0)
    values = {item["name"]: item["value"] for item in outcome.result["variables"]}
    assert values["x11"] == pytest.approx(1.0)
    assert values["x22"] == pytest.approx(1.0)


def test_production_service_preserves_infeasible_status():
    pytest.importorskip("ortools")
    payload = {
        "version": "1",
        "variables": [{"name": "x", "lb": 0, "ub": 1, "integrality": "B"}],
        "objective": {"sense": "max", "coefficients": [1]},
        "constraints": [
            {"coefficients": [1], "relation": ">=", "rhs": 1},
            {"coefficients": [1], "relation": "<=", "rhs": 0},
        ],
    }

    outcome = create_local_optimization_service().solve(MILP_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "infeasible"
    assert outcome.result["objective"] is None


def test_registry_documents_milp_backends_and_time_limit():
    descriptor = next(
        item
        for item in create_local_optimization_service().list_capabilities()
        if item["id"] == MILP_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == list(MILP_BACKEND_IDS)
    assert descriptor["supports_time_limit"] is True
