from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import Field

from optees.application.codecs.artifact_request_codec import (
    artifact_batch_request_from_dict,
)
from optees.application.codecs.report_request_codec import report_request_from_dict
from optees.application.contracts.batch import BatchItemRequest, BatchRequest
from optees.application.contracts.artifact import ArtifactStatus
from optees.application.contracts.errors import StructuredError
from optees.application.contracts.json_value import require_json_value
from optees.application.services.artifact_generation_service import (
    ArtifactGenerationService,
)
from optees.application.services.local_job_service import LocalJobService
from optees.application.services.report_composition_service import (
    ReportCompositionService,
)


class LocalMcpToolFacade:
    """Stateful MCP facade enforcing discovery before validated execution."""

    def __init__(
        self,
        job_service: LocalJobService,
        artifact_service: ArtifactGenerationService | None = None,
        report_service: ReportCompositionService | None = None,
    ) -> None:
        self._jobs = job_service
        self._artifacts = artifact_service
        self._reports = report_service
        self._described_capabilities: set[str] = set()
        self._validated_problems: set[str] = set()
        self._validated_batches: set[str] = set()

    def list_capabilities(self) -> dict[str, object]:
        summaries = []
        for descriptor in self._jobs.list_capabilities():
            summaries.append(
                {
                    key: descriptor.get(key)
                    for key in (
                        "id",
                        "title",
                        "problem_type",
                        "available",
                        "problem_schema_version",
                        "result_schema_version",
                    )
                }
            )
        return {"ok": True, "capabilities": summaries}

    def get_capability(self, capability_id: str) -> dict[str, object]:
        descriptor = next(
            (
                item
                for item in self._jobs.list_capabilities()
                if item.get("id") == capability_id
            ),
            None,
        )
        if descriptor is None:
            return _tool_error(
                "capability_not_found",
                f"Capability '{capability_id}' is not registered.",
            )
        self._described_capabilities.add(capability_id)
        return {"ok": True, "capability": descriptor}

    def validate_problem(
        self,
        capability_id: str,
        problem: dict[str, Any],
    ) -> dict[str, object]:
        if capability_id not in self._described_capabilities:
            return _tool_error(
                "capability_not_inspected",
                "Call optees_get_capability before validating a problem.",
            )
        outcome = self._jobs.validate(capability_id, problem)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        validation = outcome.to_dict()
        if validation.get("valid") is True and validation.get("available") is True:
            self._validated_problems.add(_problem_key(capability_id, problem))
        return {"ok": True, "validation": validation}

    def create_job(
        self,
        capability_id: str,
        problem: dict[str, Any],
    ) -> dict[str, object]:
        if _problem_key(capability_id, problem) not in self._validated_problems:
            return _tool_error(
                "problem_not_validated",
                "Validate this exact capability and problem before creating a job.",
            )
        outcome = self._jobs.submit(capability_id, problem)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "job": outcome.to_dict()}

    def get_job_status(self, job_id: str) -> dict[str, object]:
        outcome = self._jobs.get(job_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "job": outcome.to_dict()}

    def get_job_result(self, job_id: str) -> dict[str, object]:
        outcome = self._jobs.result(job_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "result": outcome.to_dict()}

    def cancel_job(self, job_id: str) -> dict[str, object]:
        outcome = self._jobs.cancel(job_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "job": outcome.to_dict()}

    def validate_batch(
        self,
        version: str,
        items: list[dict[str, Any]],
    ) -> dict[str, object]:
        try:
            request = _batch_request(version, items)
        except ValueError as exc:
            return _tool_error("invalid_batch_request", str(exc))
        missing = sorted(
            {
                item.capability_id
                for item in request.items
                if item.capability_id not in self._described_capabilities
            }
        )
        if missing:
            return _tool_error(
                "capability_not_inspected",
                "Inspect every batch capability before validating the batch.",
                {"capability_ids": missing},
            )
        validation = self._jobs.validate_batch(request)
        if validation.valid:
            self._validated_batches.add(_batch_key(request))
        return {"ok": True, "validation": validation.to_dict()}

    def create_batch(
        self,
        version: str,
        items: list[dict[str, Any]],
    ) -> dict[str, object]:
        try:
            request = _batch_request(version, items)
        except ValueError as exc:
            return _tool_error("invalid_batch_request", str(exc))
        if _batch_key(request) not in self._validated_batches:
            return _tool_error(
                "batch_not_validated",
                "Validate this exact versioned batch before creating it.",
            )
        outcome = self._jobs.submit_batch(request)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "batch": outcome.to_dict()}

    def get_batch_status(self, batch_id: str) -> dict[str, object]:
        outcome = self._jobs.get_batch(batch_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "batch": outcome.to_dict()}

    def get_batch_result(self, batch_id: str) -> dict[str, object]:
        outcome = self._jobs.batch_result(batch_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "batch_result": outcome.to_dict()}

    def cancel_batch(self, batch_id: str) -> dict[str, object]:
        outcome = self._jobs.cancel_batch(batch_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()}
        return {"ok": True, "batch": outcome.to_dict()}

    def list_result_artifacts(self, job_id: str) -> dict[str, object]:
        if self._artifacts is None:
            return _tool_error(
                "artifact_service_unavailable",
                "Artifact generation is not configured for this MCP session.",
            )
        snapshot = self._jobs.get(job_id)
        if isinstance(snapshot, StructuredError):
            return {"ok": False, "error": snapshot.to_dict()["error"]}
        descriptor = next(
            (
                item
                for item in self._jobs.list_capabilities()
                if item.get("id") == snapshot.capability_id
            ),
            None,
        )
        batches = self._artifacts.list_for_job(job_id)
        if isinstance(batches, StructuredError):
            return {"ok": False, "error": batches.to_dict()["error"]}
        return {
            "ok": True,
            "job_id": job_id,
            "capability_id": snapshot.capability_id,
            "available_artifacts": (
                descriptor.get("available_artifacts", [])
                if descriptor is not None
                else []
            ),
            "artifact_batches": [batch.to_dict() for batch in batches],
            "content_policy": {
                "embedded_by_default": False,
                "retrieval": "Read optees-artifact://{artifact_id} explicitly.",
            },
        }

    def render_result_artifacts(
        self,
        job_id: str,
        requests: list[dict[str, Any]],
        *,
        contract_version: str = "1",
    ) -> dict[str, object]:
        if self._artifacts is None:
            return _tool_error(
                "artifact_service_unavailable",
                "Artifact generation is not configured for this MCP session.",
            )
        try:
            request = artifact_batch_request_from_dict(
                requests,
                contract_version=contract_version,
            )
        except ValueError as exc:
            return _tool_error("artifact_request_invalid", str(exc))
        outcome = self._artifacts.submit(job_id, request)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()["error"]}
        return {
            "ok": True,
            "artifact_batch": outcome.to_dict(),
            "content_policy": {
                "embedded_by_default": False,
                "next_step": (
                    "Poll optees_list_result_artifacts, then inspect metadata with "
                    "optees_get_artifact before explicitly reading its resource URI."
                ),
            },
        }

    def get_artifact(self, artifact_id: str) -> dict[str, object]:
        if self._artifacts is None:
            return _tool_error(
                "artifact_service_unavailable",
                "Artifact generation is not configured for this MCP session.",
            )
        outcome = self._artifacts.manifest_entry(artifact_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()["error"]}
        payload: dict[str, object] = {
            "ok": True,
            "artifact": outcome.to_dict(),
            "content_included": False,
        }
        if outcome.status is ArtifactStatus.AVAILABLE:
            payload["resource_uri"] = f"optees-artifact://{outcome.artifact_id}"
            payload["retrieval_instruction"] = (
                "Read the resource URI only when the user needs the file content. "
                "Binary bytes are never inserted by this metadata tool."
            )
        return payload

    def cancel_artifact(self, artifact_id: str) -> dict[str, object]:
        if self._artifacts is None:
            return _tool_error(
                "artifact_service_unavailable",
                "Artifact generation is not configured for this MCP session.",
            )
        outcome = self._artifacts.cancel(artifact_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()["error"]}
        return {"ok": True, "artifact": outcome.to_dict()}

    def read_artifact_resource(self, artifact_id: str) -> bytes:
        if self._artifacts is None:
            raise ValueError("artifact service is unavailable")
        outcome = self._artifacts.download(artifact_id)
        if isinstance(outcome, StructuredError):
            raise ValueError(outcome.message)
        return outcome.content

    def compose_report(self, request: dict[str, Any]) -> dict[str, object]:
        if self._reports is None:
            return _tool_error(
                "report_service_unavailable",
                "Report composition is not configured for this MCP session.",
            )
        try:
            parsed = report_request_from_dict(request)
        except ValueError as exc:
            return _tool_error("report_request_invalid", str(exc))
        outcome = self._reports.submit(parsed)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()["error"]}
        return {
            "ok": True,
            "report": outcome.to_dict(),
            "content_policy": {
                "embedded_by_default": False,
                "next_step": (
                    "Poll optees_get_report_status, then inspect metadata with "
                    "optees_get_report before explicitly reading its resource URI."
                ),
            },
        }

    def get_report_backends(self) -> dict[str, object]:
        if self._reports is None:
            return _tool_error(
                "report_service_unavailable",
                "Report composition is not configured for this MCP session.",
            )
        return {
            "ok": True,
            "backends": [
                diagnostic.to_dict()
                for diagnostic in self._reports.backend_diagnostics()
            ],
        }

    def cancel_report(self, report_id: str) -> dict[str, object]:
        if self._reports is None:
            return _tool_error(
                "report_service_unavailable",
                "Report composition is not configured for this MCP session.",
            )
        outcome = self._reports.cancel(report_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()["error"]}
        return {"ok": True, "report": outcome.to_dict()}

    def get_report_status(self, report_id: str) -> dict[str, object]:
        if self._reports is None:
            return _tool_error(
                "report_service_unavailable",
                "Report composition is not configured for this MCP session.",
            )
        outcome = self._reports.get(report_id)
        if isinstance(outcome, StructuredError):
            return {"ok": False, "error": outcome.to_dict()["error"]}
        return {"ok": True, "report": outcome.to_dict()}

    def get_report(self, report_id: str) -> dict[str, object]:
        status = self.get_report_status(report_id)
        if status.get("ok") is not True:
            return status
        report = status["report"]
        assert isinstance(report, dict)
        payload: dict[str, object] = {
            "ok": True,
            "report": report,
            "content_included": False,
        }
        if report.get("status") == "available":
            payload["resource_uri"] = f"optees-report://{report_id}"
            payload["retrieval_instruction"] = (
                "Read the resource URI only when the user needs the report bytes; "
                "inspect media_type first."
            )
        return payload

    def read_report_resource(self, report_id: str) -> bytes:
        if self._reports is None:
            raise ValueError("report service is unavailable")
        outcome = self._reports.download(report_id)
        if isinstance(outcome, StructuredError):
            raise ValueError(outcome.message)
        return outcome.content


def create_mcp_server(
    job_service: LocalJobService,
    artifact_service: ArtifactGenerationService | None = None,
    report_service: ReportCompositionService | None = None,
):
    """Create the stdio MCP server without starting or owning the job service."""

    from mcp.server.fastmcp import FastMCP

    facade = LocalMcpToolFacade(job_service, artifact_service, report_service)
    server = FastMCP(
        "Optees Local Solver",
        instructions=(
            "Inspect a capability before formulating a problem. Validate the exact "
            "versioned payload before creating a job. Use batch tools for independent "
            "repeated scenarios instead of coordinating many individual jobs. Report "
            "mathematical status and independent validation separately, and never "
            "invent missing data. Artifact tools return metadata only by default; "
            "read an artifact resource explicitly only when its bytes are needed."
            " Report composition accepts only bounded Markdown, job status, and "
            "artifact references; report tools also return metadata by default."
        ),
        log_level="WARNING",
        json_response=True,
    )

    @server.tool(
        name="optees_list_capabilities",
        description="List available Optees solver capabilities and contract versions.",
        structured_output=True,
    )
    def optees_list_capabilities() -> dict[str, object]:
        return facade.list_capabilities()

    @server.tool(
        name="optees_get_capability",
        description="Get the complete descriptor and JSON schemas for one capability.",
        structured_output=True,
    )
    def optees_get_capability(capability_id: str) -> dict[str, object]:
        return facade.get_capability(capability_id)

    @server.tool(
        name="optees_validate_problem",
        description="Validate a versioned problem without running its solver.",
        structured_output=True,
    )
    def optees_validate_problem(
        capability_id: str,
        problem: dict[str, Any],
    ) -> dict[str, object]:
        return facade.validate_problem(capability_id, problem)

    @server.tool(
        name="optees_create_job",
        description="Create a solver job only after the identical problem validates.",
        structured_output=True,
    )
    def optees_create_job(
        capability_id: str,
        problem: dict[str, Any],
    ) -> dict[str, object]:
        return facade.create_job(capability_id, problem)

    @server.tool(
        name="optees_get_job_status",
        description="Get lifecycle and mathematical status for an Optees job.",
        structured_output=True,
    )
    def optees_get_job_status(job_id: str) -> dict[str, object]:
        return facade.get_job_status(job_id)

    @server.tool(
        name="optees_get_job_result",
        description=(
            "Get a completed job result and its independent validation report."
        ),
        structured_output=True,
    )
    def optees_get_job_result(job_id: str) -> dict[str, object]:
        return facade.get_job_result(job_id)

    @server.tool(
        name="optees_cancel_job",
        description="Request cancellation of an Optees job.",
        structured_output=True,
    )
    def optees_cancel_job(job_id: str) -> dict[str, object]:
        return facade.cancel_job(job_id)

    @server.tool(
        name="optees_validate_batch",
        description=(
            "Validate up to 32 versioned problems together without running solvers."
        ),
        structured_output=True,
    )
    def optees_validate_batch(
        items: Annotated[list[dict[str, Any]], Field(min_length=1, max_length=32)],
        version: str = "1",
    ) -> dict[str, object]:
        return facade.validate_batch(version, items)

    @server.tool(
        name="optees_create_batch",
        description=(
            "Atomically submit an identical previously validated batch. Every item "
            "retains its own job and independent validation."
        ),
        structured_output=True,
    )
    def optees_create_batch(
        items: Annotated[list[dict[str, Any]], Field(min_length=1, max_length=32)],
        version: str = "1",
    ) -> dict[str, object]:
        return facade.create_batch(version, items)

    @server.tool(
        name="optees_get_batch_status",
        description="Get aggregate and per-item lifecycle status for a batch.",
        structured_output=True,
    )
    def optees_get_batch_status(batch_id: str) -> dict[str, object]:
        return facade.get_batch_status(batch_id)

    @server.tool(
        name="optees_get_batch_result",
        description=(
            "Get every completed item result, independent validation, and aggregate "
            "status counts for a batch."
        ),
        structured_output=True,
    )
    def optees_get_batch_result(batch_id: str) -> dict[str, object]:
        return facade.get_batch_result(batch_id)

    @server.tool(
        name="optees_cancel_batch",
        description="Request cancellation for every active item in a batch.",
        structured_output=True,
    )
    def optees_cancel_batch(batch_id: str) -> dict[str, object]:
        return facade.cancel_batch(batch_id)

    @server.tool(
        name="optees_list_result_artifacts",
        description=(
            "Discover artifact types supported by a job's capability and list every "
            "artifact batch already requested for that job. Example: call this after "
            "a completed job before choosing a table, chart, or 3D export."
        ),
        structured_output=True,
    )
    def optees_list_result_artifacts(job_id: str) -> dict[str, object]:
        return facade.list_result_artifacts(job_id)

    @server.tool(
        name="optees_render_result_artifacts",
        description=(
            "Request bounded result artifacts for a completed job. Pass only types, "
            "formats, and options advertised by optees_list_result_artifacts. The "
            "response contains manifests, never binary content."
        ),
        structured_output=True,
    )
    def optees_render_result_artifacts(
        job_id: str,
        requests: Annotated[
            list[dict[str, Any]],
            Field(min_length=1, max_length=8),
        ],
        contract_version: str = "1",
    ) -> dict[str, object]:
        return facade.render_result_artifacts(
            job_id,
            requests,
            contract_version=contract_version,
        )

    @server.tool(
        name="optees_get_artifact",
        description=(
            "Inspect one artifact manifest and obtain its explicit resource URI. "
            "This metadata-only tool never inserts file bytes into model context."
        ),
        structured_output=True,
    )
    def optees_get_artifact(artifact_id: str) -> dict[str, object]:
        return facade.get_artifact(artifact_id)

    @server.tool(
        name="optees_cancel_artifact",
        description="Request cancellation of one queued or rendering artifact.",
        structured_output=True,
    )
    def optees_cancel_artifact(artifact_id: str) -> dict[str, object]:
        return facade.cancel_artifact(artifact_id)

    @server.resource(
        "optees-artifact://{artifact_id}",
        name="Optees result artifact",
        description=(
            "Explicitly retrieve one bounded, verified artifact by opaque ID. Read "
            "only after inspecting its media type and size with optees_get_artifact."
        ),
        mime_type="application/octet-stream",
    )
    def optees_artifact_resource(artifact_id: str) -> bytes:
        return facade.read_artifact_resource(artifact_id)

    @server.tool(
        name="optees_compose_report",
        description=(
            "Compose a bounded deterministic Markdown or optional PDF report from "
            "safe Markdown, Optees job statuses, and existing result artifact IDs."
        ),
        structured_output=True,
    )
    def optees_compose_report(request: dict[str, Any]) -> dict[str, object]:
        return facade.compose_report(request)

    @server.tool(
        name="optees_get_report_backends",
        description=(
            "Inspect optional local report backend availability and versions before "
            "requesting PDF output."
        ),
        structured_output=True,
    )
    def optees_get_report_backends() -> dict[str, object]:
        return facade.get_report_backends()

    @server.tool(
        name="optees_cancel_report",
        description="Request cancellation of one queued or composing report.",
        structured_output=True,
    )
    def optees_cancel_report(report_id: str) -> dict[str, object]:
        return facade.cancel_report(report_id)

    @server.tool(
        name="optees_get_report_status",
        description="Poll lifecycle and provenance metadata for one report.",
        structured_output=True,
    )
    def optees_get_report_status(report_id: str) -> dict[str, object]:
        return facade.get_report_status(report_id)

    @server.tool(
        name="optees_get_report",
        description=(
            "Inspect one report manifest and obtain its explicit resource URI. "
            "This metadata-only tool never inserts report content into context."
        ),
        structured_output=True,
    )
    def optees_get_report(report_id: str) -> dict[str, object]:
        return facade.get_report(report_id)

    @server.resource(
        "optees-report://{report_id}",
        name="Optees report",
        description=(
            "Explicitly retrieve one bounded, verified report by opaque ID after "
            "inspecting its media type."
        ),
        mime_type="application/octet-stream",
    )
    def optees_report_resource(report_id: str) -> bytes:
        return facade.read_report_resource(report_id)

    return server


def _problem_key(capability_id: str, problem: Mapping[str, object]) -> str:
    canonical = json.dumps(
        problem,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{capability_id}:{digest}"


def _batch_request(
    version: str,
    items: list[dict[str, Any]],
) -> BatchRequest:
    requests = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("every batch item must be an object")
        client_item_id = item.get("client_item_id")
        capability_id = item.get("capability_id")
        problem = item.get("problem")
        if not isinstance(client_item_id, str):
            raise ValueError("batch client_item_id must be a string")
        if not isinstance(capability_id, str):
            raise ValueError("batch capability_id must be a string")
        normalized = require_json_value(problem, path="$.batch.items[].problem")
        if not isinstance(normalized, dict):
            raise ValueError("batch problem must be an object")
        requests.append(
            BatchItemRequest(client_item_id, capability_id, normalized)
        )
    return BatchRequest(tuple(requests), version=version)


def _batch_key(request: BatchRequest) -> str:
    canonical = json.dumps(
        request.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _tool_error(
    code: str,
    message: str,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    error: dict[str, object] = {
        "code": code,
        "message": message,
    }
    if context:
        error["context"] = context
    return {
        "ok": False,
        "error": error,
    }
