from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple
import numpy as np

from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense


def _validate_finite_number(val: object, context: str) -> float:
    if val is None or isinstance(val, bool):
        raise ValueError(f"{context} must be a finite number")
    try:
        num = float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be a finite number") from exc
    if not math.isfinite(num):
        raise ValueError(f"{context} contains non-finite value")
    return num


@dataclass(frozen=True)
class QPOptions:
    """Solver options for Convex QP."""

    method: str = "osqp"
    tolerance: float = 1e-7
    max_iterations: int = 4000
    time_limit_seconds: float = 60.0

    def __post_init__(self) -> None:
        method = str(self.method).strip().lower()
        if method != "osqp":
            raise ValueError(
                f"unsupported QP method {self.method!r}; version 1 supports 'osqp' only"
            )
        if (
            isinstance(self.tolerance, bool)
            or not math.isfinite(self.tolerance)
            or not 1e-12 <= self.tolerance <= 1e-2
        ):
            raise ValueError("QP tolerance must be between 1e-12 and 1e-2")
        if (
            isinstance(self.max_iterations, bool)
            or not isinstance(self.max_iterations, int)
            or not 10 <= self.max_iterations <= 100_000
        ):
            raise ValueError("QP max_iterations must be between 10 and 100000")
        if (
            isinstance(self.time_limit_seconds, bool)
            or not math.isfinite(self.time_limit_seconds)
            or not 0.1 <= self.time_limit_seconds <= 300.0
        ):
            raise ValueError("QP time_limit_seconds must be between 0.1 and 300")

        object.__setattr__(self, "method", method)


@dataclass(frozen=True)
class QPModel:
    """Aggregate root for a continuous convex Quadratic Program."""

    variables: Tuple[QPVariable, ...]
    objective: QPObjective
    constraints: Tuple[QPConstraint, ...] = ()
    options: QPOptions = QPOptions()

    def __post_init__(self) -> None:
        variables = tuple(self.variables)
        if not variables:
            raise ValueError("QP model must contain at least one variable")

        var_names = [v.name for v in variables]
        if any(not isinstance(name, str) or not name.strip() for name in var_names):
            raise ValueError("QP variable names must be non-empty strings")
        if len(set(var_names)) != len(var_names):
            raise ValueError("QP variable names must be unique")

        n = len(variables)

        # Validate bounds
        for i, v in enumerate(variables):
            lb = v.bounds.lb
            ub = v.bounds.ub
            if lb is not None:
                _validate_finite_number(lb, f"variable '{v.name}' lower bound")
            if ub is not None:
                _validate_finite_number(ub, f"variable '{v.name}' upper bound")
            if lb is not None and ub is not None and lb > ub:
                raise ValueError(
                    f"variable '{v.name}' lower bound ({lb}) exceeds upper bound ({ub})"
                )

        # Validate linear coefficients
        linear_coefs = tuple(
            _validate_finite_number(c, f"objective linear coefficient {i}")
            for i, c in enumerate(self.objective.linear_coefs)
        )
        if len(linear_coefs) != n:
            raise ValueError(
                f"objective linear coefficients length ({len(linear_coefs)}) does not match variable count ({n})"
            )

        # Validate offset
        offset = _validate_finite_number(self.objective.offset, "objective offset")

        # Validate quadratic matrix
        raw_matrix = self.objective.quadratic_matrix
        if len(raw_matrix) != n:
            raise ValueError(
                f"objective quadratic matrix rows ({len(raw_matrix)}) does not match variable count ({n})"
            )
        matrix_rows = []
        for r_idx, row in enumerate(raw_matrix):
            if len(row) != n:
                raise ValueError(
                    f"objective quadratic matrix row {r_idx} length ({len(row)}) does not match variable count ({n})"
                )
            matrix_rows.append(
                [
                    _validate_finite_number(val, f"quadratic matrix entry [{r_idx}][{c_idx}]")
                    for c_idx, val in enumerate(row)
                ]
            )

        Q_arr = np.array(matrix_rows, dtype=float)
        max_q = float(np.max(np.abs(Q_arr))) if n > 0 else 1.0
        eps_sym = 1e-8 * max(1.0, max_q)
        eps_psd = 1e-8 * max(1.0, max_q)

        # Symmetry check
        asym = float(np.max(np.abs(Q_arr - Q_arr.T)))
        if asym > eps_sym:
            raise ValueError(
                f"quadratic matrix is asymmetric (max absolute difference {asym:.2e} > tolerance {eps_sym:.2e})"
            )

        # Canonicalize near-symmetric matrix
        Q_sym = 0.5 * (Q_arr + Q_arr.T)

        # Convexity / Concavity check
        eigenvalues = np.linalg.eigvalsh(Q_sym)
        is_min = self.objective.sense == ObjectiveSense.MIN
        if is_min:
            min_eig = float(np.min(eigenvalues))
            if min_eig < -eps_psd:
                raise ValueError(
                    f"quadratic matrix is not positive semi-definite (min eigenvalue {min_eig:.2e} < -{eps_psd:.2e})"
                )
        else:
            max_eig = float(np.max(eigenvalues))
            if max_eig > eps_psd:
                raise ValueError(
                    f"quadratic matrix is not negative semi-definite for maximization (max eigenvalue {max_eig:.2e} > {eps_psd:.2e})"
                )

        # Canonicalized quadratic matrix tuple (near-symmetric canonicalized, NO eigenvalue clamping in domain)
        canonical_matrix = tuple(tuple(float(val) for val in row) for row in Q_sym)

        # Validate constraints
        constraints = tuple(self.constraints)
        canonical_constraints = []
        for c_idx, cons in enumerate(constraints):
            if len(cons.coefs) != n:
                raise ValueError(
                    f"constraint {c_idx} coefficients length ({len(cons.coefs)}) does not match variable count ({n})"
                )
            c_coefs = tuple(
                _validate_finite_number(val, f"constraint {c_idx} coefficient {i}")
                for i, val in enumerate(cons.coefs)
            )
            c_rhs = _validate_finite_number(cons.rhs, f"constraint {c_idx} rhs")
            canonical_constraints.append(
                QPConstraint(
                    name=cons.name,
                    coefs=c_coefs,
                    relation=cons.relation,
                    rhs=c_rhs,
                )
            )

        # Validate options
        options = self.options if isinstance(self.options, QPOptions) else QPOptions(**self.options)
        object.__setattr__(self, "variables", variables)
        object.__setattr__(
            self,
            "objective",
            QPObjective(
                sense=self.objective.sense,
                linear_coefs=linear_coefs,
                quadratic_matrix=canonical_matrix,
                offset=offset,
            ),
        )
        object.__setattr__(self, "constraints", tuple(canonical_constraints))
        object.__setattr__(self, "options", options)

    @classmethod
    def from_parts(
        cls,
        *,
        variables: Sequence[QPVariable] | Iterable[QPVariable],
        objective: QPObjective,
        constraints: Sequence[QPConstraint] | Iterable[QPConstraint] = (),
        options: Optional[QPOptions] = None,
    ) -> QPModel:
        return cls(
            variables=tuple(variables),
            objective=objective,
            constraints=tuple(constraints),
            options=options or QPOptions(),
        )

    def n_vars(self) -> int:
        return len(self.variables)

    def n_constraints(self) -> int:
        return len(self.constraints)

    def variable_names(self) -> Tuple[str, ...]:
        return tuple(v.name for v in self.variables)
