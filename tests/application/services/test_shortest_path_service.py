from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    DIJKSTRA_BACKEND_ID,
    DIJKSTRA_CAPABILITY_ID,
    create_dijkstra_optimization_service,
    create_local_optimization_service,
)


ROOT = Path(__file__).resolve().parents[3]


class RecordingShortestPathSolver:
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "PathFound",
            "distance": 3,
            "path": ["A", "B"],
            "extras": {
                "settled_order": ["A", "B"],
                "settled_distances": {"A": 0, "B": 3},
            },
        }


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "shortest_path",
        "directed": True,
        "vertices": [{"id": "A"}, {"id": "B"}],
        "edges": [{"from": "A", "to": "B", "weight": 3}],
        "source": "A",
        "destination": "B",
    }


def test_dijkstra_capability_maps_public_contract_through_solver_port():
    solver = RecordingShortestPathSolver()
    service = create_dijkstra_optimization_service(solver_port=solver)

    outcome = service.solve(DIJKSTRA_CAPABILITY_ID, _payload())

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result == {"distance": 3.0, "path": ["A", "B"], "hop_count": 1}
    assert solver.problem == {
        "vertices": ["A", "B"],
        "edges": [{"source": "A", "target": "B", "weight": 3.0}],
        "source": "A",
        "destination": "B",
        "directed": True,
    }
    assert outcome.diagnostics["backend_id"] == DIJKSTRA_BACKEND_ID


def test_invalid_payload_is_rejected_before_solver_call():
    solver = RecordingShortestPathSolver()
    service = create_dijkstra_optimization_service(solver_port=solver)
    payload = _payload()
    payload["edges"][0]["weight"] = -1

    outcome = service.solve(DIJKSTRA_CAPABILITY_ID, payload)

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert solver.problem is None


def test_production_service_solves_documented_delivery_example():
    payload = json.loads(
        (ROOT / "examples" / "shortest_path_delivery.json").read_text(
            encoding="utf-8"
        )
    )

    outcome = create_local_optimization_service().solve(
        DIJKSTRA_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["distance"] == pytest.approx(4.0)
    assert outcome.result["path"] == ["A", "C", "B", "D"]


def test_production_service_honours_undirected_edges():
    payload = _payload()
    payload["directed"] = False
    payload["source"] = "B"
    payload["destination"] = "A"

    outcome = create_local_optimization_service().solve(
        DIJKSTRA_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.result["path"] == ["B", "A"]
    assert outcome.result["distance"] == pytest.approx(3.0)


def test_production_service_preserves_unreachable_status():
    payload = _payload()
    payload["edges"] = []

    outcome = create_local_optimization_service().solve(
        DIJKSTRA_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "infeasible"
    assert outcome.result == {"distance": None, "path": [], "hop_count": 0}


def test_registry_documents_dijkstra_backend_and_contract():
    descriptor = next(
        item
        for item in create_local_optimization_service().list_capabilities()
        if item["id"] == DIJKSTRA_CAPABILITY_ID
    )

    assert descriptor["available"] is True
    assert descriptor["backend_candidates"] == [DIJKSTRA_BACKEND_ID]
    assert descriptor["supports_time_limit"] is False
    assert descriptor["input_schema"]["required"] == [
        "version",
        "problem_type",
        "directed",
        "vertices",
        "edges",
        "source",
        "destination",
    ]
