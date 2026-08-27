from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.models.qp.qp_model import QPModel, QPOptions
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


def qp_model_from_dict(data: Mapping[str, Any]) -> QPModel:
    """Decode a QPModel from a JSON-compatible dictionary conforming to schema v1."""
    if not isinstance(data, Mapping):
        raise ValueError("QP problem payload must be a JSON object")

    raw_vars = data.get("variables")
    if not isinstance(raw_vars, (list, tuple)) or not raw_vars:
        raise ValueError("QP problem must contain a non-empty 'variables' list")

    variables: List[QPVariable] = []
    for idx, v_data in enumerate(raw_vars):
        if not isinstance(v_data, Mapping):
            raise ValueError(f"variables[{idx}] must be an object")
        name = v_data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"variables[{idx}].name must be a non-empty string")
        label = str(v_data.get("label", ""))
        lb = v_data.get("lower_bound")
        ub = v_data.get("upper_bound")
        variables.append(QPVariable(name=name, label=label, bounds=Bounds(lb, ub)))

    raw_obj = data.get("objective")
    if not isinstance(raw_obj, Mapping):
        raise ValueError("QP problem must contain an 'objective' object")

    sense_str = str(raw_obj.get("sense", "min")).strip().lower()
    if sense_str == "min":
        sense = ObjectiveSense.MIN
    elif sense_str == "max":
        sense = ObjectiveSense.MAX
    else:
        raise ValueError(f"unsupported objective sense {sense_str!r}; must be 'min' or 'max'")

    raw_linear = raw_obj.get("linear_coefs")
    if not isinstance(raw_linear, (list, tuple)):
        raise ValueError("objective.linear_coefs must be a list of numbers")
    linear_coefs = tuple(float(val) for val in raw_linear)

    raw_matrix = raw_obj.get("quadratic_matrix")
    if not isinstance(raw_matrix, (list, tuple)):
        raise ValueError("objective.quadratic_matrix must be a 2D matrix of numbers")
    quadratic_matrix = tuple(
        tuple(float(val) for val in row) for row in raw_matrix
    )
    offset = float(raw_obj.get("offset", 0.0))

    objective = QPObjective(
        sense=sense,
        linear_coefs=linear_coefs,
        quadratic_matrix=quadratic_matrix,
        offset=offset,
    )

    raw_constraints = data.get("constraints", [])
    if not isinstance(raw_constraints, (list, tuple)):
        raise ValueError("constraints must be a list of constraint objects")

    constraints: List[QPConstraint] = []
    for idx, c_data in enumerate(raw_constraints):
        if not isinstance(c_data, Mapping):
            raise ValueError(f"constraints[{idx}] must be an object")
        c_name = str(c_data.get("name", ""))
        raw_coefs = c_data.get("coefs")
        if not isinstance(raw_coefs, (list, tuple)):
            raise ValueError(f"constraints[{idx}].coefs must be a list of numbers")
        c_coefs = tuple(float(val) for val in raw_coefs)
        rel_str = str(c_data.get("relation", "<=")).strip()
        rel = Relation.from_symbol(rel_str)
        rhs_val = float(c_data.get("rhs", 0.0))
        constraints.append(QPConstraint(name=c_name, coefs=c_coefs, relation=rel, rhs=rhs_val))

    raw_options = data.get("options", {})
    if not isinstance(raw_options, Mapping):
        raise ValueError("options must be an object")

    options = QPOptions(
        method=str(raw_options.get("method", "osqp")),
        tolerance=float(raw_options.get("tolerance", 1e-7)),
        max_iterations=int(raw_options.get("max_iterations", 4000)),
        time_limit_seconds=float(raw_options.get("time_limit_seconds", 60.0)),
        warm_start=bool(raw_options.get("warm_start", False)),
        initial_primal=tuple(float(v) for v in raw_options.get("initial_primal", ())) if raw_options.get("initial_primal") else None,
        initial_dual=tuple(float(v) for v in raw_options.get("initial_dual", ())) if raw_options.get("initial_dual") else None,
    )

    return QPModel(
        variables=tuple(variables),
        objective=objective,
        constraints=tuple(constraints),
        options=options,
    )


def qp_model_to_dict(model: QPModel) -> Dict[str, Any]:
    """Serialize a QPModel to a JSON-compatible dictionary matching public schema v1."""
    variables = [
        {
            "name": v.name,
            "label": v.label,
            "lower_bound": v.bounds.lb,
            "upper_bound": v.bounds.ub,
        }
        for v in model.variables
    ]
    objective = {
        "sense": "min" if model.objective.sense == ObjectiveSense.MIN else "max",
        "linear_coefs": list(model.objective.linear_coefs),
        "quadratic_matrix": [list(row) for row in model.objective.quadratic_matrix],
        "offset": model.objective.offset,
    }
    constraints = [
        {
            "name": c.name,
            "coefs": list(c.coefs),
            "relation": c.relation.symbol(),
            "rhs": c.rhs,
        }
        for c in model.constraints
    ]
    options: Dict[str, Any] = {
        "method": model.options.method,
        "tolerance": model.options.tolerance,
        "max_iterations": model.options.max_iterations,
        "time_limit_seconds": model.options.time_limit_seconds,
        "warm_start": model.options.warm_start,
    }
    if model.options.initial_primal is not None:
        options["initial_primal"] = list(model.options.initial_primal)
    if model.options.initial_dual is not None:
        options["initial_dual"] = list(model.options.initial_dual)

    return {
        "contract_version": "1",
        "problem_schema_version": "1",
        "capability_id": "qp.continuous",
        "problem_type": "quadratic_programming",
        "variables": variables,
        "objective": objective,
        "constraints": constraints,
        "options": options,
    }


def qp_model_from_json(text: str) -> QPModel:
    return qp_model_from_dict(json.loads(text))


def qp_model_to_json(model: QPModel, *, indent: Optional[int] = 2) -> str:
    return json.dumps(qp_model_to_dict(model), indent=indent)
