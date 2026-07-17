from __future__ import annotations

import math

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue
from optees.application.contracts.solution_validation import (
    SolutionValidation,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationViolation,
)
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.value_objects.lp.relation import Relation


class LPIndependentSolutionValidator:
    """Recompute LP candidate invariants without consulting solver diagnostics."""

    def __init__(self, *, absolute_tolerance: float = 1e-7, relative_tolerance: float = 1e-7):
        for value in (absolute_tolerance, relative_tolerance):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("LP validation tolerances must be finite and non-negative")
        self._absolute_tolerance = float(absolute_tolerance)
        self._relative_tolerance = float(relative_tolerance)

    def __call__(
        self,
        model: LPModel,
        serialized: SerializedResult,
    ) -> SolutionValidation:
        if serialized.mathematical_status not in {
            MathematicalStatus.OPTIMAL,
            MathematicalStatus.FEASIBLE,
        }:
            return SolutionValidation.not_available(
                "No primal candidate is available for independent LP validation."
            )

        values, row_indexes, vector_violations = self._candidate_values(
            model,
            serialized.result,
        )
        vector_check = ValidationCheck(
            code="lp.variable_vector",
            status=_check_status(not vector_violations),
            description="The candidate contains one finite value for every declared variable.",
            measurements={
                "declared_count": len(model.variables),
                "candidate_count": len(values),
            },
        )
        if vector_violations:
            return self._report((vector_check,), tuple(vector_violations))

        checks: list[ValidationCheck] = [vector_check]
        violations: list[ValidationViolation] = []

        bound_violations, max_bound_violation = self._validate_bounds(
            model,
            values,
            row_indexes,
        )
        violations.extend(bound_violations)
        checks.append(
            ValidationCheck(
                code="lp.bounds",
                status=_check_status(not bound_violations),
                description="Every candidate value satisfies its declared lower and upper bounds.",
                measurements={"maximum_violation": max_bound_violation},
            )
        )

        constraint_violations, max_constraint_violation = self._validate_constraints(
            model,
            values,
        )
        violations.extend(constraint_violations)
        checks.append(
            ValidationCheck(
                code="lp.constraints",
                status=_check_status(not constraint_violations),
                description="Every linear constraint is satisfied by the candidate vector.",
                measurements={
                    "constraint_count": len(model.constraints),
                    "maximum_violation": max_constraint_violation,
                },
            )
        )

        objective_check, objective_violations = self._validate_objective(
            model,
            values,
            serialized.result,
        )
        checks.append(objective_check)
        violations.extend(objective_violations)
        return self._report(tuple(checks), tuple(violations))

    def _candidate_values(
        self,
        model: LPModel,
        result: dict[str, JsonValue],
    ) -> tuple[dict[str, float], dict[str, int], list[ValidationViolation]]:
        rows = result.get("variables")
        values: dict[str, float] = {}
        row_indexes: dict[str, int] = {}
        violations: list[ValidationViolation] = []
        if not isinstance(rows, list):
            return values, row_indexes, [
                _violation(
                    "invalid_variable_vector",
                    "lp.variable_vector",
                    "$.result.variables",
                    "Candidate variables must be an array.",
                )
            ]

        duplicates: list[str] = []
        invalid_rows: list[int] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                invalid_rows.append(index)
                continue
            name = row.get("name")
            value = row.get("value")
            if not isinstance(name, str) or not name.strip():
                invalid_rows.append(index)
                continue
            if name in values:
                duplicates.append(name)
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                invalid_rows.append(index)
                continue
            number = float(value)
            if not math.isfinite(number):
                invalid_rows.append(index)
                continue
            values[name] = number
            row_indexes[name] = index

        declared = {variable.name for variable in model.variables}
        missing = sorted(declared - values.keys())
        unknown = sorted(values.keys() - declared)
        if missing or unknown or duplicates or invalid_rows:
            violations.append(
                _violation(
                    "invalid_variable_vector",
                    "lp.variable_vector",
                    "$.result.variables",
                    "Candidate variable names and finite values do not match the model.",
                    {
                        "missing": missing,
                        "unknown": unknown,
                        "duplicates": sorted(set(duplicates)),
                        "invalid_rows": invalid_rows,
                    },
                )
            )
        return values, row_indexes, violations

    def _validate_bounds(
        self,
        model: LPModel,
        values: dict[str, float],
        row_indexes: dict[str, int],
    ) -> tuple[list[ValidationViolation], float]:
        violations: list[ValidationViolation] = []
        maximum = 0.0
        for variable in model.variables:
            value = values[variable.name]
            bounds = variable.bounds
            for side, limit, raw_violation in (
                ("lower", bounds.lb, None if bounds.lb is None else bounds.lb - value),
                ("upper", bounds.ub, None if bounds.ub is None else value - bounds.ub),
            ):
                if limit is None or raw_violation is None:
                    continue
                violation = max(0.0, float(raw_violation))
                maximum = max(maximum, violation)
                allowed = self._allowed(value, float(limit))
                if violation > allowed:
                    violations.append(
                        _violation(
                            f"{side}_bound_violation",
                            "lp.bounds",
                            f"$.result.variables[{row_indexes[variable.name]}].value",
                            f"Variable '{variable.name}' violates its {side} bound.",
                            {
                                "value": value,
                                "bound": float(limit),
                                "violation": violation,
                                "allowed": allowed,
                            },
                        )
                    )
        return violations, maximum

    def _validate_constraints(
        self,
        model: LPModel,
        values: dict[str, float],
    ) -> tuple[list[ValidationViolation], float]:
        violations: list[ValidationViolation] = []
        maximum = 0.0
        vector = [values[variable.name] for variable in model.variables]
        for index, constraint in enumerate(model.constraints):
            lhs = sum(
                float(coefficient if coefficient is not None else 0.0) * value
                for coefficient, value in zip(constraint.coefs, vector)
            )
            rhs = float(constraint.rhs if constraint.rhs is not None else 0.0)
            if constraint.relation is Relation.LE:
                violation = max(0.0, lhs - rhs)
            elif constraint.relation is Relation.GE:
                violation = max(0.0, rhs - lhs)
            else:
                violation = abs(lhs - rhs)
            maximum = max(maximum, violation)
            allowed = self._allowed(lhs, rhs)
            if violation > allowed:
                violations.append(
                    _violation(
                        "constraint_violation",
                        "lp.constraints",
                        f"$.problem.constraints[{index}]",
                        f"Linear constraint {index} is violated by the candidate.",
                        {
                            "left_hand_side": lhs,
                            "relation": constraint.relation.value,
                            "right_hand_side": rhs,
                            "violation": violation,
                            "allowed": allowed,
                        },
                    )
                )
        return violations, maximum

    def _validate_objective(
        self,
        model: LPModel,
        values: dict[str, float],
        result: dict[str, JsonValue],
    ) -> tuple[ValidationCheck, list[ValidationViolation]]:
        recomputed = float(model.objective.offset) + sum(
            float(coefficient if coefficient is not None else 0.0)
            * values[variable.name]
            for coefficient, variable in zip(model.objective.coefs, model.variables)
        )
        reported = result.get("objective")
        valid_reported = (
            not isinstance(reported, bool)
            and isinstance(reported, (int, float))
            and math.isfinite(float(reported))
        )
        difference = abs(float(reported) - recomputed) if valid_reported else 0.0
        allowed = self._allowed(float(reported), recomputed) if valid_reported else 0.0
        passed = valid_reported and difference <= allowed
        measurements: dict[str, JsonValue] = {
            "reported": float(reported) if valid_reported else None,
            "recomputed": recomputed,
            "absolute_difference": difference,
            "allowed": allowed,
        }
        check = ValidationCheck(
            code="lp.objective",
            status=_check_status(passed),
            description="The reported objective equals the objective recomputed from the candidate.",
            measurements=measurements,
        )
        if passed:
            return check, []
        return check, [
            _violation(
                "objective_mismatch",
                "lp.objective",
                "$.result.objective",
                "Reported and recomputed LP objectives differ.",
                measurements,
            )
        ]

    def _allowed(self, first: float, second: float) -> float:
        return self._absolute_tolerance + self._relative_tolerance * max(
            abs(first),
            abs(second),
        )

    def _report(
        self,
        checks: tuple[ValidationCheck, ...],
        violations: tuple[ValidationViolation, ...],
    ) -> SolutionValidation:
        return SolutionValidation.from_checks(
            checks,
            violations=violations,
            tolerances={
                "absolute": self._absolute_tolerance,
                "relative": self._relative_tolerance,
            },
            limitations=(
                "Feasibility and objective consistency do not independently prove LP optimality.",
                "The validator does not assess whether the model represents the business intent.",
            ),
        )


def _check_status(passed: bool) -> ValidationCheckStatus:
    return ValidationCheckStatus.PASSED if passed else ValidationCheckStatus.FAILED


def _violation(
    code: str,
    check_code: str,
    path: str,
    message: str,
    measurements: dict[str, JsonValue] | None = None,
) -> ValidationViolation:
    return ValidationViolation(
        code=code,
        check_code=check_code,
        path=path,
        message=message,
        measurements=measurements or {},
    )
