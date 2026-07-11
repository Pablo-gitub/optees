from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Optional

from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.utility.nlp_expression import SafeNLPExpression


def _normalize_tolerance(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("NLP tolerance must be a positive finite number or None")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError("NLP tolerance must be a positive finite number or None") from exc
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError("NLP tolerance must be a positive finite number or None")
    return normalized


@dataclass(frozen=True)
class NLPOptions:
    """Stopping and method options supported by the first NLP slice."""

    method: NLPSolverMethod = NLPSolverMethod.BFGS
    max_iterations: int = 1_000
    tolerance: Optional[float] = 1e-8

    def __post_init__(self) -> None:
        method = (
            NLPSolverMethod.from_str(self.method)
            if not isinstance(self.method, NLPSolverMethod)
            else self.method
        )
        if isinstance(self.max_iterations, bool) or not isinstance(self.max_iterations, int):
            raise ValueError("NLP max_iterations must be a positive integer")
        if self.max_iterations <= 0:
            raise ValueError("NLP max_iterations must be a positive integer")

        tolerance = _normalize_tolerance(self.tolerance)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "tolerance", tolerance)


@dataclass(frozen=True)
class NLPModel:
    """Continuous scalar NLP with optional per-variable box bounds."""

    variables: tuple[NLPVariable, ...]
    objective: NLPObjective
    options: NLPOptions = NLPOptions()

    def __post_init__(self) -> None:
        variables = tuple(self.variables)
        if not variables:
            raise ValueError("NLP model must contain at least one variable")
        if len({variable.name for variable in variables}) != len(variables):
            raise ValueError("NLP variable names must be unique")
        if not isinstance(self.objective, NLPObjective):
            raise ValueError("NLP model objective must be an NLPObjective")
        options = self.options if isinstance(self.options, NLPOptions) else NLPOptions(**self.options)

        expression = SafeNLPExpression.compile(
            self.objective.expression,
            self.variable_names(),
        )
        if self.has_bounds() and not options.method.supports_bounds():
            raise ValueError(
                f"NLP method {options.method.value} does not support box bounds; use L-BFGS-B"
            )

        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "options", options)
        object.__setattr__(self, "_expression", expression)

    @classmethod
    def from_parts(
        cls,
        *,
        variables: tuple[NLPVariable, ...] | list[NLPVariable],
        objective: NLPObjective,
        options: NLPOptions | None = None,
    ) -> "NLPModel":
        return cls(tuple(variables), objective, options or NLPOptions())

    def variable_names(self) -> tuple[str, ...]:
        return tuple(variable.name for variable in self.variables)

    def initial_point(self) -> tuple[float, ...]:
        return tuple(variable.initial_value for variable in self.variables)

    def bounds(self) -> tuple[tuple[Optional[float], Optional[float]], ...]:
        return tuple(
            (variable.lower_bound, variable.upper_bound) for variable in self.variables
        )

    def has_bounds(self) -> bool:
        return any(variable.is_bounded() for variable in self.variables)

    def evaluate_objective(self, values: Mapping[str, object]) -> float:
        return self._expression.evaluate(values)
