from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    PACKING_BACKEND_IDS,
    PACKING_CAPABILITY_ID,
    PACKING_ROUTER_ID,
    create_local_optimization_service,
    create_packing_optimization_service,
)
from optees.utility.orlib_thpack_io import read_orlib_thpack


ROOT = Path(__file__).resolve().parents[3]
ORLIB_DATA = ROOT / "tests" / "data" / "packing" / "orlib" / "thpack1.txt"


class RecordingPackingSolver:
    def __init__(self, responses: list[dict] | None = None) -> None:
        self.responses = responses or [_optimal_response()]
        self.problems: list[dict] = []

    def solve(self, problem):
        self.problems.append(problem)
        return self.responses[len(self.problems) - 1]


def _payload(*, selection_policy: str = "optional") -> dict:
    return {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": selection_policy,
        "gravity_mode": "simple",
        "container": {
            "id": "container-1",
            "name": "Container",
            "dimensions": {"length": 4, "width": 3, "height": 2},
            "capacities": [{"name": "weight", "limit": 20}],
        },
        "items": [
            {
                "id": "box",
                "name": "Box",
                "dimensions": {"length": 2, "width": 3, "height": 2},
                "value": 5,
                "quantity": 2,
                "rotation_policy": "fixed",
                "allowed_orientations": [],
                "consumptions": [{"name": "weight", "amount": 4}],
            }
        ],
        "solver_options": {"time_limit": 10, "mip_gap": 0.01},
    }


def _optimal_response() -> dict:
    return {
        "status": "Optimal",
        "objective": 10,
        "placements": [
            {
                "instance_id": f"box#{unit}",
                "item_id": "box",
                "item_name": "Box",
                "unit_index": unit,
                "orientation_code": "LWH",
                "x": 2 * (unit - 1),
                "y": 0,
                "z": 0,
                "length": 2,
                "width": 3,
                "height": 2,
                "value": 5,
            }
            for unit in (1, 2)
        ],
        "excluded_instance_ids": [],
        "extras": {"backend": "SCIP", "solve_role": "requested"},
    }


def test_packing_service_maps_public_contract_to_expanded_solver_problem():
    solver = RecordingPackingSolver()

    outcome = create_packing_optimization_service(solver_port=solver).solve(
        PACKING_CAPABILITY_ID, _payload()
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["requested"]["total_value"] == pytest.approx(10)
    problem = solver.problems[0]
    assert problem["container"]["dimensions"] == [4.0, 3.0, 2.0]
    assert problem["container"]["capacities"] == {"weight": 20.0}
    assert [item["instance_id"] for item in problem["items"]] == [
        "box#1",
        "box#2",
    ]
    assert problem["items"][0]["orientations"] == [
        {"code": "LWH", "dimensions": [2.0, 3.0, 2.0]}
    ]
    assert problem["time_limit"] == pytest.approx(10)
    assert problem["mip_gap"] == pytest.approx(0.01)
    assert outcome.diagnostics["backend_id"] == PACKING_ROUTER_ID


def test_invalid_payload_is_rejected_before_packing_solver_call():
    solver = RecordingPackingSolver()
    payload = _payload()
    payload["items"][0]["quantity"] = 0

    outcome = create_packing_optimization_service(solver_port=solver).solve(
        PACKING_CAPABILITY_ID, payload
    )

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.VALIDATION_FAILED
    assert solver.problems == []


def test_unavailable_ortools_is_reported_before_packing_solver_call():
    solver = RecordingPackingSolver()

    outcome = create_packing_optimization_service(
        solver_port=solver,
        dependency_available=False,
    ).solve(PACKING_CAPABILITY_ID, _payload())

    assert isinstance(outcome, StructuredError)
    assert outcome.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert solver.problems == []


def test_all_required_infeasibility_preserves_separate_recovery_result():
    solver = RecordingPackingSolver(
        [
            {
                "status": "Infeasible",
                "objective": None,
                "placements": [],
                "excluded_instance_ids": [],
                "extras": {"backend": "SCIP", "solve_role": "requested"},
            },
            _optimal_response(),
        ]
    )

    outcome = create_packing_optimization_service(solver_port=solver).solve(
        PACKING_CAPABILITY_ID, _payload(selection_policy="all_required")
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "infeasible"
    assert outcome.result["requested"]["placements"] == []
    assert len(outcome.result["recovery"]["placements"]) == 2
    assert solver.problems[0]["all_items_required"] is True
    assert solver.problems[1]["all_items_required"] is False
    assert solver.problems[1]["solve_role"] == "maximum_feasible_recovery"


def test_production_service_solves_small_orthogonal_packing():
    pytest.importorskip("ortools")

    outcome = create_local_optimization_service().solve(
        PACKING_CAPABILITY_ID, _payload(selection_policy="all_required")
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert len(outcome.result["requested"]["placements"]) == 2
    assert outcome.result["requested"]["excluded_instance_ids"] == []


def test_public_service_matches_orlib_thpack1_two_copy_reference_subset():
    pytest.importorskip("ortools")
    source = read_orlib_thpack(ORLIB_DATA)[0]
    box = source.box_types[0]
    box_volume = box.dimensions[0] * box.dimensions[1] * box.dimensions[2]
    payload = _payload(selection_policy="all_required")
    payload["container"]["dimensions"] = dict(
        zip(("length", "width", "height"), source.container_dimensions, strict=True)
    )
    payload["container"]["capacities"] = []
    payload["items"] = [
        {
            "id": "type-1",
            "name": "Published type 1 (two-copy CI subset)",
            "dimensions": dict(
                zip(("length", "width", "height"), box.dimensions, strict=True)
            ),
            "value": box_volume,
            "quantity": 2,
            "rotation_policy": "fixed",
            "allowed_orientations": [],
            "consumptions": [],
        }
    ]

    outcome = create_local_optimization_service().solve(PACKING_CAPABILITY_ID, payload)

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.mathematical_status.value == "optimal"
    assert outcome.result["requested"]["objective"] == pytest.approx(2 * box_volume)
    assert len(outcome.result["requested"]["placements"]) == 2


def test_registry_documents_packing_backends_and_current_execution_controls():
    descriptor = next(
        item
        for item in create_local_optimization_service().list_capabilities()
        if item["id"] == PACKING_CAPABILITY_ID
    )

    assert descriptor["backend_candidates"] == list(PACKING_BACKEND_IDS)
    assert descriptor["supports_time_limit"] is True
    assert descriptor["supports_cancellation"] is False
    assert descriptor["input_schema"]["properties"]["gravity_mode"] == {
        "enum": ["none", "simple"]
    }
