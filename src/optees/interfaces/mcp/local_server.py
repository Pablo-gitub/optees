from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import Field

from optees.application.contracts.batch import BatchItemRequest, BatchRequest
from optees.application.contracts.errors import StructuredError
from optees.application.contracts.json_value import require_json_value
from optees.application.services.local_job_service import LocalJobService


class LocalMcpToolFacade:
    """Stateful MCP facade enforcing discovery before validated execution."""

    def __init__(self, job_service: LocalJobService) -> None:
        self._jobs = job_service
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


def create_mcp_server(job_service: LocalJobService):
    """Create the stdio MCP server without starting or owning the job service."""

    from mcp.server.fastmcp import FastMCP

    facade = LocalMcpToolFacade(job_service)
    server = FastMCP(
        "Optees Local Solver",
        instructions=(
            "Inspect a capability before formulating a problem. Validate the exact "
            "versioned payload before creating a job. Use batch tools for independent "
            "repeated scenarios instead of coordinating many individual jobs. Report "
            "mathematical status and independent validation separately, and never "
            "invent missing data."
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
