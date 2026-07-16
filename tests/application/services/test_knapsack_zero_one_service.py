from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.ports.knapsack_solver_port import KnapsackSolverPort
from optees.composition.local_agent import (
    KNAPSACK_ZERO_ONE_BACKEND_ID,
    KNAPSACK_ZERO_ONE_CAPABILITY_ID,
    create_knapsack_zero_one_optimization_service,
    create_local_optimization_service,
)
from optees.utility.data_adapters.knapsack_burkardt_adapter import (
    load_knapsack_burkardt,
)


DATA_ROOT = Path("tests/data/knapsack")


class FakeKnapsackSolver(KnapsackSolverPort):
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 11.0,
            "selected_indices": [0, 2],
            "extras": {
                "method": "dynamic_programming",
                "complexity": "O(n * capacity)",
                "item_count": 3,
                "capacity": 5,
                "dp_cells": 24,
                "max_dp_cells": 100,
                "success": True,
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "zero_one",
        "capacity": 5,
        "items": [
            {"name": "A", "value": 6, "weight": 2},
            {"name": "B", "value": 10, "weight": 4},
            {"name": "C", "value": 5, "weight": 3},
        ],
    }


def test_zero_one_capability_executes_through_fake_solver_port():
    fake = FakeKnapsackSolver()
    service = create_knapsack_zero_one_optimization_service(solver_port=fake)

    outcome = service.solve(KNAPSACK_ZERO_ONE_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["selected_indices"] == [0, 2]
    assert outcome.result["remaining_capacity"] == 0
    assert outcome.diagnostics["backend_id"] == KNAPSACK_ZERO_ONE_BACKEND_ID
    assert fake.problem == {
        "values": [6.0, 10.0, 5.0],
        "weights": [2, 4, 3],
        "capacity": 5,
        "var_names": ["A", "B", "C"],
    }


def test_zero_one_capability_rejects_bounded_payload_before_solver_call():
    fake = FakeKnapsackSolver()
    service = create_knapsack_zero_one_optimization_service(solver_port=fake)
    payload = _payload()
    payload["variant"] = "bounded"

    outcome = service.solve(KNAPSACK_ZERO_ONE_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert fake.problem is None


@pytest.mark.parametrize("instance", ["p01", "p02"])
def test_production_service_solves_burkardt_reference_instances(instance: str):
    data = load_knapsack_burkardt(str(DATA_ROOT / instance), instance)
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "zero_one",
        "capacity": data["capacity"],
        "items": [
            {
                "name": f"{instance}_item_{index + 1}",
                "value": value,
                "weight": weight,
            }
            for index, (value, weight) in enumerate(
                zip(data["values"], data["weights"], strict=True)
            )
        ],
    }
    expected_indices = [
        index for index, selected in enumerate(data["opt_selection"]) if selected
    ]

    outcome = create_local_optimization_service().solve(
        KNAPSACK_ZERO_ONE_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["selected_indices"] == expected_indices
    assert outcome.result["total_weight"] <= data["capacity"]
    assert outcome.result["objective"] == pytest.approx(outcome.result["total_value"])


def test_production_registry_contains_lp_and_zero_one_knapsack():
    descriptors = create_local_optimization_service().list_capabilities()

    assert {
        "lp.continuous",
        "knapsack.zero_one",
    } <= {descriptor["id"] for descriptor in descriptors}
