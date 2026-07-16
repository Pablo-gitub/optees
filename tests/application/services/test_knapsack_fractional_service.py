from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.ports.fractional_knapsack_solver_port import (
    FractionalKnapsackSolverPort,
)
from optees.composition.local_agent import (
    KNAPSACK_FRACTIONAL_BACKEND_ID,
    KNAPSACK_FRACTIONAL_CAPABILITY_ID,
    create_knapsack_fractional_optimization_service,
    create_local_optimization_service,
)


REFERENCE_CASES_PATH = Path("tests/data/knapsack/reference_cases.json")


class FakeFractionalKnapsackSolver(FractionalKnapsackSolverPort):
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 240.0,
            "fractions": [1.0, 1.0, 2 / 3],
            "extras": {
                "method": "fractional_greedy_density",
                "complexity": "O(n log n)",
                "item_count": 3,
                "capacity": 50.0,
                "max_items": 100,
                "success": True,
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "fractional",
        "capacity": 50,
        "items": [
            {"name": "A", "value": 60, "weight": 10},
            {"name": "B", "value": 100, "weight": 20},
            {"name": "C", "value": 120, "weight": 30},
        ],
    }


def _reference_cases() -> list[dict]:
    return json.loads(REFERENCE_CASES_PATH.read_text(encoding="utf-8"))["fractional"]


def test_fractional_capability_executes_through_fake_solver_port():
    fake = FakeFractionalKnapsackSolver()
    service = create_knapsack_fractional_optimization_service(solver_port=fake)

    outcome = service.solve(KNAPSACK_FRACTIONAL_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["fractions"] == pytest.approx([1.0, 1.0, 2 / 3])
    assert outcome.result["total_weight"] == pytest.approx(50.0)
    assert outcome.diagnostics["backend_id"] == KNAPSACK_FRACTIONAL_BACKEND_ID
    assert fake.problem == {
        "values": [60.0, 100.0, 120.0],
        "weights": [10.0, 20.0, 30.0],
        "capacity": 50.0,
        "var_names": ["A", "B", "C"],
    }


def test_fractional_capability_rejects_zero_one_payload_before_solver_call():
    fake = FakeFractionalKnapsackSolver()
    service = create_knapsack_fractional_optimization_service(solver_port=fake)
    payload = _payload()
    payload["variant"] = "zero_one"

    outcome = service.solve(KNAPSACK_FRACTIONAL_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert fake.problem is None


@pytest.mark.parametrize("case", _reference_cases(), ids=lambda case: case["id"])
def test_production_service_solves_fractional_reference_cases(case: dict):
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "fractional",
        "capacity": case["capacity"],
        "items": case["items"],
    }

    outcome = create_local_optimization_service().solve(
        KNAPSACK_FRACTIONAL_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["objective"] == pytest.approx(case["expected_objective"])
    assert outcome.result["fractions"] == pytest.approx(case["expected_fractions"])
    assert outcome.result["total_weight"] <= case["capacity"] + 1e-9


def test_production_registry_includes_fractional_capability():
    descriptors = create_local_optimization_service().list_capabilities()
    descriptor = next(
        item for item in descriptors if item["id"] == KNAPSACK_FRACTIONAL_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == [KNAPSACK_FRACTIONAL_BACKEND_ID]
    item_schema = descriptor["input_schema"]["properties"]["items"]["items"]
    assert item_schema["properties"]["weight"]["exclusiveMinimum"] == 0
