from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from optees.application.contracts.json_value import JsonValue, require_json_value


class SolutionValidationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"


class ValidationCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class ValidationCheck:
    code: str
    status: ValidationCheckStatus
    description: str
    measurements: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("validation check code must not be empty")
        if not self.description.strip():
            raise ValueError("validation check description must not be empty")
        require_json_value(self.measurements, path="$.validation.check.measurements")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "code": self.code,
            "status": self.status.value,
            "description": self.description,
            "measurements": self.measurements,
        }


@dataclass(frozen=True)
class ValidationViolation:
    code: str
    check_code: str
    path: str
    message: str
    measurements: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.check_code.strip():
            raise ValueError("validation violation codes must not be empty")
        if not self.path.startswith("$"):
            raise ValueError("validation violation path must be a JSON path")
        if not self.message.strip():
            raise ValueError("validation violation message must not be empty")
        require_json_value(
            self.measurements,
            path="$.validation.violation.measurements",
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "code": self.code,
            "check_code": self.check_code,
            "path": self.path,
            "message": self.message,
            "measurements": self.measurements,
        }


@dataclass(frozen=True)
class SolutionValidation:
    status: SolutionValidationStatus
    checks: tuple[ValidationCheck, ...] = ()
    violations: tuple[ValidationViolation, ...] = ()
    tolerances: dict[str, float] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if not self.contract_version.strip():
            raise ValueError("validation contract_version must not be empty")
        for name, value in self.tolerances.items():
            if not name.strip():
                raise ValueError("validation tolerance name must not be empty")
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("validation tolerances must be finite and non-negative")
        failed_checks = {
            check.code
            for check in self.checks
            if check.status is ValidationCheckStatus.FAILED
        }
        if self.status is SolutionValidationStatus.NOT_AVAILABLE:
            if self.checks or self.violations or not self.limitations:
                raise ValueError(
                    "not_available validation requires only explicit limitations"
                )
        elif not self.checks:
            raise ValueError("available validation must record at least one check")
        elif self.status is SolutionValidationStatus.FAILED:
            if not failed_checks or not self.violations:
                raise ValueError("failed validation requires failed checks and violations")
        elif failed_checks or self.violations:
            raise ValueError("non-failed validation cannot contain failed checks or violations")
        if any(violation.check_code not in failed_checks for violation in self.violations):
            raise ValueError("every violation must reference a failed check")
        require_json_value(self.to_dict(), path="$.validation")

    @classmethod
    def not_available(cls, reason: str) -> "SolutionValidation":
        if not reason.strip():
            raise ValueError("validation unavailability reason must not be empty")
        return cls(
            status=SolutionValidationStatus.NOT_AVAILABLE,
            limitations=(reason,),
        )

    @classmethod
    def from_checks(
        cls,
        checks: tuple[ValidationCheck, ...],
        *,
        violations: tuple[ValidationViolation, ...] = (),
        tolerances: dict[str, float] | None = None,
        limitations: tuple[str, ...] = (),
        partial: bool = False,
    ) -> "SolutionValidation":
        status = (
            SolutionValidationStatus.FAILED
            if any(check.status is ValidationCheckStatus.FAILED for check in checks)
            else SolutionValidationStatus.PARTIAL
            if partial
            else SolutionValidationStatus.VERIFIED
        )
        return cls(
            status=status,
            checks=checks,
            violations=violations,
            tolerances=tolerances or {},
            limitations=limitations,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "status": self.status.value,
            "tolerances": self.tolerances,
            "checks": [check.to_dict() for check in self.checks],
            "violations": [violation.to_dict() for violation in self.violations],
            "limitations": list(self.limitations),
        }
        normalized = require_json_value(payload, path="$.validation")
        assert isinstance(normalized, dict)
        return normalized
