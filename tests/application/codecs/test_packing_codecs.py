from __future__ import annotations

import json

import pytest

from optees.application.codecs.packing_problem_codec import (
    packing_model_from_public_dict,
)
from optees.application.codecs.packing_result_codec import PackingResultCodec
from optees.domain.entities.packing.solution import PackingSolution, PackingSolveResult


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": "optional",
        "gravity_mode": "simple",
        "container": {
            "id": "truck-1",
            "name": "Truck",
            "dimensions": {"length": 10, "width": 8, "height": 6},
            "capacities": [{"name": "weight", "limit": 30}],
        },
        "items": [
            {
                "id": "part",
                "name": "Machine part",
                "dimensions": {"length": 6, "width": 4, "height": 3},
                "value": 12,
                "quantity": 2,
                "rotation_policy": "custom",
                "allowed_orientations": ["LWH", "WLH"],
                "consumptions": [{"name": "weight", "amount": 8}],
            }
        ],
        "solver_options": {"time_limit": 20, "mip_gap": 0.05},
    }


def _raw_solution(status: str = "Optimal") -> dict:
    return {
        "status": status,
        "objective": 12,
        "placements": [
            {
                "instance_id": "part#1",
                "item_id": "part",
                "item_name": "Machine part",
                "unit_index": 1,
                "orientation_code": "LWH",
                "x": 0,
                "y": 0,
                "z": 0,
                "length": 6,
                "width": 4,
                "height": 3,
                "value": 12,
            }
        ],
        "excluded_instance_ids": ["part#2"],
        "extras": {
            "backend": "SCIP",
            "result_status": 0,
            "best_bound": 12,
            "relative_gap": 0,
            "wall_time_ms": 4,
            "nodes": 1,
            "solve_role": "requested",
            "gravity_mode": "simple",
            "variable_count": 18,
            "constraint_count": 25,
        },
    }


def test_problem_codec_preserves_geometry_resources_rotations_and_limits():
    model = packing_model_from_public_dict(_payload())

    assert model.container.dimensions.as_tuple() == pytest.approx((10, 8, 6))
    assert model.container.capacity("weight") == pytest.approx(30)
    assert model.items[0].quantity == 2
    assert [orientation.code for orientation in model.items[0].orientations()] == [
        "LWH",
        "WLH",
    ]
    assert model.items[0].consumption("weight") == pytest.approx(8)
    assert model.time_limit == pytest.approx(20)
    assert model.mip_gap == pytest.approx(0.05)


def test_problem_codec_requires_explicit_public_contract_fields():
    payload = _payload()
    del payload["gravity_mode"]

    with pytest.raises(ValueError, match="missing required fields: gravity_mode"):
        packing_model_from_public_dict(payload)


def test_problem_codec_rejects_invalid_numbers_and_unknown_resources():
    payload = _payload()
    payload["container"]["dimensions"]["length"] = float("inf")
    with pytest.raises(ValueError, match="finite positive"):
        packing_model_from_public_dict(payload)

    payload = _payload()
    payload["items"][0]["consumptions"][0]["name"] = "volume"
    with pytest.raises(ValueError, match="resources absent from the container"):
        packing_model_from_public_dict(payload)


def test_result_codec_serializes_placements_and_diagnostics_as_strict_json():
    solution = PackingSolution.from_solver_result(_raw_solution())

    serialized = PackingResultCodec().serialize(PackingSolveResult(solution))

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result["requested"]["placements"][0]["position"] == {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
    }
    assert serialized.result["requested"]["excluded_instance_ids"] == ["part#2"]
    assert serialized.diagnostics["requested"]["backend"] == "SCIP"
    json.dumps(serialized.result, allow_nan=False)
    json.dumps(serialized.diagnostics, allow_nan=False)


def test_result_codec_keeps_infeasible_request_separate_from_feasible_recovery():
    requested = PackingSolution.from_solver_result(
        {
            "status": "Infeasible",
            "objective": None,
            "placements": [],
            "excluded_instance_ids": [],
            "extras": {"backend": "SCIP", "solve_role": "requested"},
        }
    )
    recovery_raw = _raw_solution("Feasible")
    recovery_raw["extras"]["solve_role"] = "maximum_feasible_recovery"
    recovery = PackingSolution.from_solver_result(recovery_raw)

    serialized = PackingResultCodec().serialize(
        PackingSolveResult(requested=requested, recovery=recovery)
    )

    assert serialized.mathematical_status.value == "infeasible"
    assert serialized.result["requested"]["placements"] == []
    assert serialized.result["recovery"]["placements"][0]["instance_id"] == "part#1"
    assert "recovery" in serialized.warnings[0]


def test_result_codec_sanitizes_non_finite_optional_diagnostics():
    raw = _raw_solution()
    raw["extras"]["best_bound"] = float("inf")
    raw["extras"]["relative_gap"] = float("nan")

    serialized = PackingResultCodec().serialize(
        PackingSolveResult(PackingSolution.from_solver_result(raw))
    )

    assert serialized.diagnostics["requested"]["best_bound"] is None
    assert serialized.diagnostics["requested"]["relative_gap"] is None
    json.dumps(serialized.diagnostics, allow_nan=False)
