from __future__ import annotations

import math
from pathlib import Path

import pytest
from scipy.optimize import linprog

from optees.application.contracts.execution import TerminationReason

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "contracts" / "linear-scenario-optimization-contract.md"


def _schema_subset_errors(value: object, schema: dict, path: str = "$") -> list[str]:
    """Validate JSON value against schema subset."""
    errors: list[str] = []
    expected = schema.get("type")
    expected_types = [expected] if isinstance(expected, str) else expected or []
    matches_type = not expected_types or any(
        (
            (kind == "null" and value is None)
            or (kind == "object" and isinstance(value, dict))
            or (kind == "array" and isinstance(value, list))
            or (kind == "string" and isinstance(value, str))
            or (kind == "integer" and isinstance(value, int) and not isinstance(value, bool))
            or (
                kind == "number"
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
            )
            or (kind == "boolean" and isinstance(value, bool))
        )
        for kind in expected_types
    )
    if not matches_type:
        return [f"{path}: wrong type {type(value)} (expected {expected_types})"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: wrong constant (expected {schema['const']!r}, got {value!r})")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: outside enum {schema['enum']!r} (got {value!r})")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than minLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: not strictly greater than exclusiveMinimum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: shorter than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: longer than maxItems")
        for index, item in enumerate(value):
            errors.extend(_schema_subset_errors(item, schema.get("items", {}), f"{path}[{index}]"))
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing {required}")
        for key, item in value.items():
            if key in properties:
                errors.extend(_schema_subset_errors(item, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property {key}")
    return errors


def test_contract_markdown_file_exists() -> None:
    assert CONTRACT_PATH.is_file(), f"Contract file missing at {CONTRACT_PATH}"


def test_contract_uses_existing_execution_envelope_vocabulary() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert {reason.value for reason in TerminationReason} == {
        "completed",
        "time_limit",
        "iteration_limit",
        "cancelled",
        "dependency_failure",
        "internal_error",
    }
    assert '"version": { "const": "1" }' in contract
    assert '"variables": {\n      "type": "array"' in contract
    assert '"delegated_backend"' not in contract
    assert '"numerical_error"' not in contract
    assert '"dependency_missing"' not in contract


def test_example1_min_max_loss_analytical_recomputation() -> None:
    """Verify analytical and numerical derivation of Example 1 (min-max loss with tie)."""
    # Problem: min max(L1, L2, L3) s.t. x1 + x2 = 10, x1 >= 0, x2 >= 0
    # L1 = 2 x1 - x2 + 5 = 3 x1 - 5 (substituting x2 = 10 - x1)
    # L2 = -x1 + 3 x2 + 2 = -4 x1 + 32
    # L3 = x1 + x2 - 4 = 6
    # Intersection 3 x1 - 5 = -4 x1 + 32 => 7 x1 = 37 => x1* = 37/7, x2* = 33/7
    # L1(x*) = L2(x*) = 76/7 approx 10.857143, L3(x*) = 6
    x1_star = 37.0 / 7.0
    x2_star = 33.0 / 7.0
    l_max_star = 76.0 / 7.0

    v1 = 2.0 * x1_star - x2_star + 5.0
    v2 = -1.0 * x1_star + 3.0 * x2_star + 2.0
    v3 = 1.0 * x1_star + 1.0 * x2_star - 4.0

    assert math.isclose(v1, l_max_star, abs_tol=1e-12)
    assert math.isclose(v2, l_max_star, abs_tol=1e-12)
    assert v3 < l_max_star

    # Epigraph LP reduction:
    # min theta s.t. x1 + x2 = 10,
    # 2 x1 - x2 - theta <= -5
    # -x1 + 3 x2 - theta <= -2
    # x1 + x2 - theta <= 4
    # x1 >= 0, x2 >= 0, theta in R
    c = [0.0, 0.0, 1.0]
    A_ub = [
        [2.0, -1.0, -1.0],
        [-1.0, 3.0, -1.0],
        [1.0, 1.0, -1.0],
    ]
    b_ub = [-5.0, -2.0, 4.0]
    A_eq = [[1.0, 1.0, 0.0]]
    b_eq = [10.0]
    bounds = [(0.0, None), (0.0, None), (None, None)]

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    assert res.success
    assert math.isclose(res.x[0], x1_star, abs_tol=1e-8)
    assert math.isclose(res.x[1], x2_star, abs_tol=1e-8)
    assert math.isclose(res.fun, l_max_star, abs_tol=1e-8)


def test_example2_max_min_reward_analytical_recomputation() -> None:
    """Verify analytical and numerical derivation of Example 2 (max-min reward, negative values)."""
    # Problem: max min(RA, RB, RC) s.t. x1 + x2 <= 6, 0 <= x1 <= 4, 0 <= x2 <= 4
    # RA = 4 x1 - 2 x2 - 10
    # RB = -2 x1 + 5 x2 - 8
    # RC = x1 + x2 - 5
    # Setting RA = RB on boundary x1 + x2 = 6:
    # 4 x1 - 2(6 - x1) - 10 = -2 x1 + 5(6 - x1) - 8
    # 6 x1 - 22 = -7 x1 + 22 => 13 x1 = 44 => x1* = 44/13, x2* = 34/13
    # RA(x*) = RB(x*) = -22/13 approx -1.692308
    # RC(x*) = 6 - 5 = 1.0 > -22/13
    x1_star = 44.0 / 13.0
    x2_star = 34.0 / 13.0
    r_min_star = -22.0 / 13.0

    va = 4.0 * x1_star - 2.0 * x2_star - 10.0
    vb = -2.0 * x1_star + 5.0 * x2_star - 8.0
    vc = 1.0 * x1_star + 1.0 * x2_star - 5.0

    assert math.isclose(va, r_min_star, abs_tol=1e-12)
    assert math.isclose(vb, r_min_star, abs_tol=1e-12)
    assert vc > r_min_star

    # Hypograph LP reduction:
    # max tau <=> min -tau
    # -4 x1 + 2 x2 + tau <= -10
    # 2 x1 - 5 x2 + tau <= -8
    # -x1 - x2 + tau <= -5
    # x1 + x2 <= 6, 0 <= x1 <= 4, 0 <= x2 <= 4, tau in R
    c = [0.0, 0.0, -1.0]
    A_ub = [
        [1.0, 1.0, 0.0],
        [-4.0, 2.0, 1.0],
        [2.0, -5.0, 1.0],
        [-1.0, -1.0, 1.0],
    ]
    b_ub = [6.0, -10.0, -8.0, -5.0]
    bounds = [(0.0, 4.0), (0.0, 4.0), (None, None)]

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    assert res.success
    assert math.isclose(res.x[0], x1_star, abs_tol=1e-8)
    assert math.isclose(res.x[1], x2_star, abs_tol=1e-8)
    assert math.isclose(-res.fun, r_min_star, abs_tol=1e-8)


def test_example3_discrete_binary_analytical_recomputation() -> None:
    """Verify analytical derivation of Example 3 (binary min-max loss with 3 items)."""
    # 3 binary variables, sum(x) = 2
    # Combinations: (1,1,0)->max(12,15,11)=15; (1,0,1)->max(18,7,15)=18; (0,1,1)->max(10,16,14)=16
    from ortools.linear_solver import pywraplp

    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        pytest.skip("OR-Tools CBC solver not available")

    x1 = solver.IntVar(0, 1, "x1")
    x2 = solver.IntVar(0, 1, "x2")
    x3 = solver.IntVar(0, 1, "x3")
    theta = solver.NumVar(-1e9, 1e9, "theta")

    solver.Add(x1 + x2 + x3 == 2)
    solver.Add(10 * x1 + 2 * x2 + 8 * x3 - theta <= 0)
    solver.Add(3 * x1 + 12 * x2 + 4 * x3 - theta <= 0)
    solver.Add(6 * x1 + 5 * x2 + 9 * x3 - theta <= 0)

    solver.Minimize(theta)
    status = solver.Solve()

    assert status == pywraplp.Solver.OPTIMAL
    assert math.isclose(x1.solution_value(), 1.0, abs_tol=1e-6)
    assert math.isclose(x2.solution_value(), 1.0, abs_tol=1e-6)
    assert math.isclose(x3.solution_value(), 0.0, abs_tol=1e-6)
    assert math.isclose(theta.solution_value(), 15.0, abs_tol=1e-6)


def test_canonical_problem_json_schema_validation() -> None:
    """Verify that canonical problem examples validate against the contract problem schema."""
    problem_schema = {
        "type": "object",
        "required": [
            "version",
            "problem_type",
            "orientation",
            "variables",
            "scenarios",
        ],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "linear_scenario"},
            "orientation": {
                "enum": [
                    "minimize_maximum_loss",
                    "maximize_minimum_reward",
                ]
            },
            "variables": {
                "type": "array",
                "minItems": 1,
                "maxItems": 500,
                "items": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "label": {"type": "string"},
                        "lower_bound": {"type": ["number", "null"]},
                        "upper_bound": {"type": ["number", "null"]},
                        "integrality": {
                            "enum": ["C", "I", "B"],
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "scenarios": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2000,
                "items": {
                    "type": "object",
                    "required": ["id", "coefficients"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "label": {"type": "string"},
                        "coefficients": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 500,
                            "items": {"type": "number"},
                        },
                        "offset": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
            },
            "shared_constraints": {
                "type": "array",
                "maxItems": 1000,
                "items": {
                    "type": "object",
                    "required": ["coefficients", "relation", "rhs"],
                    "properties": {
                        "name": {"type": "string"},
                        "coefficients": {
                            "type": "array",
                            "items": {"type": "number"},
                        },
                        "relation": {"enum": ["<=", "=", ">="]},
                        "rhs": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
            },
            "options": {
                "type": "object",
                "properties": {
                    "tolerance": {"type": "number", "exclusiveMinimum": 0},
                    "binding_tolerance": {"type": "number", "exclusiveMinimum": 0},
                    "time_limit_seconds": {"type": "number", "exclusiveMinimum": 0},
                },
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    }

    example_min_max = {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "minimize_maximum_loss",
        "variables": [
            {
                "name": "x1",
                "label": "Resource allocation 1",
                "lower_bound": 0.0,
                "upper_bound": None,
                "integrality": "C",
            },
            {
                "name": "x2",
                "label": "Resource allocation 2",
                "lower_bound": 0.0,
                "upper_bound": None,
                "integrality": "C",
            },
        ],
        "scenarios": [
            {"id": "s1", "label": "High-demand regime", "coefficients": [2.0, -1.0], "offset": 5.0},
            {"id": "s2", "label": "Low-demand regime", "coefficients": [-1.0, 3.0], "offset": 2.0},
            {"id": "s3", "label": "Baseline regime", "coefficients": [1.0, 1.0], "offset": -4.0},
        ],
        "shared_constraints": [
            {"name": "total_budget", "coefficients": [1.0, 1.0], "relation": "=", "rhs": 10.0}
        ],
        "options": {
            "tolerance": 1e-7,
            "binding_tolerance": 1e-6,
        },
    }

    errors = _schema_subset_errors(example_min_max, problem_schema)
    assert errors == [], f"Validation errors on min-max example: {errors}"


def test_canonical_result_json_schema_validation() -> None:
    """Verify that canonical result examples validate against the contract result schema."""
    result_schema = {
        "type": "object",
        "required": [
            "orientation",
            "guaranteed_value",
            "variables",
            "scenario_values",
            "binding_scenario_ids",
        ],
        "properties": {
            "orientation": {
                "enum": [
                    "minimize_maximum_loss",
                    "maximize_minimum_reward",
                ]
            },
            "guaranteed_value": {"type": ["number", "null"]},
            "variables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "value": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
            },
            "scenario_values": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["scenario_id", "value", "is_binding"],
                    "properties": {
                        "scenario_id": {"type": "string"},
                        "value": {"type": "number"},
                        "is_binding": {"type": "boolean"},
                    },
                    "additionalProperties": False,
                },
            },
            "binding_scenario_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    }

    example_result = {
        "orientation": "minimize_maximum_loss",
        "guaranteed_value": 10.857142857142858,
        "variables": [
            {"name": "x1", "value": 5.285714285714286},
            {"name": "x2", "value": 4.714285714285714},
        ],
        "scenario_values": [
            {"scenario_id": "s1", "value": 10.857142857142858, "is_binding": True},
            {"scenario_id": "s2", "value": 10.857142857142858, "is_binding": True},
            {"scenario_id": "s3", "value": 6.0, "is_binding": False},
        ],
        "binding_scenario_ids": ["s1", "s2"],
    }

    errors = _schema_subset_errors(example_result, result_schema)
    assert errors == [], f"Validation errors on result example: {errors}"
