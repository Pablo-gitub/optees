from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    NLP_BACKEND_ID,
    NLP_CAPABILITY_ID,
    create_local_optimization_service,
    create_nlp_optimization_service,
)


ROOT = Path(__file__).resolve().parents[3]


class RecordingNLPSolver:
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Converged",
            "objective": 0,
            "x": {"x": 2},
            "extras": {
                "method": "BFGS",
                "success": True,
                "iterations": 3,
                "evaluations": 8,
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "nonlinear_programming",
        "variables": [
            {"name": "x", "label": "coordinate", "lb": None, "ub": None, "initial": 0}
        ],
        "objective": {"sense": "min", "expression": "(x - 2)**2"},
        "solver_options": {
            "method": "BFGS",
            "max_iterations": 100,
            "tolerance": 1e-8,
        },
    }


def test_nlp_capability_maps_public_contract_through_solver_port():
    solver = RecordingNLPSolver()
    service = create_nlp_optimization_service(solver_port=solver)

    outcome = service.solve(NLP_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "feasible"
    assert outcome.result["objective"] == pytest.approx(0.0)
    assert outcome.result["local_candidate"] is True
    assert solver.problem == {
        "sense": "min",
        "expression": "(x - 2)**2",
        "variables": ["x"],
        "initial_point": [0.0],
        "bounds": [(None, None)],
        "method": "BFGS",
        "max_iterations": 100,
        "tolerance": 1e-8,
    }
    assert outcome.diagnostics["backend_id"] == NLP_BACKEND_ID


def test_invalid_payload_is_rejected_before_solver_call():
    solver = RecordingNLPSolver()
    service = create_nlp_optimization_service(solver_port=solver)
    payload = _payload()
    payload["variables"][0]["initial"] = float("nan")

    outcome = service.solve(NLP_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.INVALID_REQUEST
    assert solver.problem is None


def test_unavailable_dependency_is_reported_without_solver_call():
    solver = RecordingNLPSolver()
    service = create_nlp_optimization_service(
        solver_port=solver,
        dependency_available=False,
    )

    outcome = service.solve(NLP_CAPABILITY_ID, _payload())

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert solver.problem is None


def test_production_service_solves_rosenbrock_reference_case():
    payload = json.loads(
        (ROOT / "examples" / "nlp_rosenbrock.json").read_text(encoding="utf-8")
    )

    outcome = create_local_optimization_service().solve(NLP_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "feasible"
    assert outcome.result["local_candidate"] is True
    assert outcome.result["objective"] == pytest.approx(0.0, abs=1e-5)
    values = {item["name"]: item["value"] for item in outcome.result["variables"]}
    assert values == pytest.approx({"x1": 1.0, "x2": 1.0}, abs=1e-5)


def test_registry_documents_nlp_dependency_and_local_contract():
    descriptor = next(
        item
        for item in create_local_optimization_service().list_capabilities()
        if item["id"] == NLP_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == [NLP_BACKEND_ID]
    assert descriptor["supports_time_limit"] is False
    assert descriptor["result_schema"]["properties"]["local_candidate"] == {
        "type": "boolean"
    }
