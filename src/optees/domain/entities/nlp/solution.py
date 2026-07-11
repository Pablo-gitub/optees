from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional

from optees.domain.value_objects.nlp.solve_status import NLPSolveStatus


@dataclass(frozen=True)
class NLPSolution:
    """Numerical result for a continuous NLP run, never a global-optimum proof."""

    status: NLPSolveStatus
    objective: Optional[float]
    values: dict[str, float]
    iterations: Optional[int] = None
    evaluations: Optional[int] = None
    termination_message: Optional[str] = None
    convergence_history: tuple[float, ...] = ()
    extras: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_solver_result(
        cls,
        *,
        status: object,
        objective: object,
        values: Mapping[str, object] | None,
        extras: Mapping[str, object] | None = None,
    ) -> "NLPSolution":
        raw_extras = dict(extras or {})
        return cls(
            status=NLPSolveStatus.from_str(status),
            objective=_optional_finite_float(objective),
            values={
                str(name): value
                for name, raw_value in (values or {}).items()
                if (value := _optional_finite_float(raw_value)) is not None
            },
            iterations=_optional_non_negative_int(raw_extras.get("iterations")),
            evaluations=_optional_non_negative_int(raw_extras.get("evaluations")),
            termination_message=_optional_message(raw_extras.get("message")),
            convergence_history=tuple(
                value
                for raw_value in raw_extras.get("convergence_history", ())
                if (value := _optional_finite_float(raw_value)) is not None
            ),
            extras=raw_extras,
        )

    def converged(self) -> bool:
        return self.status is NLPSolveStatus.CONVERGED


def _optional_finite_float(value: object) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return normalized if math.isfinite(normalized) else None


def _optional_non_negative_int(value: object) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        normalized = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return normalized if normalized >= 0 else None


def _optional_message(value: object) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
