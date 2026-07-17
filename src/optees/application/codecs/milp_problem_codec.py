from __future__ import annotations

import math

from optees.application.contracts.json_value import JsonValue
from optees.domain.models.milp.milp_model import MILPModel
from optees.utility.milp_json_io import milp_model_from_dict


def milp_model_from_public_dict(payload: dict[str, JsonValue]) -> MILPModel:
    required = ("version", "variables", "objective", "constraints")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError("milp.linear is missing required fields: " + ", ".join(missing))
    model = milp_model_from_dict(payload)
    _validate_public_model(model)
    return model


def _validate_public_model(model: MILPModel) -> None:
    names = [variable.name for variable in model.variables]
    if len(set(names)) != len(names):
        raise ValueError("variable names must be unique")

    for index, variable in enumerate(model.variables):
        _optional_finite(variable.bounds.lb, f"variables[{index}].lb")
        _optional_finite(variable.bounds.ub, f"variables[{index}].ub")
    for index, coefficient in enumerate(model.objective.coefs):
        _optional_finite(coefficient, f"objective.coefficients[{index}]")
    _finite(model.objective.offset, "objective.offset")
    for row, constraint in enumerate(model.constraints):
        for column, coefficient in enumerate(constraint.coefs):
            _optional_finite(
                coefficient,
                f"constraints[{row}].coefficients[{column}]",
            )
        _optional_finite(constraint.rhs, f"constraints[{row}].rhs")
    if model.time_limit is not None:
        _finite(model.time_limit, "solver.time_limit")
        if model.time_limit <= 0:
            raise ValueError("solver.time_limit must be positive")
    if model.mip_gap is not None:
        _finite(model.mip_gap, "solver.mip_gap")
        if model.mip_gap < 0:
            raise ValueError("solver.mip_gap must be non-negative")


def _optional_finite(value: float | None, path: str) -> None:
    if value is not None:
        _finite(value, path)


def _finite(value: float, path: str) -> None:
    if not math.isfinite(float(value)):
        raise ValueError(f"{path} must be finite")
