"""Versioned JSON import/export for Phase 1 continuous NLP models.

Schema v1:

.. code-block:: json

  {
    "version": "1",
    "problem_type": "nonlinear_programming",
    "variables": [
      {"name": "x1", "label": "coordinate", "lb": null, "ub": 2,
       "initial": 0}
    ],
    "objective": {"sense": "min", "expression": "(x1 - 1)**2"},
    "solver_options": {"method": "L-BFGS-B", "max_iterations": 1000,
                       "tolerance": 1e-8}
  }

Every reader path builds the same domain model used by the formulation UI, so
an imported document cannot bypass name, bound, initial-point, or expression
safety validation.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Optional

from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.models.nlp.nlp_model import NLPModel, NLPOptions
from optees.domain.value_objects.nlp.objective_sense import NLPObjectiveSense
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod


NLP_JSON_VERSION = "1"
NLP_PROBLEM_TYPE = "nonlinear_programming"


def nlp_model_from_dict(data: Mapping[str, object]) -> NLPModel:
    """Build an ``NLPModel`` from a schema-v1 JSON object."""
    if not isinstance(data, Mapping):
        raise ValueError("NLP JSON root must be an object")

    version = str(data.get("version", ""))
    if version != NLP_JSON_VERSION:
        raise ValueError(f"unsupported NLP JSON version: {version!r}")

    problem_type = str(data.get("problem_type", "")).strip().lower()
    if problem_type != NLP_PROBLEM_TYPE:
        raise ValueError(f"problem_type must be {NLP_PROBLEM_TYPE!r}")

    variables = _parse_variables(data.get("variables"))
    objective = _parse_objective(data.get("objective"))
    options = _parse_solver_options(data.get("solver_options", {}))
    try:
        return NLPModel.from_parts(
            variables=variables,
            objective=objective,
            options=options,
        )
    except ValueError as exc:
        raise ValueError(f"invalid NLP model: {exc}") from exc


def nlp_model_to_dict(model: NLPModel) -> dict[str, object]:
    """Serialize an ``NLPModel`` to the schema-v1 JSON-ready representation."""
    return {
        "version": NLP_JSON_VERSION,
        "problem_type": NLP_PROBLEM_TYPE,
        "variables": [
            {
                "name": variable.name,
                "label": variable.label,
                "lb": variable.lower_bound,
                "ub": variable.upper_bound,
                "initial": variable.initial_value,
            }
            for variable in model.variables
        ],
        "objective": {
            "sense": model.objective.sense.value,
            "expression": model.objective.expression,
        },
        "solver_options": {
            "method": model.options.method.value,
            "max_iterations": model.options.max_iterations,
            "tolerance": model.options.tolerance,
        },
    }


def nlp_model_from_file(path: str | Path) -> NLPModel:
    """Load a continuous NLP model from a UTF-8 JSON file."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read NLP JSON file: {exc}") from exc
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid NLP JSON: {exc}") from exc
    return nlp_model_from_dict(data)


def nlp_model_to_file(model: NLPModel, path: str | Path) -> None:
    """Write a continuous NLP model as formatted UTF-8 JSON."""
    Path(path).write_text(
        json.dumps(nlp_model_to_dict(model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _parse_variables(value: object) -> list[NLPVariable]:
    if not isinstance(value, list) or not value:
        raise ValueError("variables must be a non-empty array")

    variables: list[NLPVariable] = []
    for index, raw_variable in enumerate(value):
        if not isinstance(raw_variable, Mapping):
            raise ValueError(f"variables[{index}] must be an object")
        name = raw_variable.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"variables[{index}].name must be a non-empty string")
        label = raw_variable.get("label", "")
        if not isinstance(label, str):
            raise ValueError(f"variables[{index}].label must be a string")
        try:
            variables.append(
                NLPVariable(
                    name=name,
                    label=label,
                    lower_bound=_optional_finite_number(
                        raw_variable.get("lb"), f"variables[{index}].lb"
                    ),
                    upper_bound=_optional_finite_number(
                        raw_variable.get("ub"), f"variables[{index}].ub"
                    ),
                    initial_value=_required_finite_number(
                        raw_variable.get("initial"), f"variables[{index}].initial"
                    ),
                )
            )
        except ValueError as exc:
            raise ValueError(f"variables[{index}]: {exc}") from exc
    return variables


def _parse_objective(value: object) -> NLPObjective:
    if not isinstance(value, Mapping):
        raise ValueError("objective must be an object")
    expression = value.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("objective.expression must be a non-empty string")
    try:
        sense = NLPObjectiveSense.from_str(value.get("sense"))
    except ValueError as exc:
        raise ValueError(f"objective.sense: {exc}") from exc
    return NLPObjective(expression=expression, sense=sense)


def _parse_solver_options(value: object) -> NLPOptions:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise ValueError("solver_options must be an object")
    try:
        method = NLPSolverMethod.from_str(value.get("method", NLPSolverMethod.BFGS.value))
    except ValueError as exc:
        raise ValueError(f"solver_options.method: {exc}") from exc

    max_iterations = value.get("max_iterations", 1_000)
    tolerance = _optional_finite_number(value.get("tolerance", 1e-8), "solver_options.tolerance")
    try:
        return NLPOptions(
            method=method,
            max_iterations=max_iterations,  # domain validates an integer
            tolerance=tolerance,
        )
    except ValueError as exc:
        raise ValueError(f"solver_options: {exc}") from exc


def _required_finite_number(value: object, context: str) -> float:
    if value is None:
        raise ValueError(f"{context} is required")
    return _finite_number(value, context)


def _optional_finite_number(value: object, context: str) -> Optional[float]:
    if value is None:
        return None
    return _finite_number(value, context)


def _finite_number(value: object, context: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{context} must be a finite number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be a finite number") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{context} must be a finite number")
    return normalized
