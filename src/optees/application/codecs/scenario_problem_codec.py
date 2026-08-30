from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Sequence

from optees.application.contracts.errors import CodedValidationError
from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.scenario.scenario_options import (
    ScenarioOptions,
)
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)

_ALLOWED_TOP_LEVEL_KEYS = {
    "version",
    "problem_type",
    "orientation",
    "variables",
    "scenarios",
    "shared_objective",
    "shared_constraints",
    "options",
}
_ALLOWED_VARIABLE_KEYS = {
    "name",
    "label",
    "lower_bound",
    "upper_bound",
    "integrality",
}
_ALLOWED_SCENARIO_KEYS = {"id", "label", "coefficients", "offset"}
_ALLOWED_SHARED_OBJECTIVE_KEYS = {"coefficients", "offset"}
_ALLOWED_SHARED_CONSTRAINT_KEYS = {"name", "coefficients", "relation", "rhs"}
_ALLOWED_OPTIONS_KEYS = {"tolerance", "binding_tolerance", "time_limit_seconds"}


def _parse_number(val: Any, path: str) -> float:
    if isinstance(val, bool):
        raise CodedValidationError(
            f"Expected number at {path}, got boolean",
            detail_code="scenario.boolean_as_number",
            path=path,
        )
    if not isinstance(val, (int, float)):
        raise CodedValidationError(
            f"Expected number at {path}, got {type(val).__name__}",
            detail_code="scenario.invalid_structure",
            path=path,
        )
    if not math.isfinite(val):
        raise CodedValidationError(
            f"Non-finite number at {path}",
            detail_code="scenario.non_finite_value",
            path=path,
        )
    return float(val)


def _parse_optional_number(val: Any, path: str) -> float | None:
    if val is None:
        return None
    return _parse_number(val, path)


def _parse_optional_string(value: Any, path: str, *, default: str = "") -> str:
    if value is None:
        raise CodedValidationError(
            f"Expected string at {path}, got null",
            detail_code="scenario.invalid_structure",
            path=path,
        )
    if not isinstance(value, str):
        raise CodedValidationError(
            f"Expected string at {path}, got {type(value).__name__}",
            detail_code="scenario.invalid_structure",
            path=path,
        )
    return value if value else default


def scenario_model_from_public_dict(
    payload: Mapping[str, Any],
    *,
    expected_orientation: ScenarioOrientation | str,
) -> ScenarioModel:
    """Decode the versioned public linear scenario payload into a domain ScenarioModel.

    Rejects payloads with orientation belonging to another capability, unknown fields,
    malformed nested structures, booleans used as numbers, non-finite values, and dimension mismatches.
    """
    if not isinstance(payload, Mapping):
        raise CodedValidationError(
            "Problem payload must be a JSON object",
            detail_code="scenario.invalid_structure",
            path="$",
        )

    # Check unknown top-level keys
    for key in payload:
        if key not in _ALLOWED_TOP_LEVEL_KEYS:
            raise CodedValidationError(
                f"Unknown field '{key}' in problem payload",
                detail_code="scenario.invalid_structure",
                path=f"$.{key}",
            )

    # Required top-level keys
    required_keys = (
        "version",
        "problem_type",
        "orientation",
        "variables",
        "scenarios",
    )
    for req in required_keys:
        if req not in payload:
            raise CodedValidationError(
                f"Missing required field '{req}' in problem payload",
                detail_code="scenario.invalid_structure",
                path=f"$.{req}",
            )

    # Version check
    version = payload["version"]
    if version != "1":
        raise CodedValidationError(
            f"Expected problem schema version '1', got {version!r}",
            detail_code="scenario.invalid_version",
            path="$.version",
        )

    # Problem type check
    problem_type = payload["problem_type"]
    if problem_type != "linear_scenario":
        raise CodedValidationError(
            f"Expected problem_type 'linear_scenario', got {problem_type!r}",
            detail_code="scenario.invalid_problem_type",
            path="$.problem_type",
        )

    # Orientation check
    raw_orientation = payload["orientation"]
    if raw_orientation not in (
        "minimize_maximum_loss",
        "maximize_minimum_reward",
    ):
        raise CodedValidationError(
            f"Invalid orientation {raw_orientation!r}",
            detail_code="scenario.orientation_mismatch",
            path="$.orientation",
        )

    expected_orientation_val = (
        expected_orientation.value
        if isinstance(expected_orientation, ScenarioOrientation)
        else str(expected_orientation)
    )
    if raw_orientation != expected_orientation_val:
        raise CodedValidationError(
            f"Expected orientation '{expected_orientation_val}', got '{raw_orientation}'",
            detail_code="scenario.orientation_mismatch",
            path="$.orientation",
        )
    orientation = ScenarioOrientation(raw_orientation)

    # Variables parsing
    raw_variables = payload["variables"]
    if not isinstance(raw_variables, Sequence) or isinstance(raw_variables, (str, bytes)):
        raise CodedValidationError(
            "variables must be an array",
            detail_code="scenario.invalid_structure",
            path="$.variables",
        )
    if len(raw_variables) < 1 or len(raw_variables) > 500:
        raise CodedValidationError(
            f"variables count must be between 1 and 500, got {len(raw_variables)}",
            detail_code="scenario.dimension_mismatch",
            path="$.variables",
        )

    seen_var_names: set[str] = set()
    parsed_variables: list[ScenarioVariable] = []
    for idx, raw_var in enumerate(raw_variables):
        var_path = f"$.variables[{idx}]"
        if not isinstance(raw_var, Mapping):
            raise CodedValidationError(
                f"Variable at index {idx} must be an object",
                detail_code="scenario.invalid_structure",
                path=var_path,
            )
        for vk in raw_var:
            if vk not in _ALLOWED_VARIABLE_KEYS:
                raise CodedValidationError(
                    f"Unknown field '{vk}' in variable",
                    detail_code="scenario.invalid_structure",
                    path=f"{var_path}.{vk}",
                )
        if "name" not in raw_var:
            raise CodedValidationError(
                f"Missing required field 'name' in variable at index {idx}",
                detail_code="scenario.invalid_structure",
                path=f"{var_path}.name",
            )
        var_name = raw_var["name"]
        if not isinstance(var_name, str) or not var_name.strip():
            raise CodedValidationError(
                f"Variable name at index {idx} must be a non-empty string",
                detail_code="scenario.invalid_structure",
                path=f"{var_path}.name",
            )
        clean_name = var_name.strip()
        if clean_name in seen_var_names:
            raise CodedValidationError(
                f"Duplicate variable name '{clean_name}'",
                detail_code="scenario.duplicate_variable_name",
                path=f"{var_path}.name",
            )
        seen_var_names.add(clean_name)

        label = (
            _parse_optional_string(raw_var["label"], f"{var_path}.label")
            if "label" in raw_var
            else ""
        )

        lb = _parse_optional_number(raw_var.get("lower_bound"), f"{var_path}.lower_bound")
        ub = _parse_optional_number(raw_var.get("upper_bound"), f"{var_path}.upper_bound")
        if lb is not None and ub is not None and lb > ub:
            raise CodedValidationError(
                f"lower_bound ({lb}) exceeds upper_bound ({ub}) for variable '{clean_name}'",
                detail_code="scenario.invalid_bounds",
                path=var_path,
            )

        raw_integrality = raw_var.get("integrality", "C")
        if raw_integrality not in ("C", "I", "B"):
            raise CodedValidationError(
                f"Invalid integrality {raw_integrality!r} for variable '{clean_name}', expected 'C', 'I', or 'B'",
                detail_code="scenario.invalid_integrality",
                path=f"{var_path}.integrality",
            )
        integrality = (
            Integrality.CONTINUOUS
            if raw_integrality == "C"
            else (Integrality.INTEGER if raw_integrality == "I" else Integrality.BINARY)
        )

        bounds = Bounds(lb, ub)
        parsed_variables.append(
            ScenarioVariable(
                name=clean_name,
                label=label,
                bounds=bounds,
                integrality=integrality,
            )
        )

    n_vars = len(parsed_variables)

    # Scenarios parsing
    raw_scenarios = payload["scenarios"]
    if not isinstance(raw_scenarios, Sequence) or isinstance(raw_scenarios, (str, bytes)):
        raise CodedValidationError(
            "scenarios must be an array",
            detail_code="scenario.invalid_structure",
            path="$.scenarios",
        )
    if len(raw_scenarios) < 1 or len(raw_scenarios) > 2000:
        raise CodedValidationError(
            f"scenarios count must be between 1 and 2000, got {len(raw_scenarios)}",
            detail_code="scenario.dimension_mismatch",
            path="$.scenarios",
        )

    seen_scenario_ids: set[str] = set()
    parsed_scenarios: list[Scenario] = []
    for s_idx, raw_scen in enumerate(raw_scenarios):
        scen_path = f"$.scenarios[{s_idx}]"
        if not isinstance(raw_scen, Mapping):
            raise CodedValidationError(
                f"Scenario at index {s_idx} must be an object",
                detail_code="scenario.invalid_structure",
                path=scen_path,
            )
        for sk in raw_scen:
            if sk not in _ALLOWED_SCENARIO_KEYS:
                raise CodedValidationError(
                    f"Unknown field '{sk}' in scenario",
                    detail_code="scenario.invalid_structure",
                    path=f"{scen_path}.{sk}",
                )
        if "id" not in raw_scen:
            raise CodedValidationError(
                f"Missing required field 'id' in scenario at index {s_idx}",
                detail_code="scenario.invalid_structure",
                path=f"{scen_path}.id",
            )
        scen_id = raw_scen["id"]
        if not isinstance(scen_id, str) or not scen_id.strip():
            raise CodedValidationError(
                f"Scenario id at index {s_idx} must be a non-empty string",
                detail_code="scenario.invalid_structure",
                path=f"{scen_path}.id",
            )
        clean_id = scen_id.strip()
        if clean_id in seen_scenario_ids:
            raise CodedValidationError(
                f"Duplicate scenario id '{clean_id}'",
                detail_code="scenario.duplicate_scenario_id",
                path=f"{scen_path}.id",
            )
        seen_scenario_ids.add(clean_id)

        scen_label = (
            _parse_optional_string(raw_scen["label"], f"{scen_path}.label")
            if "label" in raw_scen
            else ""
        )

        if "coefficients" not in raw_scen:
            raise CodedValidationError(
                f"Missing required field 'coefficients' in scenario '{clean_id}'",
                detail_code="scenario.invalid_structure",
                path=f"{scen_path}.coefficients",
            )
        raw_coefs = raw_scen["coefficients"]
        if not isinstance(raw_coefs, Sequence) or isinstance(raw_coefs, (str, bytes)):
            raise CodedValidationError(
                f"coefficients in scenario '{clean_id}' must be an array",
                detail_code="scenario.invalid_structure",
                path=f"{scen_path}.coefficients",
            )
        if len(raw_coefs) != n_vars:
            raise CodedValidationError(
                f"Scenario '{clean_id}' coefficients length ({len(raw_coefs)}) does not match variables count ({n_vars})",
                detail_code="scenario.dimension_mismatch",
                path=f"{scen_path}.coefficients",
            )

        parsed_coefs = tuple(
            _parse_number(c, f"{scen_path}.coefficients[{c_idx}]")
            for c_idx, c in enumerate(raw_coefs)
        )
        offset = _parse_number(raw_scen.get("offset", 0.0), f"{scen_path}.offset")

        parsed_scenarios.append(
            Scenario(
                id=clean_id,
                label=scen_label,
                coefficients=parsed_coefs,
                offset=offset,
            )
        )

    # Shared objective parsing
    parsed_shared_objective: ScenarioSharedObjective | None = None
    if "shared_objective" in payload:
        raw_obj = payload["shared_objective"]
        if not isinstance(raw_obj, Mapping):
            raise CodedValidationError(
                "shared_objective must be an object",
                detail_code="scenario.invalid_structure",
                path="$.shared_objective",
            )
        else:
            for ok in raw_obj:
                if ok not in _ALLOWED_SHARED_OBJECTIVE_KEYS:
                    raise CodedValidationError(
                        f"Unknown field '{ok}' in shared_objective",
                        detail_code="scenario.invalid_structure",
                        path=f"$.shared_objective.{ok}",
                    )
            obj_coefs: tuple[float, ...] = ()
            if "coefficients" in raw_obj:
                raw_obj_coefs = raw_obj["coefficients"]
                if not isinstance(raw_obj_coefs, Sequence) or isinstance(
                    raw_obj_coefs, (str, bytes)
                ):
                    raise CodedValidationError(
                        "shared_objective.coefficients must be an array",
                        detail_code="scenario.invalid_structure",
                        path="$.shared_objective.coefficients",
                    )
                if len(raw_obj_coefs) != n_vars:
                    raise CodedValidationError(
                        f"shared_objective.coefficients length ({len(raw_obj_coefs)}) does not match variables count ({n_vars})",
                        detail_code="scenario.dimension_mismatch",
                        path="$.shared_objective.coefficients",
                    )
                obj_coefs = tuple(
                    _parse_number(c, f"$.shared_objective.coefficients[{c_idx}]")
                    for c_idx, c in enumerate(raw_obj_coefs)
                )
            obj_offset = _parse_number(raw_obj.get("offset", 0.0), "$.shared_objective.offset")
            parsed_shared_objective = ScenarioSharedObjective(
                coefficients=obj_coefs, offset=obj_offset
            )

    # Shared constraints parsing
    parsed_constraints: list[ScenarioConstraint] = []
    if "shared_constraints" in payload:
        raw_constraints = payload["shared_constraints"]
        if not isinstance(raw_constraints, Sequence) or isinstance(raw_constraints, (str, bytes)):
            raise CodedValidationError(
                "shared_constraints must be an array",
                detail_code="scenario.invalid_structure",
                path="$.shared_constraints",
            )
        else:
            if len(raw_constraints) > 1000:
                raise CodedValidationError(
                    f"shared_constraints count exceeds maximum 1000, got {len(raw_constraints)}",
                    detail_code="scenario.dimension_mismatch",
                    path="$.shared_constraints",
                )
            for c_idx, raw_cons in enumerate(raw_constraints):
                cons_path = f"$.shared_constraints[{c_idx}]"
                if not isinstance(raw_cons, Mapping):
                    raise CodedValidationError(
                        f"Constraint at index {c_idx} must be an object",
                        detail_code="scenario.invalid_structure",
                        path=cons_path,
                    )
                for ck in raw_cons:
                    if ck not in _ALLOWED_SHARED_CONSTRAINT_KEYS:
                        raise CodedValidationError(
                            f"Unknown field '{ck}' in constraint",
                            detail_code="scenario.invalid_structure",
                            path=f"{cons_path}.{ck}",
                        )
                if "coefficients" not in raw_cons:
                    raise CodedValidationError(
                        f"Missing required field 'coefficients' in constraint at index {c_idx}",
                        detail_code="scenario.invalid_structure",
                        path=f"{cons_path}.coefficients",
                    )
                if "relation" not in raw_cons:
                    raise CodedValidationError(
                        f"Missing required field 'relation' in constraint at index {c_idx}",
                        detail_code="scenario.invalid_structure",
                        path=f"{cons_path}.relation",
                    )
                if "rhs" not in raw_cons:
                    raise CodedValidationError(
                        f"Missing required field 'rhs' in constraint at index {c_idx}",
                        detail_code="scenario.invalid_structure",
                        path=f"{cons_path}.rhs",
                    )

                c_name = (
                    _parse_optional_string(raw_cons["name"], f"{cons_path}.name")
                    if "name" in raw_cons
                    else f"c{c_idx + 1}"
                )
                raw_c_coefs = raw_cons["coefficients"]
                if not isinstance(raw_c_coefs, Sequence) or isinstance(raw_c_coefs, (str, bytes)):
                    raise CodedValidationError(
                        f"Constraint '{c_name}' coefficients must be an array",
                        detail_code="scenario.invalid_structure",
                        path=f"{cons_path}.coefficients",
                    )
                if len(raw_c_coefs) != n_vars:
                    raise CodedValidationError(
                        f"Constraint '{c_name}' coefficients length ({len(raw_c_coefs)}) does not match variables count ({n_vars})",
                        detail_code="scenario.dimension_mismatch",
                        path=f"{cons_path}.coefficients",
                    )
                c_coefs = tuple(
                    _parse_number(c, f"{cons_path}.coefficients[{k}]")
                    for k, c in enumerate(raw_c_coefs)
                )

                raw_rel = raw_cons["relation"]
                if raw_rel not in ("<=", "=", ">="):
                    raise CodedValidationError(
                        f"Invalid constraint relation {raw_rel!r}, expected '<=', '=', or '>='",
                        detail_code="scenario.invalid_relation",
                        path=f"{cons_path}.relation",
                    )
                c_rel = Relation.from_symbol(raw_rel)
                c_rhs = _parse_number(raw_cons["rhs"], f"{cons_path}.rhs")

                parsed_constraints.append(
                    ScenarioConstraint(
                        name=c_name,
                        coefficients=c_coefs,
                        relation=c_rel,
                        rhs=c_rhs,
                    )
                )

    # Options parsing
    tol = 1e-7
    bind_tol = 1e-6
    time_limit: float | None = None
    if "options" in payload:
        raw_options = payload["options"]
        if not isinstance(raw_options, Mapping):
            raise CodedValidationError(
                "options must be an object",
                detail_code="scenario.invalid_structure",
                path="$.options",
            )
        else:
            for opt_key in raw_options:
                if opt_key not in _ALLOWED_OPTIONS_KEYS:
                    raise CodedValidationError(
                        f"Unknown field '{opt_key}' in options",
                        detail_code="scenario.invalid_structure",
                        path=f"$.options.{opt_key}",
                    )
            if "tolerance" in raw_options:
                tol = _parse_number(raw_options["tolerance"], "$.options.tolerance")
                if tol <= 0:
                    raise CodedValidationError(
                        f"options.tolerance must be positive, got {tol}",
                        detail_code="scenario.invalid_option",
                        path="$.options.tolerance",
                    )
            if "binding_tolerance" in raw_options:
                bind_tol = _parse_number(
                    raw_options["binding_tolerance"],
                    "$.options.binding_tolerance",
                )
                if bind_tol <= 0:
                    raise CodedValidationError(
                        f"options.binding_tolerance must be positive, got {bind_tol}",
                        detail_code="scenario.invalid_option",
                        path="$.options.binding_tolerance",
                    )
            if "time_limit_seconds" in raw_options:
                time_limit = _parse_number(
                    raw_options["time_limit_seconds"], "$.options.time_limit_seconds"
                )
                if time_limit <= 0:
                    raise CodedValidationError(
                        f"options.time_limit_seconds must be positive, got {time_limit}",
                        detail_code="scenario.invalid_option",
                        path="$.options.time_limit_seconds",
                    )

    options = ScenarioOptions(
        tolerance=tol,
        binding_tolerance=bind_tol,
        time_limit_seconds=time_limit,
    )

    return ScenarioModel(
        orientation=orientation,
        variables=tuple(parsed_variables),
        scenarios=tuple(parsed_scenarios),
        shared_objective=parsed_shared_objective,
        shared_constraints=tuple(parsed_constraints),
        options=options,
    )


def scenario_min_max_loss_model_from_public_dict(
    payload: Mapping[str, Any],
) -> ScenarioModel:
    """Decode public problem payload expecting minimize_maximum_loss orientation."""
    return scenario_model_from_public_dict(
        payload, expected_orientation=ScenarioOrientation.MIN_MAX_LOSS
    )


def scenario_max_min_reward_model_from_public_dict(
    payload: Mapping[str, Any],
) -> ScenarioModel:
    """Decode public problem payload expecting maximize_minimum_reward orientation."""
    return scenario_model_from_public_dict(
        payload, expected_orientation=ScenarioOrientation.MAX_MIN_REWARD
    )
