"""Continuous nonlinear-programming utilities backed by SciPy.

The public function consumes the canonical NLP dictionary produced by the
application layer. User expressions are always evaluated by
``SafeNLPExpression``; no arbitrary Python text reaches SciPy.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Optional, Sequence

from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.utility.nlp_expression import SafeNLPExpression

try:
    from scipy.optimize import minimize
except Exception as exc:  # pragma: no cover - exercised only without SciPy
    minimize = None
    _SCIPY_IMPORT_ERROR = exc


__all__ = ["solve_nlp"]


def solve_nlp(
    problem: Mapping[str, object],
) -> tuple[str, Optional[float], dict[str, float], dict[str, object]]:
    """Solve a scalar continuous NLP with optional box bounds.

    Returns ``(status, objective, values, extras)``. ``Converged`` is a local
    numerical termination status, never a certificate of global optimality.
    """
    if minimize is None:  # pragma: no cover - local test environment has SciPy
        raise RuntimeError(f"SciPy not available: {_SCIPY_IMPORT_ERROR}")

    normalized = _normalize_problem(problem)
    expression = SafeNLPExpression.compile(
        normalized["expression"],
        normalized["variable_names"],
    )
    history: list[float] = []

    def original_objective(point: Sequence[object]) -> float:
        values = _point_to_values(point, normalized["variable_names"])
        return expression.evaluate(values)

    try:
        initial_objective = original_objective(normalized["initial_point"])
        history.append(initial_objective)

        def solver_objective(point: Sequence[object]) -> float:
            value = original_objective(point)
            return value if normalized["sense"] == "min" else -value

        def callback(point: Sequence[object]) -> None:
            history.append(original_objective(point))

        result = minimize(
            solver_objective,
            normalized["initial_point"],
            method=normalized["method"].value,
            bounds=normalized["bounds"] if normalized["has_bounds"] else None,
            callback=callback,
            tol=normalized["tolerance"],
            options={"maxiter": normalized["max_iterations"]},
        )
    except Exception as exc:
        return (
            "Failed",
            None,
            {},
            {
                "method": normalized["method"].value,
                "success": False,
                "message": f"objective evaluation or solver failed: {exc}",
                "iterations": None,
                "evaluations": None,
                "convergence_history": tuple(history),
            },
        )

    status = _map_result_status(result)
    extras = {
        "method": normalized["method"].value,
        "success": bool(getattr(result, "success", False)),
        "message": str(getattr(result, "message", "")),
        "iterations": _optional_non_negative_int(getattr(result, "nit", None)),
        "evaluations": _optional_non_negative_int(getattr(result, "nfev", None)),
        "convergence_history": tuple(history),
        "scipy_status": getattr(result, "status", None),
    }
    if status == "Failed":
        return status, None, {}, extras

    try:
        values = _point_to_values(result.x, normalized["variable_names"])
        objective = original_objective(result.x)
    except Exception as exc:
        extras["message"] = f"solver returned an invalid candidate: {exc}"
        extras["success"] = False
        return "Failed", None, {}, extras

    if not history or not math.isclose(history[-1], objective, rel_tol=0.0, abs_tol=0.0):
        history.append(objective)
        extras["convergence_history"] = tuple(history)
    return status, objective, values, extras


def _normalize_problem(problem: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(problem, Mapping):
        raise ValueError("NLP problem must be a mapping")

    sense = str(problem.get("sense", "min")).strip().lower()
    if sense not in {"min", "max"}:
        raise ValueError("NLP sense must be 'min' or 'max'")

    expression = problem.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("NLP expression must be a non-empty string")

    variable_names = _normalize_variable_names(problem.get("variables"))
    initial_point = _normalize_point(problem.get("initial_point"), len(variable_names))
    bounds = _normalize_bounds(problem.get("bounds"), len(variable_names))
    method = NLPSolverMethod.from_str(problem.get("method", NLPSolverMethod.BFGS.value))
    has_bounds = any(lower is not None or upper is not None for lower, upper in bounds)
    if has_bounds and not method.supports_bounds():
        raise ValueError(
            f"NLP method {method.value} does not support box bounds; use L-BFGS-B"
        )

    for name, value, (lower, upper) in zip(variable_names, initial_point, bounds):
        if lower is not None and value < lower:
            raise ValueError(f"initial point for {name!r} violates its lower bound")
        if upper is not None and value > upper:
            raise ValueError(f"initial point for {name!r} violates its upper bound")

    return {
        "sense": sense,
        "expression": expression.strip(),
        "variable_names": variable_names,
        "initial_point": initial_point,
        "bounds": bounds,
        "has_bounds": has_bounds,
        "method": method,
        "max_iterations": _normalize_max_iterations(problem.get("max_iterations", 1_000)),
        "tolerance": _normalize_tolerance(problem.get("tolerance", 1e-8)),
    }


def _normalize_variable_names(value: object) -> tuple[str, ...]:
    if not _is_sequence(value):
        raise ValueError("NLP variables must be a non-empty sequence")
    names = tuple(value)  # type: ignore[arg-type]
    if not names:
        raise ValueError("NLP variables must be a non-empty sequence")
    # The expression compiler owns the complete identifier and reserved-name rules.
    SafeNLPExpression.compile("0", names)  # type: ignore[arg-type]
    return names  # type: ignore[return-value]


def _normalize_point(value: object, count: int) -> tuple[float, ...]:
    if not _is_sequence(value):
        raise ValueError("NLP initial_point must be a numeric sequence")
    point = tuple(_finite_float(item, "initial point value") for item in value)  # type: ignore[arg-type]
    if len(point) != count:
        raise ValueError("NLP initial_point length must match variables")
    return point


def _normalize_bounds(
    value: object,
    count: int,
) -> tuple[tuple[Optional[float], Optional[float]], ...]:
    if value is None:
        return ((None, None),) * count
    if not _is_sequence(value):
        raise ValueError("NLP bounds must be a sequence")
    raw_bounds = tuple(value)  # type: ignore[arg-type]
    if len(raw_bounds) != count:
        raise ValueError("NLP bounds length must match variables")

    normalized: list[tuple[Optional[float], Optional[float]]] = []
    for index, raw_bound in enumerate(raw_bounds):
        if not _is_sequence(raw_bound) or len(raw_bound) != 2:  # type: ignore[arg-type]
            raise ValueError(f"NLP bounds[{index}] must be a (lower, upper) pair")
        lower = None if raw_bound[0] is None else _finite_float(raw_bound[0], "lower bound")  # type: ignore[index]
        upper = None if raw_bound[1] is None else _finite_float(raw_bound[1], "upper bound")  # type: ignore[index]
        if lower is not None and upper is not None and lower > upper:
            raise ValueError(f"NLP bounds[{index}] has lower bound greater than upper bound")
        normalized.append((lower, upper))
    return tuple(normalized)


def _normalize_max_iterations(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("NLP max_iterations must be a positive integer")
    return value


def _normalize_tolerance(value: object) -> Optional[float]:
    if value is None:
        return None
    normalized = _finite_float(value, "tolerance")
    if normalized <= 0:
        raise ValueError("NLP tolerance must be positive")
    return normalized


def _finite_float(value: object, description: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"NLP {description} must be a finite number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NLP {description} must be a finite number") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"NLP {description} must be a finite number")
    return normalized


def _point_to_values(
    point: Sequence[object],
    names: tuple[str, ...],
) -> dict[str, float]:
    if len(point) != len(names):
        raise ValueError("solver point length does not match variables")
    return {
        name: _finite_float(value, f"solver value for {name!r}")
        for name, value in zip(names, point)
    }


def _map_result_status(result: object) -> str:
    if bool(getattr(result, "success", False)):
        return "Converged"
    message = str(getattr(result, "message", "")).lower()
    if "maximum number" in message or "maxiter" in message or "maxfev" in message:
        return "IterationLimit"
    return "Failed"


def _optional_non_negative_int(value: object) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        normalized = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return normalized if normalized >= 0 else None


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))
