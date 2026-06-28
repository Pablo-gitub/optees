from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.utility.milp_json_io import (
    milp_model_from_dict,
    milp_model_from_file,
    milp_model_to_dict,
    milp_model_to_file,
)


ASSIGNMENT = {
    "version": "1",
    "variables": [
        {"name": "x11", "label": "worker 1 -> task 1", "lb": 0, "ub": 1, "integrality": "B"},
        {"name": "x12", "label": "worker 1 -> task 2", "lb": 0, "ub": 1, "integrality": "B"},
        {"name": "flow", "label": "continuous tie-breaker", "lb": 0, "ub": None, "integrality": "C"},
    ],
    "objective": {"sense": "min", "coefficients": [1, 2, 0.5], "offset": 3},
    "constraints": [
        {"coefficients": [1, 1, 0], "relation": "=", "rhs": 1},
        {"coefficients": [1, 0, 1], "relation": "<=", "rhs": 4},
    ],
    "solver": {"time_limit": 7.5, "mip_gap": 0.01},
}


def test_parse_variables_integrality_and_solver_options():
    model = milp_model_from_dict(ASSIGNMENT)

    assert len(model.variables) == 3
    assert model.variables[0].name == "x11"
    assert model.variables[0].integrality is Integrality.BINARY
    assert model.variables[0].bounds.lb == 0.0
    assert model.variables[0].bounds.ub == 1.0
    assert model.variables[2].integrality is Integrality.CONTINUOUS
    assert model.time_limit == pytest.approx(7.5)
    assert model.mip_gap == pytest.approx(0.01)


def test_parse_objective_and_constraints():
    model = milp_model_from_dict(ASSIGNMENT)

    assert model.objective.sense is ObjectiveSense.MIN
    assert model.objective.coefs == (1.0, 2.0, 0.5)
    assert model.objective.offset == pytest.approx(3.0)
    assert model.constraints[0].relation is Relation.EQ
    assert model.constraints[1].relation is Relation.LE


def test_binary_bounds_are_normalized():
    data = {
        **ASSIGNMENT,
        "variables": [{"name": "x", "lb": -10, "ub": 10, "integrality": "binary"}],
        "objective": {"sense": "max", "coefficients": [1]},
        "constraints": [],
    }

    model = milp_model_from_dict(data)

    assert model.variables[0].bounds.lb == 0.0
    assert model.variables[0].bounds.ub == 1.0


def test_missing_integrality_defaults_to_continuous():
    data = {
        **ASSIGNMENT,
        "variables": [{"name": "x", "lb": 0, "ub": None}],
        "objective": {"sense": "max", "coefficients": [1]},
        "constraints": [],
        "solver": {},
    }

    model = milp_model_from_dict(data)

    assert model.variables[0].integrality is Integrality.CONTINUOUS


def test_invalid_integrality_raises():
    data = {
        **ASSIGNMENT,
        "variables": [{"name": "x", "lb": 0, "ub": None, "integrality": "semi"}],
        "objective": {"sense": "max", "coefficients": [1]},
        "constraints": [],
    }

    with pytest.raises(ValueError, match="integrality"):
        milp_model_from_dict(data)


def test_coefficient_length_mismatch_raises():
    data = {
        **ASSIGNMENT,
        "objective": {"sense": "min", "coefficients": [1]},
    }

    with pytest.raises(ValueError, match="coefficients"):
        milp_model_from_dict(data)


def test_roundtrip_preserves_schema():
    model = milp_model_from_dict(ASSIGNMENT)
    restored = milp_model_from_dict(milp_model_to_dict(model))

    assert restored.variables == model.variables
    assert restored.objective == model.objective
    assert restored.constraints == model.constraints
    assert restored.time_limit == model.time_limit
    assert restored.mip_gap == model.mip_gap


def test_file_io_roundtrip(tmp_path: Path):
    model = milp_model_from_dict(ASSIGNMENT)
    path = tmp_path / "assignment.json"

    milp_model_to_file(model, path)
    restored = milp_model_from_file(path)

    assert restored.variables == model.variables
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == "1"


def test_malformed_json_raises(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        milp_model_from_file(path)
