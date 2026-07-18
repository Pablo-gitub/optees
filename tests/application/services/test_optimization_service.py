from __future__ import annotations

from dataclasses import replace
import importlib.util
import sys

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.application.contracts.solution_validation import (
    SolutionValidationStatus,
)
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.application.services.capability_registry import CapabilityRegistry
from optees.application.services.optimization_service import OptimizationService
from optees.composition.local_agent import (
    LP_BACKEND_ID,
    LP_CAPABILITY_ID,
    create_local_optimization_service,
    create_lp_registration,
    create_lp_optimization_service,
)


class FakeLPSolver(LPSolverPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self.problem = None
        self.error = error

    def solve(self, problem):
        self.problem = problem
        if self.error is not None:
            raise self.error
        return {
            "status": "Optimal",
            "objective": 10.0,
            "x": {"x": 2.0, "y": 2.0},
            "extras": {
                "method": "highs",
                "success": True,
                "status_code": 0,
                "message": "Solved by fake port.",
                "nit": 3,
                "var_names": ["x", "y"],
                "objective_sense": "max",
            },
        }


def _valid_payload() -> dict:
    return {
        "version": "1",
        "variables": [
            {"name": "x", "label": "", "lb": 0, "ub": None},
            {"name": "y", "label": "", "lb": 0, "ub": None},
        ],
        "objective": {
            "sense": "max",
            "coefficients": [3, 2],
            "offset": 0,
        },
        "constraints": [
            {"coefficients": [1, 1], "relation": "<=", "rhs": 4},
            {"coefficients": [1, 0], "relation": "<=", "rhs": 2},
        ],
    }


def test_lp_pilot_executes_with_fake_port_and_returns_versioned_envelope():
    fake = FakeLPSolver()
    service = create_lp_optimization_service(solver_port=fake)

    outcome = service.solve(LP_CAPABILITY_ID, _valid_payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.job_status is JobStatus.COMPLETED
    assert outcome.mathematical_status is MathematicalStatus.OPTIMAL
    assert outcome.termination_reason is TerminationReason.COMPLETED
    assert outcome.result["objective"] == pytest.approx(10.0)
    assert outcome.validation.status is SolutionValidationStatus.VERIFIED
    assert outcome.diagnostics["backend_id"] == LP_BACKEND_ID
    assert outcome.metadata.problem_schema_version == "1"
    assert fake.problem["sense"] == "max"
    assert fake.problem["method"] == "highs"


def test_capability_discovery_does_not_expose_backend_as_problem_type():
    service = create_lp_optimization_service(solver_port=FakeLPSolver())

    descriptor = service.list_capabilities()[0]

    assert descriptor["id"] == LP_CAPABILITY_ID
    assert descriptor["problem_type"] == "linear_programming"
    assert descriptor["backend_candidates"] == [LP_BACKEND_ID]
    assert descriptor["default_options"] == {"method": "highs"}
    assert descriptor["available"] is True


def test_lp_capability_exposes_an_agent_ready_problem_schema_and_example():
    service = create_lp_optimization_service(solver_port=FakeLPSolver())

    descriptor = service.list_capabilities()[0]
    schema = descriptor["input_schema"]
    example = schema["examples"][0]

    assert schema["properties"]["variables"]["items"]["required"] == [
        "name",
        "lb",
        "ub",
    ]
    assert schema["properties"]["objective"]["required"] == [
        "sense",
        "coefficients",
    ]
    assert schema["properties"]["constraints"]["items"]["required"] == [
        "coefficients",
        "relation",
        "rhs",
    ]
    optimal_face = descriptor["result_schema"]["properties"]["optimal_face"]
    assert "analysis_status" in optimal_face["required"]
    assert "has_alternate_optimum" in optimal_face["required"]
    assert "ranges" in optimal_face["required"]
    assert service.validate(LP_CAPABILITY_ID, example).to_dict()["valid"] is True


def test_invalid_lp_payload_returns_validation_details_without_calling_solver():
    fake = FakeLPSolver()
    service = create_lp_optimization_service(solver_port=fake)
    payload = _valid_payload()
    payload["objective"]["coefficients"] = [1]

    outcome = service.solve(LP_CAPABILITY_ID, payload, request_id="request-1")

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert outcome.request_id == "request-1"
    assert "there are 2 variables" in outcome.details[0].message
    assert fake.problem is None


def test_validate_parses_payload_without_executing_solver():
    fake = FakeLPSolver()
    service = create_lp_optimization_service(solver_port=fake)

    outcome = service.validate(LP_CAPABILITY_ID, _valid_payload())

    assert outcome.to_dict() == {
        "contract_version": "1",
        "capability_id": LP_CAPABILITY_ID,
        "valid": True,
        "available": True,
        "problem_schema_version": "1",
        "warnings": [],
    }
    assert fake.problem is None


def test_validate_reports_valid_payload_even_if_backend_is_unavailable():
    service = create_lp_optimization_service(
        solver_port=FakeLPSolver(), dependency_available=False
    )

    outcome = service.validate(LP_CAPABILITY_ID, _valid_payload())

    assert outcome.to_dict()["valid"] is True
    assert outcome.to_dict()["available"] is False
    assert outcome.to_dict()["warnings"]


def test_non_json_payload_is_rejected_before_domain_validation():
    service = create_lp_optimization_service(solver_port=FakeLPSolver())
    payload = _valid_payload()
    payload["objective"]["offset"] = float("nan")

    outcome = service.solve(LP_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.INVALID_REQUEST
    assert "non-finite" in outcome.details[0].message


def test_unknown_capability_returns_stable_structured_error():
    service = create_lp_optimization_service(solver_port=FakeLPSolver())

    outcome = service.solve("missing.capability", {})

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.CAPABILITY_NOT_FOUND


def test_unavailable_dependency_is_visible_in_discovery_and_solve_error():
    service = create_lp_optimization_service(
        solver_port=FakeLPSolver(), dependency_available=False
    )

    descriptor = service.list_capabilities()[0]
    outcome = service.solve(LP_CAPABILITY_ID, _valid_payload())

    assert descriptor["available"] is False
    assert "SciPy" in descriptor["unavailable_reason"]
    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert "SciPy" in outcome.context["reason"]


def test_technical_execution_error_does_not_leak_exception_message():
    service = create_lp_optimization_service(
        solver_port=FakeLPSolver(error=RuntimeError("secret dataset row 42"))
    )

    outcome = service.solve(LP_CAPABILITY_ID, _valid_payload())

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.EXECUTION_FAILED
    assert "secret dataset" not in str(outcome.to_dict())


def test_validator_failure_preserves_the_solver_result_and_is_not_available():
    registration = create_lp_registration(solver_port=FakeLPSolver())
    registry = CapabilityRegistry()
    registry.register(
        replace(
            registration,
            validate_result=lambda _model, _result: 1 / 0,
        )
    )
    service = OptimizationService(registry, job_id_factory=lambda: "job-test")

    outcome = service.solve(LP_CAPABILITY_ID, _valid_payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status is MathematicalStatus.OPTIMAL
    assert outcome.result["objective"] == pytest.approx(10.0)
    assert outcome.validation.status is SolutionValidationStatus.NOT_AVAILABLE
    assert "failed internally" in outcome.validation.limitations[0]


@pytest.mark.skipif(
    importlib.util.find_spec("scipy") is None,
    reason="SciPy is not installed.",
)
def test_production_composition_solves_reference_lp_without_presentation_imports():
    presentation_before = {
        name for name in sys.modules if name.startswith("optees.presentation")
    }
    service = create_local_optimization_service()

    outcome = service.solve(LP_CAPABILITY_ID, _valid_payload())

    presentation_after = {
        name for name in sys.modules if name.startswith("optees.presentation")
    }
    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status is MathematicalStatus.OPTIMAL
    assert outcome.validation.status is SolutionValidationStatus.VERIFIED
    assert outcome.result["objective"] == pytest.approx(10.0)
    assert {row["name"]: row["value"] for row in outcome.result["variables"]} == (
        pytest.approx({"x": 2.0, "y": 2.0})
    )
    assert presentation_after == presentation_before
