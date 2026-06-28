"""Tests for src/optees/utility/lp_json_io.py."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from optees.utility.lp_json_io import (
    lp_model_from_dict,
    lp_model_to_dict,
    lp_model_from_file,
    lp_model_to_file,
)
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL = {
    "version": "1",
    "variables": [{"lb": 0, "ub": None}],
    "objective": {"sense": "max", "coefficients": [1], "offset": 0},
    "constraints": [],
}

PRODUCTION_MIX = {
    "version": "1",
    "variables": [
        {"name": "X1", "label": "chairs/day", "lb": 0, "ub": None},
        {"name": "X2", "label": "tables/day", "lb": 0, "ub": None},
    ],
    "objective": {
        "sense": "max",
        "coefficients": [30, 50],
        "offset": 0,
    },
    "constraints": [
        {"coefficients": [2, 4], "relation": "<=", "rhs": 80},
        {"coefficients": [1, 1], "relation": "<=", "rhs": 30},
    ],
}


# ---------------------------------------------------------------------------
# Happy-path: parse
# ---------------------------------------------------------------------------

class TestParseHappyPath:
    def test_variable_count(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert len(m.variables) == 2

    def test_variable_name_and_label(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert m.variables[0].name  == "X1"
        assert m.variables[0].label == "chairs/day"

    def test_variable_bounds_finite(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert m.variables[0].bounds.lb == 0.0
        assert m.variables[0].bounds.ub is None

    def test_objective_sense_max(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert m.objective.sense is ObjectiveSense.MAX

    def test_objective_sense_min(self):
        data = {**PRODUCTION_MIX, "objective": {**PRODUCTION_MIX["objective"], "sense": "min"}}
        m = lp_model_from_dict(data)
        assert m.objective.sense is ObjectiveSense.MIN

    def test_objective_coefficients(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert m.objective.coefs == (30.0, 50.0)

    def test_objective_offset(self):
        data = {**PRODUCTION_MIX, "objective": {**PRODUCTION_MIX["objective"], "offset": 5.5}}
        m = lp_model_from_dict(data)
        assert m.objective.offset == pytest.approx(5.5)

    def test_constraint_count(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert len(m.constraints) == 2

    def test_constraint_relation_le(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert m.constraints[0].relation is Relation.LE

    def test_constraint_relation_ge(self):
        data = {**PRODUCTION_MIX, "constraints": [
            {"coefficients": [1, 2], "relation": ">=", "rhs": 5}
        ]}
        m = lp_model_from_dict(data)
        assert m.constraints[0].relation is Relation.GE

    def test_constraint_relation_eq(self):
        data = {**PRODUCTION_MIX, "constraints": [
            {"coefficients": [1, 2], "relation": "=", "rhs": 5}
        ]}
        m = lp_model_from_dict(data)
        assert m.constraints[0].relation is Relation.EQ

    def test_constraint_rhs(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        assert m.constraints[0].rhs == pytest.approx(80.0)

    def test_null_bounds_become_none(self):
        data = {**PRODUCTION_MIX, "variables": [
            {"name": "X1", "lb": None, "ub": None}
        ], "objective": {"sense": "max", "coefficients": [1], "offset": 0},
           "constraints": []}
        m = lp_model_from_dict(data)
        assert m.variables[0].bounds.lb is None
        assert m.variables[0].bounds.ub is None

    def test_missing_name_defaults_to_x_index(self):
        m = lp_model_from_dict(MINIMAL)
        assert m.variables[0].name == "X1"

    def test_missing_label_defaults_to_empty(self):
        m = lp_model_from_dict(MINIMAL)
        assert m.variables[0].label == ""

    def test_missing_offset_defaults_to_zero(self):
        data = {**MINIMAL, "objective": {"sense": "max", "coefficients": [1]}}
        m = lp_model_from_dict(data)
        assert m.objective.offset == 0.0

    def test_empty_constraints_list(self):
        m = lp_model_from_dict(MINIMAL)
        assert len(m.constraints) == 0


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestValidationErrors:
    def test_missing_version_raises(self):
        bad = {k: v for k, v in PRODUCTION_MIX.items() if k != "version"}
        with pytest.raises(ValueError, match="version"):
            lp_model_from_dict(bad)

    def test_wrong_version_raises(self):
        bad = {**PRODUCTION_MIX, "version": "99"}
        with pytest.raises(ValueError, match="version"):
            lp_model_from_dict(bad)

    def test_non_dict_root_raises(self):
        with pytest.raises(ValueError):
            lp_model_from_dict([1, 2, 3])  # type: ignore

    def test_empty_variables_raises(self):
        bad = {**PRODUCTION_MIX, "variables": []}
        with pytest.raises(ValueError, match="variable"):
            lp_model_from_dict(bad)

    def test_variables_not_list_raises(self):
        bad = {**PRODUCTION_MIX, "variables": "X1"}
        with pytest.raises(ValueError):
            lp_model_from_dict(bad)

    def test_invalid_sense_raises(self):
        bad = {**PRODUCTION_MIX, "objective": {**PRODUCTION_MIX["objective"], "sense": "maximize"}}
        with pytest.raises(ValueError, match="sense"):
            lp_model_from_dict(bad)

    def test_coef_length_mismatch_raises(self):
        bad = {**PRODUCTION_MIX, "objective": {**PRODUCTION_MIX["objective"], "coefficients": [1]}}
        with pytest.raises(ValueError, match="coefficients"):
            lp_model_from_dict(bad)

    def test_constraint_coef_length_mismatch_raises(self):
        bad = {**PRODUCTION_MIX, "constraints": [
            {"coefficients": [1], "relation": "<=", "rhs": 10}
        ]}
        with pytest.raises(ValueError, match="coefficients"):
            lp_model_from_dict(bad)

    def test_invalid_relation_raises(self):
        bad = {**PRODUCTION_MIX, "constraints": [
            {"coefficients": [1, 2], "relation": "!=", "rhs": 5}
        ]}
        with pytest.raises(ValueError, match="relation"):
            lp_model_from_dict(bad)

    def test_non_numeric_bound_raises(self):
        bad = {**PRODUCTION_MIX, "variables": [
            {"name": "X1", "lb": "zero", "ub": None},
            {"name": "X2", "lb": 0, "ub": None},
        ]}
        with pytest.raises(ValueError, match="lb"):
            lp_model_from_dict(bad)

    def test_inverted_bounds_raises(self):
        bad = {**PRODUCTION_MIX, "variables": [
            {"name": "X1", "lb": 10, "ub": 5},
            {"name": "X2", "lb": 0, "ub": None},
        ]}
        with pytest.raises(ValueError):
            lp_model_from_dict(bad)


# ---------------------------------------------------------------------------
# Round-trip: to_dict → from_dict
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_production_mix_roundtrip(self):
        original = lp_model_from_dict(PRODUCTION_MIX)
        serialised = lp_model_to_dict(original)
        restored  = lp_model_from_dict(serialised)

        assert len(restored.variables)   == len(original.variables)
        assert len(restored.constraints) == len(original.constraints)
        assert restored.objective.sense  == original.objective.sense
        assert restored.objective.coefs  == original.objective.coefs
        assert restored.objective.offset == original.objective.offset

        for orig_v, rest_v in zip(original.variables, restored.variables):
            assert orig_v.name        == rest_v.name
            assert orig_v.label       == rest_v.label
            assert orig_v.bounds.lb   == rest_v.bounds.lb
            assert orig_v.bounds.ub   == rest_v.bounds.ub

    def test_schema_version_preserved(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        d = lp_model_to_dict(m)
        assert d["version"] == "1"

    def test_serialised_json_is_valid(self):
        m = lp_model_from_dict(PRODUCTION_MIX)
        text = json.dumps(lp_model_to_dict(m))
        parsed = json.loads(text)
        assert parsed["version"] == "1"


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

class TestFileIO:
    def test_write_and_read_file(self, tmp_path: Path):
        m = lp_model_from_dict(PRODUCTION_MIX)
        p = tmp_path / "problem.json"
        lp_model_to_file(m, p)

        restored = lp_model_from_file(p)
        assert len(restored.variables) == len(m.variables)

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Cannot read"):
            lp_model_from_file(tmp_path / "nonexistent.json")

    def test_malformed_json_raises(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            lp_model_from_file(p)
