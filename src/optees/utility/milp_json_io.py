"""
milp_json_io.py - JSON import/export for MILP problems.

Schema v1 extends LP JSON with an `integrality` token per variable:

{
  "version": "1",
  "variables": [
    {"name": "x1", "label": "open plant", "lb": 0, "ub": 1, "integrality": "B"}
  ],
  "objective": {"sense": "min", "coefficients": [100], "offset": 0},
  "constraints": [
    {"coefficients": [1], "relation": "<=", "rhs": 1}
  ],
  "solver": {"time_limit": 10.0, "mip_gap": 0.01}
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality

_SUPPORTED_VERSIONS = {"1"}


def milp_model_from_dict(data: dict) -> MILPModel:
    """Parse a schema-v1 dict into an immutable MILPModel."""
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object.")

    version = str(data.get("version", ""))
    if version not in _SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported schema version '{version}'. "
            f"Supported: {sorted(_SUPPORTED_VERSIONS)}."
        )

    variables = _parse_variables(data)
    n = len(variables)
    objective = _parse_objective(data, n)
    constraints = _parse_constraints(data, n)
    time_limit, mip_gap = _parse_solver_options(data)

    return MILPModel.from_parts(
        variables,
        objective,
        constraints,
        time_limit=time_limit,
        mip_gap=mip_gap,
    )


def milp_model_to_dict(model: MILPModel) -> dict:
    """Serialise a MILPModel to a schema-v1 JSON-ready dict."""
    data = {
        "version": "1",
        "variables": [
            {
                "name": v.name,
                "label": v.label,
                "lb": v.bounds.lb,
                "ub": v.bounds.ub,
                "integrality": v.integrality.value,
            }
            for v in model.variables
        ],
        "objective": {
            "sense": model.objective.sense.value,
            "coefficients": list(model.objective.coefs),
            "offset": model.objective.offset,
        },
        "constraints": [
            {
                "coefficients": list(c.coefs),
                "relation": c.relation.symbol(),
                "rhs": c.rhs,
            }
            for c in model.constraints
        ],
    }
    solver: dict[str, float] = {}
    if model.time_limit is not None:
        solver["time_limit"] = float(model.time_limit)
    if model.mip_gap is not None:
        solver["mip_gap"] = float(model.mip_gap)
    if solver:
        data["solver"] = solver
    return data


def milp_model_from_file(path: str | Path) -> MILPModel:
    """Load a MILPModel from a JSON file on disk."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read file: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    return milp_model_from_dict(data)


def milp_model_to_file(model: MILPModel, path: str | Path) -> None:
    """Write a MILPModel to a JSON file on disk."""
    Path(path).write_text(
        json.dumps(milp_model_to_dict(model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _parse_variables(data: dict) -> list[MILPVariable]:
    raw = data.get("variables")
    if not isinstance(raw, list):
        raise ValueError("'variables' must be a JSON array.")
    if not raw:
        raise ValueError("'variables' must contain at least one entry.")

    variables: list[MILPVariable] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"variables[{i}] must be a JSON object.")

        name = item.get("name") or f"X{i + 1}"
        label = item.get("label") or ""
        try:
            integrality = Integrality.from_token(item.get("integrality", "C"))
        except ValueError as exc:
            raise ValueError(f"variables[{i}].integrality: {exc}") from exc

        lb = _parse_optional_float(item, "lb", context=f"variables[{i}].lb")
        ub = _parse_optional_float(item, "ub", context=f"variables[{i}].ub")
        if integrality is Integrality.BINARY:
            lb, ub = 0.0, 1.0

        try:
            bounds = Bounds(lb, ub)
        except ValueError as exc:
            raise ValueError(f"variables[{i}]: {exc}") from exc

        variables.append(
            MILPVariable(
                name=str(name),
                label=str(label),
                bounds=bounds,
                integrality=integrality,
            )
        )
    return variables


def _parse_objective(data: dict, n: int) -> Objective:
    raw = data.get("objective")
    if not isinstance(raw, dict):
        raise ValueError("'objective' must be a JSON object.")

    sense_str = raw.get("sense", "")
    try:
        sense = ObjectiveSense.from_str(str(sense_str))
    except ValueError as exc:
        raise ValueError(
            f"objective.sense must be 'min' or 'max', got '{sense_str}'."
        ) from exc

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

    offset_raw = raw.get("offset", 0)
    try:
        offset = float(offset_raw) if offset_raw is not None else 0.0
    except (TypeError, ValueError) as exc:
        raise ValueError(f"objective.offset must be a number, got '{offset_raw}'.") from exc

    return Objective(sense=sense, coefs=coefs, offset=offset)


def _parse_constraints(data: dict, n: int) -> list[Constraint]:
    raw = data.get("constraints", [])
    if not isinstance(raw, list):
        raise ValueError("'constraints' must be a JSON array.")

    constraints: list[Constraint] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"constraints[{i}] must be a JSON object.")
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
        rel_str = item.get("relation", "")
        try:
            relation = Relation.from_symbol(str(rel_str))
        except ValueError as exc:
            raise ValueError(
                f"constraints[{i}].relation must be '<=', '=', or '>=',"
                f" got '{rel_str}'."
            ) from exc
        rhs = _parse_optional_float(item, "rhs", context=f"constraints[{i}].rhs")
        constraints.append(Constraint(coefs=coefs, relation=relation, rhs=rhs))
    return constraints


def _parse_solver_options(data: dict) -> tuple[float | None, float | None]:
    raw = data.get("solver", {})
    if raw is None:
        return None, None
    if not isinstance(raw, dict):
        raise ValueError("'solver' must be a JSON object when present.")
    time_limit = _parse_optional_float(raw, "time_limit", context="solver.time_limit")
    mip_gap = _parse_optional_float(raw, "mip_gap", context="solver.mip_gap")
    return time_limit, mip_gap


def _parse_optional_float(obj: dict, key: str, *, context: str) -> float | None:
    value: Any = obj.get(key, None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be a number or null, got '{value}'.") from exc
