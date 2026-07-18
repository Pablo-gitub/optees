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
from optees.application.validation.lp_solution_validator import (
    LPIndependentSolutionValidator,
)
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.value_objects.milp.integrality import Integrality


class MILPIndependentSolutionValidator:
    """Verify a MILP incumbent independently from backend diagnostics.

    Linear feasibility and objective consistency are delegated to the LP
    validator because a MILP incumbent must first satisfy the same polyhedron.
    The discrete-domain check is then evaluated directly from the public
    candidate: integer values must lie near Z, while binary values must lie
    near either 0 or 1.
    """

    def __init__(
        self,
        *,
        absolute_tolerance: float = 1e-7,
        relative_tolerance: float = 1e-7,
        integrality_tolerance: float = 1e-7,
    ) -> None:
        for value in (
            absolute_tolerance,
            relative_tolerance,
            integrality_tolerance,
        ):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(
                    "MILP validation tolerances must be finite and non-negative"
                )
        self._absolute_tolerance = float(absolute_tolerance)
        self._relative_tolerance = float(relative_tolerance)
        self._integrality_tolerance = float(integrality_tolerance)
        self._linear_validator = LPIndependentSolutionValidator(
            absolute_tolerance=self._absolute_tolerance,
            relative_tolerance=self._relative_tolerance,
        )

    def __call__(
        self,
        model: MILPModel,
        serialized: SerializedResult,
    ) -> SolutionValidation:
        if serialized.mathematical_status not in {
            MathematicalStatus.OPTIMAL,
            MathematicalStatus.FEASIBLE,
        }:
            return SolutionValidation.not_available(
                "No primal incumbent is available for independent MILP validation."
            )

        linear_report = self._linear_validator(model, serialized)  # type: ignore[arg-type]
        checks = [_as_milp_check(check) for check in linear_report.checks]
        violations = [
            _as_milp_violation(violation) for violation in linear_report.violations
        ]

        vector_check = next(
            (check for check in checks if check.code == "milp.variable_vector"),
            None,
        )
        if vector_check is None or vector_check.status is ValidationCheckStatus.FAILED:
            return self._report(tuple(checks), tuple(violations))

        integrality_check, integrality_violations = self._validate_integrality(
            model,
            serialized.result,
        )
        insert_at = next(
            (
                index + 1
                for index, check in enumerate(checks)
                if check.code == "milp.bounds"
            ),
            len(checks),
        )
        checks.insert(insert_at, integrality_check)
        violations.extend(integrality_violations)
        return self._report(tuple(checks), tuple(violations))

    def _validate_integrality(
        self,
        model: MILPModel,
        result: dict[str, JsonValue],
    ) -> tuple[ValidationCheck, list[ValidationViolation]]:
        rows = result["variables"]
        assert isinstance(rows, list)
        indexed_values = {
            row["name"]: (index, float(row["value"]))
            for index, row in enumerate(rows)
            if isinstance(row, dict)
        }
        violations: list[ValidationViolation] = []
        maximum = 0.0
        integer_count = 0
        binary_count = 0

        for variable in model.variables:
            if variable.integrality is Integrality.CONTINUOUS:
                continue
            row_index, value = indexed_values[variable.name]
            if variable.integrality is Integrality.BINARY:
                binary_count += 1
                nearest = 0.0 if abs(value) <= abs(value - 1.0) else 1.0
                code = "binary_domain_violation"
                message = (
                    f"Binary variable '{variable.name}' is not within the "
                    "integrality tolerance of 0 or 1."
                )
            else:
                integer_count += 1
                nearest = float(round(value))
                code = "integrality_violation"
                message = (
                    f"Integer variable '{variable.name}' is not within the "
                    "integrality tolerance of an integer."
                )
            distance = abs(value - nearest)
            maximum = max(maximum, distance)
            if distance > self._integrality_tolerance:
                violations.append(
                    ValidationViolation(
                        code=code,
                        check_code="milp.integrality",
                        path=f"$.result.variables[{row_index}].value",
                        message=message,
                        measurements={
                            "value": value,
                            "nearest_domain_value": nearest,
                            "distance": distance,
                            "allowed": self._integrality_tolerance,
                        },
                    )
                )

        check = ValidationCheck(
            code="milp.integrality",
            status=(
                ValidationCheckStatus.PASSED
                if not violations
                else ValidationCheckStatus.FAILED
            ),
            description=(
                "Every integer and binary candidate value satisfies its declared "
                "discrete domain."
            ),
            measurements={
                "integer_variable_count": integer_count,
                "binary_variable_count": binary_count,
                "maximum_distance": maximum,
            },
        )
        return check, violations

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
                "integrality": self._integrality_tolerance,
            },
            limitations=(
                "Feasibility, integrality, and objective consistency do not "
                "independently prove MILP optimality.",
                "The validator does not assess whether the model represents the "
                "business intent.",
            ),
        )


def _as_milp_check(check: ValidationCheck) -> ValidationCheck:
    return ValidationCheck(
        code=check.code.replace("lp.", "milp.", 1),
        status=check.status,
        description=check.description.replace("LP", "MILP"),
        measurements=check.measurements,
    )


def _as_milp_violation(violation: ValidationViolation) -> ValidationViolation:
    return ValidationViolation(
        code=violation.code,
        check_code=violation.check_code.replace("lp.", "milp.", 1),
        path=violation.path,
        message=violation.message.replace("LP", "MILP"),
        measurements=violation.measurements,
    )
