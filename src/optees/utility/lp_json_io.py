"""
lp_json_io.py — JSON import / export for LP problems.

Schema v1
---------
{
  "version": "1",
  "variables": [
    {"name": "X1", "label": "chairs/day", "lb": 0, "ub": null}
  ],
  "objective": {
    "sense": "max",
    "coefficients": [30, 50],
    "offset": 0
  },
  "constraints": [
    {"coefficients": [2, 4], "relation": "<=", "rhs": 80}
  ]
}

null  → unbounded (−∞ for lb, +∞ for ub)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.lp.variable import Variable
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation

_SUPPORTED_VERSIONS = {"1"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lp_model_from_dict(data: dict) -> LPModel:
    """
    Parse a schema-v1 dict into an immutable LPModel.
    Raises ValueError with a human-readable message on any validation error.
    """
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object.")

    version = str(data.get("version", ""))
    if version not in _SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported schema version '{version}'. "
            f"Supported: {sorted(_SUPPORTED_VERSIONS)}."
        )

    variables  = _parse_variables(data)
    n          = len(variables)
    objective  = _parse_objective(data, n)
    constraints = _parse_constraints(data, n)

    return LPModel(
        variables=tuple(variables),
        objective=objective,
        constraints=tuple(constraints),
    )


def lp_model_to_dict(model: LPModel) -> dict:
    """Serialise an LPModel to a schema-v1 dict (JSON-ready)."""
    return {
        "version": "1",
        "variables": [
            {
                "name":  v.name,
                "label": v.label,
                "lb":    v.bounds.lb,
                "ub":    v.bounds.ub,
            }
            for v in model.variables
        ],
        "objective": {
            "sense":        model.objective.sense.value,
            "coefficients": list(model.objective.coefs),
            "offset":       model.objective.offset,
        },
        "constraints": [
            {
                "coefficients": list(c.coefs),
                "relation":     c.relation.symbol(),
                "rhs":          c.rhs,
            }
            for c in model.constraints
        ],
    }


def lp_model_from_file(path: str | Path) -> LPModel:
    """Load an LPModel from a JSON file on disk."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read file: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    return lp_model_from_dict(data)


def lp_model_to_file(model: LPModel, path: str | Path) -> None:
    """Write an LPModel to a JSON file on disk."""
    Path(path).write_text(
        json.dumps(lp_model_to_dict(model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------

def _parse_variables(data: dict) -> list[Variable]:
    raw = data.get("variables")
    if not isinstance(raw, list):
        raise ValueError("'variables' must be a JSON array.")
    if len(raw) == 0:
        raise ValueError("'variables' must contain at least one entry.")

    variables: list[Variable] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"variables[{i}] must be a JSON object.")

        name  = item.get("name") or f"X{i + 1}"
        label = item.get("label") or ""
        lb    = _parse_optional_float(item, "lb",  context=f"variables[{i}].lb")
        ub    = _parse_optional_float(item, "ub",  context=f"variables[{i}].ub")

        try:
            bounds = Bounds(lb, ub)
        except ValueError as exc:
            raise ValueError(f"variables[{i}]: {exc}") from exc

        variables.append(Variable(name=str(name), label=str(label), bounds=bounds))

    return variables


def _parse_objective(data: dict, n: int) -> Objective:
    raw = data.get("objective")
    if not isinstance(raw, dict):
        raise ValueError("'objective' must be a JSON object.")

    # sense
    sense_str = raw.get("sense", "")
    try:
        sense = ObjectiveSense.from_str(str(sense_str))
    except ValueError:
        raise ValueError(
            f"objective.sense must be 'min' or 'max', got '{sense_str}'."
        )

    # coefficients
    coef_raw = raw.get("coefficients")
    if not isinstance(coef_raw, list):
        raise ValueError("objective.coefficients must be a JSON array.")
    if len(coef_raw) != n:
        raise ValueError(
            f"objective.coefficients has {len(coef_raw)} entries "
            f"but there are {n} variables."
        )
    coefs = tuple(
        _parse_optional_float({"v": c}, "v", context=f"objective.coefficients[{i}]")
        for i, c in enumerate(coef_raw)
    )

    # offset (optional)
    offset_raw = raw.get("offset", 0)
    try:
        offset = float(offset_raw) if offset_raw is not None else 0.0
    except (TypeError, ValueError):
        raise ValueError(f"objective.offset must be a number, got '{offset_raw}'.")

    return Objective(sense=sense, coefs=coefs, offset=offset)


def _parse_constraints(data: dict, n: int) -> list[Constraint]:
    raw = data.get("constraints", [])
    if not isinstance(raw, list):
        raise ValueError("'constraints' must be a JSON array.")

    constraints: list[Constraint] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"constraints[{i}] must be a JSON object.")

        # coefficients
        coef_raw = item.get("coefficients")
        if not isinstance(coef_raw, list):
            raise ValueError(f"constraints[{i}].coefficients must be a JSON array.")
        if len(coef_raw) != n:
            raise ValueError(
                f"constraints[{i}].coefficients has {len(coef_raw)} entries "
                f"but there are {n} variables."
            )
        coefs = tuple(
            _parse_optional_float(
                {"v": c}, "v", context=f"constraints[{i}].coefficients[{j}]"
            )
            for j, c in enumerate(coef_raw)
        )

        # relation
        rel_str = item.get("relation", "")
        try:
            relation = Relation.from_symbol(str(rel_str))
        except ValueError:
            raise ValueError(
                f"constraints[{i}].relation must be '<=', '=', or '>=',"
                f" got '{rel_str}'."
            )

        # rhs
        rhs = _parse_optional_float(item, "rhs", context=f"constraints[{i}].rhs")
        constraints.append(Constraint(coefs=coefs, relation=relation, rhs=rhs))

    return constraints


def _parse_optional_float(
    obj: dict, key: str, *, context: str
) -> float | None:
    """Return float or None; raise ValueError on non-numeric values."""
    val: Any = obj.get(key, None)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        raise ValueError(f"{context} must be a number or null, got '{val}'.")
