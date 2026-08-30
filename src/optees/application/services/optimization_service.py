from __future__ import annotations

from collections.abc import Callable, Mapping
from time import perf_counter
from typing import TypeAlias
from uuid import uuid4

from optees.application.contracts.capability import ProblemValidation
from optees.application.contracts.errors import (
    ErrorCode,
    ErrorDetail,
    StructuredError,
)
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    ExecutionMetadata,
    JobStatus,
)
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.application.contracts.solution_validation import SolutionValidation
from optees.application.services.capability_registry import CapabilityRegistry
from optees.core.version import get_app_version


ExecutionOutcome: TypeAlias = ExecutionEnvelope | StructuredError
ValidationOutcome: TypeAlias = ProblemValidation | StructuredError


class OptimizationService:
    """Headless in-process facade shared by future CLI and service adapters."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        job_id_factory: Callable[[], str] | None = None,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._registry = registry
        self._job_id_factory = job_id_factory or (lambda: f"job-{uuid4().hex}")
        self._clock = clock

    def list_capabilities(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(descriptor.to_dict() for descriptor in self._registry.descriptors())

    def validate(
        self,
        capability_id: str,
        payload: Mapping[str, object],
        *,
        request_id: str | None = None,
    ) -> ValidationOutcome:
        registration = self._registry.get(capability_id)
        if registration is None:
            return self._capability_not_found(capability_id, request_id=request_id)

        normalized_payload = self._normalize_payload(capability_id, payload, request_id=request_id)
        if isinstance(normalized_payload, StructuredError):
            return normalized_payload

        try:
            registration.parse_problem(normalized_payload)
        except (TypeError, ValueError) as exc:
            return self._validation_error(capability_id, exc, request_id=request_id)

        descriptor = registration.descriptor
        warnings = (
            ("The payload is valid, but the capability is unavailable.",)
            if not descriptor.available
            else ()
        )
        return ProblemValidation(
            capability_id=capability_id,
            problem_schema_version=descriptor.problem_schema_version,
            available=descriptor.available,
            warnings=warnings,
        )

    def solve(
        self,
        capability_id: str,
        payload: Mapping[str, object],
        *,
        request_id: str | None = None,
        job_id: str | None = None,
    ) -> ExecutionOutcome:
        registration = self._registry.get(capability_id)
        if registration is None:
            return self._capability_not_found(capability_id, request_id=request_id)

        descriptor = registration.descriptor
        if not descriptor.available:
            return StructuredError(
                code=ErrorCode.DEPENDENCY_UNAVAILABLE,
                message="The capability is unavailable in this installation.",
                request_id=request_id,
                context={
                    "capability_id": capability_id,
                    "reason": descriptor.unavailable_reason,
                },
            )

        normalized_payload = self._normalize_payload(capability_id, payload, request_id=request_id)
        if isinstance(normalized_payload, StructuredError):
            return normalized_payload

        try:
            model = registration.parse_problem(normalized_payload)
        except (TypeError, ValueError) as exc:
            return self._validation_error(capability_id, exc, request_id=request_id)

        started_at = self._clock()
        try:
            domain_result = registration.execute(model)
            serialized = registration.serialize_result(domain_result)
            elapsed_seconds = max(0.0, self._clock() - started_at)
        except Exception:
            return StructuredError(
                code=ErrorCode.EXECUTION_FAILED,
                message="The capability failed during local execution.",
                request_id=request_id,
                context={"capability_id": capability_id},
            )

        diagnostics: dict[str, object] = dict(serialized.diagnostics)
        diagnostics["backend_id"] = registration.backend_id
        diagnostics["elapsed_seconds"] = elapsed_seconds
        normalized_diagnostics = require_json_value(diagnostics, path="$.diagnostics")
        assert isinstance(normalized_diagnostics, dict)

        validation = SolutionValidation.not_available(
            "No independent validator is registered for this capability."
        )
        if registration.validate_domain_result is not None:
            try:
                validation = registration.validate_domain_result(model, domain_result)
            except Exception:
                validation = SolutionValidation.not_available(
                    "The independent validator failed internally."
                )
        elif registration.validate_result is not None:
            try:
                validation = registration.validate_result(model, serialized)
            except Exception:
                validation = SolutionValidation.not_available(
                    "The independent validator failed internally."
                )

        return ExecutionEnvelope(
            job_id=job_id or self._job_id_factory(),
            capability_id=capability_id,
            job_status=JobStatus.COMPLETED,
            mathematical_status=serialized.mathematical_status,
            termination_reason=serialized.termination_reason,
            result=serialized.result,
            diagnostics=normalized_diagnostics,
            validation=validation,
            warnings=serialized.warnings,
            metadata=ExecutionMetadata(
                optees_version=get_app_version(),
                api_version="v1",
                problem_schema_version=descriptor.problem_schema_version,
                result_schema_version=descriptor.result_schema_version,
            ),
        )

    def supports_cancellation(self, capability_id: str) -> bool:
        registration = self._registry.get(capability_id)
        return bool(
            registration is not None
            and registration.descriptor.supports_cancellation
            and registration.cancel_execution is not None
        )

    def cancel(self, capability_id: str) -> bool:
        registration = self._registry.get(capability_id)
        if registration is None or registration.cancel_execution is None:
            return False
        return bool(registration.cancel_execution())

    @staticmethod
    def _capability_not_found(capability_id: str, *, request_id: str | None) -> StructuredError:
        return StructuredError(
            code=ErrorCode.CAPABILITY_NOT_FOUND,
            message=f"Capability '{capability_id}' is not registered.",
            request_id=request_id,
            context={"capability_id": capability_id},
        )

    @staticmethod
    def _validation_error(
        capability_id: str,
        error: TypeError | ValueError,
        *,
        request_id: str | None,
    ) -> StructuredError:
        return StructuredError(
            code=ErrorCode.VALIDATION_FAILED,
            message="The problem payload is invalid.",
            request_id=request_id,
            details=(
                ErrorDetail(
                    path=str(getattr(error, "path", "$")),
                    message=str(error),
                    code=str(getattr(error, "detail_code", "invalid_value")),
                ),
            ),
            context={"capability_id": capability_id},
        )

    @staticmethod
    def _normalize_payload(
        capability_id: str,
        payload: Mapping[str, object],
        *,
        request_id: str | None,
    ) -> dict[str, JsonValue] | StructuredError:
        if not isinstance(payload, Mapping):
            return StructuredError(
                code=ErrorCode.INVALID_REQUEST,
                message="The problem payload must be a JSON object.",
                request_id=request_id,
                context={"capability_id": capability_id},
            )
        try:
            normalized = require_json_value(dict(payload), path="$")
        except ValueError as exc:
            return StructuredError(
                code=ErrorCode.INVALID_REQUEST,
                message="The problem payload is not strict JSON.",
                request_id=request_id,
                details=(ErrorDetail(path="$", message=str(exc)),),
                context={"capability_id": capability_id},
            )
        assert isinstance(normalized, dict)
        return normalized
