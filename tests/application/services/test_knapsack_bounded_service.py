from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.ports.bounded_knapsack_solver_port import (
    BoundedKnapsackSolverPort,
)
from optees.composition.local_agent import (
    KNAPSACK_BOUNDED_BACKEND_ID,
    KNAPSACK_BOUNDED_CAPABILITY_ID,
    create_knapsack_bounded_optimization_service,
    create_local_optimization_service,
)


REFERENCE_CASES_PATH = Path("tests/data/knapsack/reference_cases.json")


class FakeBoundedKnapsackSolver(BoundedKnapsackSolverPort):
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 32.0,
            "quantities": [2, 2],
            "extras": {
                "method": "bounded_dynamic_programming",
                "complexity": "O(capacity * sum_i feasible_quantity_i)",
                "item_count": 2,
                "capacity": 10,
                "dp_cells": 77,
                "max_dp_cells": 100,
                "success": True,
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "bounded",
        "capacity": 10,
        "items": [
            {"name": "A", "value": 6, "weight": 2, "max_quantity": 3},
            {"name": "B", "value": 10, "weight": 3, "max_quantity": 2},
        ],
    }


def _reference_cases() -> list[dict]:
    return json.loads(REFERENCE_CASES_PATH.read_text(encoding="utf-8"))["bounded"]


def test_bounded_capability_executes_through_fake_solver_port():
    fake = FakeBoundedKnapsackSolver()
    service = create_knapsack_bounded_optimization_service(solver_port=fake)

    outcome = service.solve(KNAPSACK_BOUNDED_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["quantities"] == [2, 2]
    assert outcome.result["total_weight"] == 10
    assert outcome.diagnostics["backend_id"] == KNAPSACK_BOUNDED_BACKEND_ID
    assert fake.problem == {
        "values": [6.0, 10.0],
        "weights": [2, 3],
        "max_quantities": [3, 2],
        "capacity": 10,
        "var_names": ["A", "B"],
    }


def test_bounded_capability_rejects_zero_one_payload_before_solver_call():
    fake = FakeBoundedKnapsackSolver()
    service = create_knapsack_bounded_optimization_service(solver_port=fake)
    payload = _payload()
    payload["variant"] = "zero_one"

    outcome = service.solve(KNAPSACK_BOUNDED_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert fake.problem is None


@pytest.mark.parametrize("case", _reference_cases(), ids=lambda case: case["id"])
def test_production_service_solves_documented_bounded_reference_cases(case: dict):
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "bounded",
        "capacity": case["capacity"],
        "items": case["items"],
    }

    outcome = create_local_optimization_service().solve(
        KNAPSACK_BOUNDED_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["objective"] == pytest.approx(case["expected_objective"])
    assert outcome.result["quantities"] == case["expected_quantities"]
    assert outcome.result["total_weight"] <= case["capacity"]


def test_production_registry_includes_bounded_capability():
    descriptors = create_local_optimization_service().list_capabilities()
    descriptor = next(
        item for item in descriptors if item["id"] == KNAPSACK_BOUNDED_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == [KNAPSACK_BOUNDED_BACKEND_ID]
    item_schema = descriptor["input_schema"]["properties"]["items"]["items"]
    assert "max_quantity" in item_schema["required"]
