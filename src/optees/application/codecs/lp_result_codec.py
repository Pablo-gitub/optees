from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from optees.application.contracts.capability_ids import LP_CAPABILITY_ID
from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.value_objects.lp.solve_status import SolveStatus


class LPResultCodec:
    capability_id = LP_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: LPSolution) -> SerializedResult:
        result: dict[str, object] = {
            "objective": _optional_finite(solution.objective, "objective"),
            "objective_sense": _optional_text(solution.extras.get("objective_sense")),
            "variables": _variables(solution),
            "optimal_face": _optimal_face(solution.extras.get("alt_opt")),
        }
        diagnostics = _diagnostics(solution)
        warnings = _warnings(solution.extras.get("alt_opt"))

        normalized_result = require_json_value(result, path="$.result")
        normalized_diagnostics = require_json_value(diagnostics, path="$.diagnostics")
        assert isinstance(normalized_result, dict)
        assert isinstance(normalized_diagnostics, dict)
        return SerializedResult(
            mathematical_status=_STATUS_MAP[solution.status],
            result=normalized_result,
            diagnostics=normalized_diagnostics,
            warnings=warnings,
        )


_STATUS_MAP = {
    SolveStatus.OPTIMAL: MathematicalStatus.OPTIMAL,
    SolveStatus.INFEASIBLE: MathematicalStatus.INFEASIBLE,
    SolveStatus.UNBOUNDED: MathematicalStatus.UNBOUNDED,
    SolveStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


def _variables(solution: LPSolution) -> list[dict[str, JsonValue]]:
    declared_order = solution.extras.get("var_names")
    names = (
        [str(name) for name in declared_order]
        if isinstance(declared_order, (list, tuple))
        else list(solution.values)
    )
    names.extend(name for name in solution.values if name not in names)
    return [
        {
            "name": name,
            "value": _required_finite(solution.values[name], f"values.{name}"),
        }
        for name in names
        if name in solution.values
    ]


def _diagnostics(solution: LPSolution) -> dict[str, object]:
    diagnostics = solution.diagnostics
    return {
        "method": diagnostics.method,
        "iterations": diagnostics.nit,
        "crossover_iterations": diagnostics.crossover_nit,
        "message": diagnostics.message,
        "status_code": diagnostics.status_code,
        "success": diagnostics.success,
        "highs": {
            "equalities": _highs_block(diagnostics.eqlin, "eqlin"),
            "inequalities": _highs_block(diagnostics.ineqlin, "ineqlin"),
            "lower_bounds": _highs_block(diagnostics.lower, "lower"),
            "upper_bounds": _highs_block(diagnostics.upper, "upper"),
        },
    }


def _highs_block(value: object, name: str) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"diagnostics.{name} must be a mapping.")
    marginals, marginal_markers = _numeric_series(
        value.get("marginals"), f"diagnostics.{name}.marginals"
    )
    residuals, residual_markers = _numeric_series(
        value.get("residual"), f"diagnostics.{name}.residual"
    )
    return {
        "marginals": marginals,
        "marginal_non_finite": marginal_markers,
        "residual": residuals,
        "residual_non_finite": residual_markers,
    }


def _numeric_series(
    value: object, path: str
) -> tuple[list[float | None] | None, list[dict[str, object]]]:
    if value is None:
        return None, []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{path} must be a numeric sequence.")
    normalized: list[float | None] = []
    markers: list[dict[str, object]] = []
    for index, item in enumerate(value):
        try:
            number = float(item)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path}[{index}] must be numeric.") from exc
        if math.isnan(number):
            raise ValueError(f"{path}[{index}] contains NaN.")
        if math.isinf(number):
            normalized.append(None)
            markers.append(
                {
                    "index": index,
                    "kind": "positive_infinity" if number > 0 else "negative_infinity",
                }
            )
        else:
            normalized.append(number)
    return normalized, markers


def _optimal_face(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {
            "analysis_status": "not_available",
            "has_alternate_optimum": None,
            "dimension": None,
            "ranges": [],
            "varying_variables": [],
            "extreme_points": None,
            "auxiliary_failures": [],
        }

    skipped = bool(value.get("range_skipped", False))
    failures = [str(item) for item in value.get("auxiliary_failures", ()) or ()]
    ranges = value.get("ranges")
    range_rows = []
    if isinstance(ranges, Mapping):
        for name, raw_range in ranges.items():
            if not isinstance(raw_range, Mapping):
                raise ValueError(f"optimal_face.ranges.{name} must be a mapping.")
            minimum, minimum_unbounded = _range_value(
                raw_range.get("min"), f"optimal_face.ranges.{name}.minimum"
            )
            maximum, maximum_unbounded = _range_value(
                raw_range.get("max"), f"optimal_face.ranges.{name}.maximum"
            )
            width, width_unbounded = _range_value(
                raw_range.get("width"), f"optimal_face.ranges.{name}.width"
            )
            range_rows.append(
                {
                    "variable": str(name),
                    "minimum": minimum,
                    "minimum_unbounded": minimum_unbounded,
                    "maximum": maximum,
                    "maximum_unbounded": maximum_unbounded,
                    "width": width,
                    "width_unbounded": width_unbounded,
                    "is_fixed": _optional_bool(raw_range.get("is_fixed")),
                }
            )

    status = "skipped" if skipped else ("partial" if failures else "computed")
    return {
        "analysis_status": status,
        "has_alternate_optimum": _optional_bool(value.get("has_alternate_optimum")),
        "dimension": _optional_int(value.get("dimension"), "optimal_face.dimension"),
        "ranges": range_rows,
        "varying_variables": [
            str(item) for item in value.get("varying_variables", ()) or ()
        ],
        "extreme_points": _point_collection(value.get("extreme_points")),
        "auxiliary_failures": failures,
        "range_tolerance": _optional_finite(value.get("range_tol"), "optimal_face.range_tolerance"),
        "skip_reason": _optional_text(value.get("range_skip_reason")),
    }


def _point_collection(value: object) -> dict[str, dict[str, float]] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("optimal_face.extreme_points must be a mapping.")
    result: dict[str, dict[str, float]] = {}
    for point_name, point in value.items():
        if not isinstance(point, Mapping):
            raise ValueError(f"optimal_face.extreme_points.{point_name} must be a mapping.")
        result[str(point_name)] = {
            str(variable): _required_finite(
                coordinate,
                f"optimal_face.extreme_points.{point_name}.{variable}",
            )
            for variable, coordinate in point.items()
        }
    return result


def _warnings(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    warnings: list[str] = []
    if value.get("range_skipped"):
        reason = _optional_text(value.get("range_skip_reason"))
        warnings.append(
            "Optimal-face range analysis was skipped."
            + (f" {reason}" if reason else "")
        )
    failures = [str(item) for item in value.get("auxiliary_failures", ()) or ()]
    if failures:
        warnings.append(
            "Optimal-face range analysis is partial; failed auxiliary solves: "
            + ", ".join(failures)
            + "."
        )
    return tuple(warnings)


def _range_value(value: object, path: str) -> tuple[float | None, bool]:
    if value is None:
        return None, False
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be numeric or null.") from exc
    if math.isnan(number):
        raise ValueError(f"{path} contains NaN.")
    if math.isinf(number):
        return None, True
    return number, False


def _required_finite(value: object, path: str) -> float:
    normalized = _optional_finite(value, path)
    if normalized is None:
        raise ValueError(f"{path} must contain a finite number.")
    return normalized


def _optional_finite(value: object, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{path} must be numeric or null.")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be numeric or null.") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{path} contains a non-finite number.")
    return normalized


def _optional_int(value: object, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{path} must be an integer or null.")
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be an integer or null.") from exc


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
