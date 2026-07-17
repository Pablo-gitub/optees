from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    KNAPSACK_MULTI_DIMENSIONAL_BACKEND_IDS,
    KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
    KNAPSACK_MULTI_DIMENSIONAL_ROUTER_ID,
    create_knapsack_multi_dimensional_optimization_service,
    create_local_optimization_service,
)
from optees.utility.data_adapters.orlib_mknap_adapter import load_orlib_mknap


ORLIB_DATASET = Path("tests/data/knapsack/orlib/mknap1.txt")


class RecordingBinarySolver:
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 17,
            "selected_indices": [0, 1],
            "extras": {
                "method": "multidimensional_branch_and_bound",
                "item_count": 2,
                "resource_count": 2,
                "resource_names": ["weight", "volume"],
                "capacities": [10, 6],
                "success": True,
            },
        }


class RecordingMilpSolver:
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 26,
            "x": {"item_1": 1, "item_2": 2},
            "extras": {"backend": "fake", "success": True},
        }


def _payload(*, domain: str = "zero_one") -> dict:
    items = [
        {"name": "A", "value": 8, "usage": [4, 1.5]},
        {"name": "B", "value": 9, "usage": [5, 2]},
    ]
    if domain == "bounded":
        items[0]["max_quantity"] = 1
        items[1]["max_quantity"] = 2
    return {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "multi_dimensional",
        "domain": domain,
        "resources": [
            {"name": "weight", "capacity": 14},
            {"name": "volume", "capacity": 6},
        ],
        "items": items,
    }


def test_binary_domain_routes_only_to_internal_multidimensional_solver():
    binary = RecordingBinarySolver()
    milp = RecordingMilpSolver()
    service = create_knapsack_multi_dimensional_optimization_service(
        binary_solver_port=binary,
        milp_solver_port=milp,
    )

    outcome = service.solve(KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["quantities"] == [1.0, 1.0]
    assert binary.problem["capacities"] == [14.0, 6.0]
    assert milp.problem is None
    assert outcome.diagnostics["backend_id"] == KNAPSACK_MULTI_DIMENSIONAL_ROUTER_ID


def test_bounded_domain_routes_to_milp_with_integer_bounds():
    binary = RecordingBinarySolver()
    milp = RecordingMilpSolver()
    service = create_knapsack_multi_dimensional_optimization_service(
        binary_solver_port=binary,
        milp_solver_port=milp,
    )

    outcome = service.solve(
        KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
        _payload(domain="bounded"),
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert binary.problem is None
    assert milp.problem["bounds"] == [(0.0, 1.0), (0.0, 2.0)]
    assert milp.problem["integrality"] == ["I", "I"]
    assert milp.problem["A_ub"] == [[4.0, 5.0], [1.5, 2.0]]
    assert outcome.result["quantities"] == [1.0, 2.0]
    assert outcome.diagnostics["domain"] == "bounded"


def test_fractional_domain_routes_to_continuous_model():
    binary = RecordingBinarySolver()
    milp = RecordingMilpSolver()
    service = create_knapsack_multi_dimensional_optimization_service(
        binary_solver_port=binary,
        milp_solver_port=milp,
    )
    payload = _payload(domain="fractional")
    payload["items"][1]["max_quantity"] = "inf"

    outcome = service.solve(KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert milp.problem["bounds"] == [(0.0, 1.0), (0.0, None)]
    assert milp.problem["integrality"] == [None, None]
    assert outcome.diagnostics["domain"] == "fractional"


def test_invalid_domain_is_rejected_before_either_solver():
    binary = RecordingBinarySolver()
    milp = RecordingMilpSolver()
    service = create_knapsack_multi_dimensional_optimization_service(
        binary_solver_port=binary,
        milp_solver_port=milp,
    )
    payload = _payload()
    payload["domain"] = "invalid"

    outcome = service.solve(KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert binary.problem is None
    assert milp.problem is None


def test_production_service_matches_orlib_known_optimum():
    data = load_orlib_mknap(ORLIB_DATASET, 1)
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "multi_dimensional",
        "domain": "zero_one",
        "resources": [
            {"name": f"Resource {index + 1}", "capacity": capacity}
            for index, capacity in enumerate(data["capacities"])
        ],
        "items": [
            {
                "name": f"Item {index + 1}",
                "value": value,
                "usage": data["usage_matrix"][index],
            }
            for index, value in enumerate(data["values"])
        ],
    }

    outcome = create_local_optimization_service().solve(
        KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
        payload,
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["objective"] == pytest.approx(data["known_optimum"])
    assert all(resource["remaining"] >= 0 for resource in outcome.result["resources"])


@pytest.mark.parametrize(
    ("domain", "max_quantity", "expected_quantity", "expected_objective"),
    [
        ("bounded", 2, 2.0, 8.0),
        ("unbounded", None, 5.0, 20.0),
        ("fractional", 2.5, 2.5, 10.0),
    ],
)
def test_production_service_solves_non_binary_domains(
    domain: str,
    max_quantity: float | None,
    expected_quantity: float,
    expected_objective: float,
):
    pytest.importorskip("ortools")
    item = {"name": "A", "value": 4, "usage": [2, 1]}
    if max_quantity is not None:
        item["max_quantity"] = max_quantity
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "multi_dimensional",
        "domain": domain,
        "resources": [
            {"name": "weight", "capacity": 10},
            {"name": "volume", "capacity": 6},
        ],
        "items": [item],
    }

    outcome = create_local_optimization_service().solve(
        KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
        payload,
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["quantities"] == pytest.approx([expected_quantity])
    assert outcome.result["objective"] == pytest.approx(expected_objective)
    assert all(resource["remaining"] >= -1e-8 for resource in outcome.result["resources"])


def test_registry_documents_all_domains_and_backends():
    descriptor = next(
        item
        for item in create_local_optimization_service().list_capabilities()
        if item["id"] == KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == list(
        KNAPSACK_MULTI_DIMENSIONAL_BACKEND_IDS
    )
    assert descriptor["input_schema"]["properties"]["domain"]["enum"] == [
        "zero_one",
        "bounded",
        "unbounded",
        "fractional",
    ]
