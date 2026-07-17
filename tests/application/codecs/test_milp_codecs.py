from __future__ import annotations

import json

import pytest

from optees.application.codecs.milp_problem_codec import (
    milp_model_from_public_dict,
)
from optees.application.codecs.milp_result_codec import MILPResultCodec
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.value_objects.milp.integrality import Integrality


def _payload() -> dict:
    return {
        "version": "1",
        "variables": [
            {"name": "x", "label": "units", "lb": 0, "ub": 4, "integrality": "I"},
            {"name": "open", "label": "setup", "lb": 0, "ub": 1, "integrality": "B"},
        ],
        "objective": {"sense": "max", "coefficients": [3, -1], "offset": 2},
        "constraints": [
            {"coefficients": [1, -4], "relation": "<=", "rhs": 0},
        ],
        "solver": {"time_limit": 10, "mip_gap": 0.01},
    }


def test_problem_codec_preserves_integrality_bounds_and_solver_options():
    model = milp_model_from_public_dict(_payload())

    assert model.variables[0].integrality is Integrality.INTEGER
    assert model.variables[1].integrality is Integrality.BINARY
    assert (model.variables[1].bounds.lb, model.variables[1].bounds.ub) == (0.0, 1.0)
    assert model.objective.offset == pytest.approx(2.0)
    assert model.time_limit == pytest.approx(10.0)
    assert model.mip_gap == pytest.approx(0.01)


def test_problem_codec_requires_explicit_public_sections():
    payload = _payload()
    del payload["constraints"]

    with pytest.raises(ValueError, match="missing required fields: constraints"):
        milp_model_from_public_dict(payload)


def test_problem_codec_rejects_duplicate_variable_names():
    payload = _payload()
    payload["variables"][1]["name"] = "x"

    with pytest.raises(ValueError, match="variable names must be unique"):
        milp_model_from_public_dict(payload)


def test_problem_codec_rejects_non_finite_numbers_and_invalid_options():
    payload = _payload()
    payload["objective"]["offset"] = "nan"
    with pytest.raises(ValueError, match="objective.offset must be finite"):
        milp_model_from_public_dict(payload)

    payload = _payload()
    payload["solver"]["time_limit"] = 0
    with pytest.raises(ValueError, match="time_limit must be positive"):
        milp_model_from_public_dict(payload)


def test_result_codec_serializes_feasible_incumbent_and_gap():
    solution = MILPSolution.from_utility_tuple(
        "Feasible",
        11,
        {"x": 4, "open": 1},
        {
            "backend": "cbc",
            "best_bound": 12,
            "relative_gap": 1 / 12,
            "wall_time_ms": 15,
            "nodes": 3,
            "success": True,
        },
    )

    serialized = MILPResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "feasible"
    assert serialized.result == {
        "objective": 11.0,
        "variables": [
            {"name": "x", "value": 4.0},
            {"name": "open", "value": 1.0},
        ],
    }
    assert serialized.diagnostics["best_bound"] == pytest.approx(12.0)
    assert serialized.diagnostics["relative_gap"] == pytest.approx(1 / 12)
    assert "without proving" in serialized.warnings[0]


def test_result_codec_emits_strict_json_for_unbounded_diagnostics():
    solution = MILPSolution.from_utility_tuple(
        "Unbounded",
        None,
        {},
        {"backend": "cbc", "best_bound": float("inf")},
    )

    serialized = MILPResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "unbounded"
    assert serialized.result["objective"] is None
    assert serialized.diagnostics["best_bound"] is None
    json.dumps(serialized.diagnostics, allow_nan=False)


def test_result_codec_preserves_time_limit_with_feasible_incumbent():
    solution = MILPSolution.from_utility_tuple(
        "Feasible",
        11,
        {"x": 4, "open": 1},
        {"backend": "cbc", "termination_reason": "time_limit"},
    )

    serialized = MILPResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "feasible"
    assert serialized.termination_reason.value == "time_limit"
