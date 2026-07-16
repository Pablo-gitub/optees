from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.ports.unbounded_knapsack_solver_port import (
    UnboundedKnapsackSolverPort,
)
from optees.composition.local_agent import (
    KNAPSACK_UNBOUNDED_BACKEND_ID,
    KNAPSACK_UNBOUNDED_CAPABILITY_ID,
    create_knapsack_unbounded_optimization_service,
    create_local_optimization_service,
)


REFERENCE_CASES_PATH = Path("tests/data/knapsack/reference_cases.json")


class FakeUnboundedKnapsackSolver(UnboundedKnapsackSolverPort):
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 120.0,
            "quantities": [0, 4, 0],
            "extras": {
                "method": "unbounded_dynamic_programming",
                "complexity": "O(n * capacity)",
                "item_count": 3,
                "capacity": 8,
                "dp_cells": 27,
                "max_dp_cells": 100,
                "success": True,
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "unbounded",
        "capacity": 8,
        "items": [
            {"name": "A", "value": 10, "weight": 1},
            {"name": "B", "value": 30, "weight": 2},
            {"name": "C", "value": 44, "weight": 3},
        ],
    }


def _reference_cases() -> list[dict]:
    return json.loads(REFERENCE_CASES_PATH.read_text(encoding="utf-8"))["unbounded"]


def test_unbounded_capability_executes_through_fake_solver_port():
    fake = FakeUnboundedKnapsackSolver()
    service = create_knapsack_unbounded_optimization_service(solver_port=fake)

    outcome = service.solve(KNAPSACK_UNBOUNDED_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["quantities"] == [0, 4, 0]
    assert outcome.result["total_weight"] == 8
    assert outcome.diagnostics["backend_id"] == KNAPSACK_UNBOUNDED_BACKEND_ID
    assert fake.problem == {
        "values": [10.0, 30.0, 44.0],
        "weights": [1, 2, 3],
        "capacity": 8,
        "var_names": ["A", "B", "C"],
    }


def test_unbounded_capability_rejects_bounded_payload_before_solver_call():
    fake = FakeUnboundedKnapsackSolver()
    service = create_knapsack_unbounded_optimization_service(solver_port=fake)
    payload = _payload()
    payload["variant"] = "bounded"

    outcome = service.solve(KNAPSACK_UNBOUNDED_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert fake.problem is None


@pytest.mark.parametrize("case", _reference_cases(), ids=lambda case: case["id"])
def test_production_service_solves_documented_unbounded_reference_cases(case: dict):
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "unbounded",
        "capacity": case["capacity"],
        "items": case["items"],
    }

    outcome = create_local_optimization_service().solve(
        KNAPSACK_UNBOUNDED_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["objective"] == pytest.approx(case["expected_objective"])
    assert outcome.result["quantities"] == case["expected_quantities"]
    assert outcome.result["total_weight"] <= case["capacity"]


def test_positive_value_zero_weight_item_is_mathematically_unbounded():
    payload = _payload()
    payload["items"] = [{"name": "Free value", "value": 1, "weight": 0}]

    outcome = create_local_optimization_service().solve(
        KNAPSACK_UNBOUNDED_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "unbounded"
    assert outcome.result["objective"] is None
    assert outcome.result["quantities"] == [0]
    assert "zero weight" in outcome.diagnostics["message"]
    json.dumps(outcome.to_dict(), allow_nan=False)


def test_production_registry_includes_unbounded_capability():
    descriptors = create_local_optimization_service().list_capabilities()
    descriptor = next(
        item for item in descriptors if item["id"] == KNAPSACK_UNBOUNDED_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == [KNAPSACK_UNBOUNDED_BACKEND_ID]
    assert descriptor["input_schema"]["properties"]["variant"] == {
        "const": "unbounded"
    }
