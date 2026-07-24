from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from collections.abc import Callable
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


JsonObject = dict[str, object]


class JsonTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: JsonObject | None = None,
        timeout: float = 30.0,
    ) -> JsonObject: ...


class RemoteApiError(RuntimeError):
    def __init__(self, status_code: int | None, payload: JsonObject) -> None:
        super().__init__(str(payload.get("message", "Remote API request failed.")))
        self.status_code = status_code
        self.payload = payload


class UrllibJsonTransport:
    """Small JSON transport with no provider-specific runtime dependency."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: JsonObject | None = None,
        timeout: float = 30.0,
    ) -> JsonObject:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = {"Accept": "application/json", **(headers or {})}
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return _json_object(response.read())
        except HTTPError as exc:
            raise RemoteApiError(exc.code, _error_payload(exc.read())) from exc
        except URLError as exc:
            raise RemoteApiError(
                None,
                {"code": "connection_failed", "message": str(exc.reason)},
            ) from exc


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        transport: JsonTransport | None = None,
        timeout: float = 120.0,
        think: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport or UrllibJsonTransport()
        self._timeout = timeout
        self._think = bool(think)

    def model_info(self, model: str) -> JsonObject:
        payload = self._transport.request(
            "GET",
            f"{self._base_url}/api/tags",
            timeout=self._timeout,
        )
        models = payload.get("models")
        if not isinstance(models, list):
            raise RuntimeError("Ollama returned an invalid model catalogue.")
        for item in models:
            if isinstance(item, dict) and item.get("name") == model:
                capabilities = item.get("capabilities")
                if not isinstance(capabilities, list) or "tools" not in capabilities:
                    raise ValueError(f"Ollama model '{model}' does not support tools.")
                return item
        raise ValueError(f"Ollama model '{model}' is not installed.")

    def chat(
        self,
        *,
        model: str,
        messages: list[JsonObject],
        tools: list[JsonObject],
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            f"{self._base_url}/api/chat",
            payload={
                "model": model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "think": self._think,
            },
            timeout=self._timeout,
        )


class OpteesToolFacade:
    """Allowlisted REST tools with deterministic orchestration safeguards."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        transport: JsonTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if len(token) < 32:
            raise ValueError("The Optees bearer token must contain at least 32 characters.")
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._transport = transport or UrllibJsonTransport()
        self._timeout = timeout
        self._described_capabilities: set[str] = set()
        self._validated_problems: set[str] = set()
        self._validated_batches: set[str] = set()

    @property
    def tool_definitions(self) -> list[JsonObject]:
        problem_properties = {
            "capability_id": {"type": "string"},
            "problem": {"type": "object", "additionalProperties": True},
        }
        batch_properties = {
            "version": {"type": "string", "enum": ["1"]},
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "items": {
                    "type": "object",
                    "properties": {
                        "client_item_id": {"type": "string"},
                        "capability_id": {"type": "string"},
                        "problem": {
                            "type": "object",
                            "additionalProperties": True,
                        },
                    },
                    "required": [
                        "client_item_id",
                        "capability_id",
                        "problem",
                    ],
                    "additionalProperties": False,
                },
            },
        }
        artifact_request_properties = {
            "job_id": {"type": "string"},
            "contract_version": {"type": "string", "enum": ["1"]},
            "requests": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "artifact_type": {"type": "string"},
                        "formats": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                        "options": {
                            "type": "object",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["artifact_type", "formats"],
                    "additionalProperties": False,
                },
            },
        }
        report_request_properties = {
            "contract_version": {"type": "string", "enum": ["1"]},
            "format": {"type": "string", "enum": ["markdown", "pdf"]},
            "locale": {"type": "string", "enum": ["en", "it"]},
            "title": {"type": "string"},
            "sections": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "items": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "heading": {"type": "string"},
                        "blocks": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "markdown",
                                            "job_status",
                                            "artifact",
                                        ],
                                    },
                                    "value": {"type": "string"},
                                    "caption": {"type": "string"},
                                    "views": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "enum": [
                                                "isometric",
                                                "front",
                                                "side",
                                                "top",
                                            ],
                                        },
                                    },
                                },
                                "required": ["type", "value"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["section_id", "heading", "blocks"],
                    "additionalProperties": False,
                },
            },
            "metadata": {
                "type": "object",
                "additionalProperties": True,
            },
        }
        return [
            _tool(
                "optees_list_capabilities",
                "List available Optees solver capabilities and contract versions.",
                {},
                [],
            ),
            _tool(
                "optees_get_capability",
                "Get the complete descriptor and JSON schemas for one capability.",
                {"capability_id": {"type": "string"}},
                ["capability_id"],
            ),
            _tool(
                "optees_validate_problem",
                "Validate a versioned problem without running its solver.",
                problem_properties,
                ["capability_id", "problem"],
            ),
            _tool(
                "optees_create_job",
                "Create a solver job only after the identical problem validates.",
                problem_properties,
                ["capability_id", "problem"],
            ),
            _tool(
                "optees_get_job_status",
                "Get lifecycle and mathematical status for an Optees job.",
                {"job_id": {"type": "string"}},
                ["job_id"],
            ),
            _tool(
                "optees_get_job_result",
                "Get a completed job result and its independent validation report.",
                {"job_id": {"type": "string"}},
                ["job_id"],
            ),
            _tool(
                "optees_cancel_job",
                "Request cancellation of an Optees job.",
                {"job_id": {"type": "string"}},
                ["job_id"],
            ),
            _tool(
                "optees_validate_batch",
                "Validate up to 32 problems in one request without running them.",
                batch_properties,
                ["version", "items"],
            ),
            _tool(
                "optees_create_batch",
                (
                    "Atomically submit an identical validated batch while preserving "
                    "one job and validation report per item."
                ),
                batch_properties,
                ["version", "items"],
            ),
            _tool(
                "optees_get_batch_status",
                "Get aggregate and per-item lifecycle status for a batch.",
                {"batch_id": {"type": "string"}},
                ["batch_id"],
            ),
            _tool(
                "optees_get_batch_result",
                "Get all item results, validations, and aggregate counts for a batch.",
                {"batch_id": {"type": "string"}},
                ["batch_id"],
            ),
            _tool(
                "optees_cancel_batch",
                "Request cancellation for every active item in a batch.",
                {"batch_id": {"type": "string"}},
                ["batch_id"],
            ),
            _tool(
                "optees_list_result_artifacts",
                (
                    "List artifact types supported by a completed job and metadata "
                    "for prior artifact batches. No file bytes are returned."
                ),
                {"job_id": {"type": "string"}},
                ["job_id"],
            ),
            _tool(
                "optees_render_result_artifacts",
                (
                    "Request up to eight bounded artifacts using only types, formats, "
                    "and options advertised by optees_list_result_artifacts."
                ),
                artifact_request_properties,
                ["job_id", "requests"],
            ),
            _tool(
                "optees_cancel_artifact",
                "Request cancellation of one queued or rendering artifact.",
                {"artifact_id": {"type": "string"}},
                ["artifact_id"],
            ),
            _tool(
                "optees_get_report_backends",
                (
                    "Inspect local report backend availability before requesting PDF. "
                    "Markdown reports need no external backend."
                ),
                {},
                [],
            ),
            _tool(
                "optees_compose_report",
                (
                    "Compose a bounded Markdown or PDF report from safe Markdown, "
                    "job status, and existing artifact blocks. No bytes are returned."
                ),
                report_request_properties,
                [
                    "contract_version",
                    "format",
                    "locale",
                    "title",
                    "sections",
                ],
            ),
            _tool(
                "optees_get_report_status",
                (
                    "Poll report status and metadata. An available report includes "
                    "its authenticated relative download endpoint."
                ),
                {"report_id": {"type": "string"}},
                ["report_id"],
            ),
            _tool(
                "optees_cancel_report",
                "Request cancellation of one queued or composing report.",
                {"report_id": {"type": "string"}},
                ["report_id"],
            ),
        ]

    def execute(self, name: str, arguments: JsonObject) -> JsonObject:
        handlers = {
            "optees_list_capabilities": self._list_capabilities,
            "optees_get_capability": self._get_capability,
            "optees_validate_problem": self._validate_problem,
            "optees_create_job": self._create_job,
            "optees_get_job_status": self._get_job_status,
            "optees_get_job_result": self._get_job_result,
            "optees_cancel_job": self._cancel_job,
            "optees_validate_batch": self._validate_batch,
            "optees_create_batch": self._create_batch,
            "optees_get_batch_status": self._get_batch_status,
            "optees_get_batch_result": self._get_batch_result,
            "optees_cancel_batch": self._cancel_batch,
            "optees_list_result_artifacts": self._list_result_artifacts,
            "optees_render_result_artifacts": self._render_result_artifacts,
            "optees_cancel_artifact": self._cancel_artifact,
            "optees_get_report_backends": self._get_report_backends,
            "optees_compose_report": self._compose_report,
            "optees_get_report_status": self._get_report_status,
            "optees_cancel_report": self._cancel_report,
        }
        handler = handlers.get(name)
        if handler is None:
            return _tool_error("unsupported_tool", f"Tool '{name}' is not allowlisted.")
        try:
            return handler(arguments)
        except (KeyError, TypeError, ValueError) as exc:
            return _tool_error("invalid_tool_arguments", str(exc))
        except RemoteApiError as exc:
            return {
                "ok": False,
                "http_status": exc.status_code,
                "error": exc.payload,
            }

    def reset_session(self) -> None:
        """Forget discovery and validation evidence between independent prompts."""
        self._described_capabilities.clear()
        self._validated_problems.clear()
        self._validated_batches.clear()

    def _list_capabilities(self, _arguments: JsonObject) -> JsonObject:
        response = self._request("GET", "/api/v1/capabilities")
        capabilities = response.get("capabilities")
        if not isinstance(capabilities, list):
            raise ValueError("Optees returned an invalid capability catalogue.")
        summaries = []
        for item in capabilities:
            if not isinstance(item, dict):
                continue
            summaries.append(
                {
                    key: item.get(key)
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

    def _get_capability(self, arguments: JsonObject) -> JsonObject:
        capability_id = _required_string(arguments, "capability_id")
        response = self._request(
            "GET",
            f"/api/v1/capabilities/{quote(capability_id, safe='')}",
        )
        self._described_capabilities.add(capability_id)
        return {"ok": True, "capability": response}

    def _validate_problem(self, arguments: JsonObject) -> JsonObject:
        capability_id, problem = self._problem_arguments(arguments)
        if capability_id not in self._described_capabilities:
            return _tool_error(
                "capability_not_inspected",
                "Call optees_get_capability before validating a problem.",
            )
        response = self._request(
            "POST",
            "/api/v1/problems/validate",
            {"capability_id": capability_id, "problem": problem},
        )
        if response.get("valid") is True and response.get("available") is True:
            self._validated_problems.add(_problem_key(capability_id, problem))
        return {"ok": True, "validation": response}

    def _create_job(self, arguments: JsonObject) -> JsonObject:
        capability_id, problem = self._problem_arguments(arguments)
        if _problem_key(capability_id, problem) not in self._validated_problems:
            return _tool_error(
                "problem_not_validated",
                "Validate this exact capability and problem before creating a job.",
            )
        response = self._request(
            "POST",
            "/api/v1/jobs",
            {"capability_id": capability_id, "problem": problem},
        )
        return {"ok": True, "job": response}

    def _get_job_status(self, arguments: JsonObject) -> JsonObject:
        job_id = _required_string(arguments, "job_id")
        response = self._request("GET", f"/api/v1/jobs/{quote(job_id, safe='')}")
        return {"ok": True, "job": response}

    def _get_job_result(self, arguments: JsonObject) -> JsonObject:
        job_id = _required_string(arguments, "job_id")
        response = self._request(
            "GET",
            f"/api/v1/jobs/{quote(job_id, safe='')}/result",
        )
        return {"ok": True, "result": response}

    def _cancel_job(self, arguments: JsonObject) -> JsonObject:
        job_id = _required_string(arguments, "job_id")
        response = self._request(
            "POST",
            f"/api/v1/jobs/{quote(job_id, safe='')}/cancel",
            {},
        )
        return {"ok": True, "job": response}

    def _validate_batch(self, arguments: JsonObject) -> JsonObject:
        version, items = self._batch_arguments(arguments)
        missing = sorted(
            {
                str(item["capability_id"])
                for item in items
                if item["capability_id"] not in self._described_capabilities
            }
        )
        if missing:
            return _tool_error(
                "capability_not_inspected",
                "Inspect every batch capability before validating the batch.",
            )
        payload = {"version": version, "items": items}
        response = self._request("POST", "/api/v1/batches/validate", payload)
        if response.get("valid") is True:
            self._validated_batches.add(_batch_key(payload))
        return {"ok": True, "validation": response}

    def _create_batch(self, arguments: JsonObject) -> JsonObject:
        version, items = self._batch_arguments(arguments)
        payload = {"version": version, "items": items}
        if _batch_key(payload) not in self._validated_batches:
            return _tool_error(
                "batch_not_validated",
                "Validate this exact versioned batch before creating it.",
            )
        response = self._request("POST", "/api/v1/batches", payload)
        return {"ok": True, "batch": response}

    def _get_batch_status(self, arguments: JsonObject) -> JsonObject:
        batch_id = _required_string(arguments, "batch_id")
        response = self._request(
            "GET",
            f"/api/v1/batches/{quote(batch_id, safe='')}",
        )
        return {"ok": True, "batch": response}

    def _get_batch_result(self, arguments: JsonObject) -> JsonObject:
        batch_id = _required_string(arguments, "batch_id")
        response = self._request(
            "GET",
            f"/api/v1/batches/{quote(batch_id, safe='')}/result",
        )
        return {"ok": True, "batch_result": response}

    def _cancel_batch(self, arguments: JsonObject) -> JsonObject:
        batch_id = _required_string(arguments, "batch_id")
        response = self._request(
            "POST",
            f"/api/v1/batches/{quote(batch_id, safe='')}/cancel",
            {},
        )
        return {"ok": True, "batch": response}

    def _list_result_artifacts(self, arguments: JsonObject) -> JsonObject:
        job_id = _required_string(arguments, "job_id")
        job = self._request("GET", f"/api/v1/jobs/{quote(job_id, safe='')}")
        capability_id = job.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id:
            raise ValueError("Optees returned a job without a capability_id.")
        descriptor = self._request(
            "GET",
            f"/api/v1/capabilities/{quote(capability_id, safe='')}",
        )
        response = self._request(
            "GET",
            f"/api/v1/jobs/{quote(job_id, safe='')}/artifacts",
        )
        return {
            "ok": True,
            "job_id": job_id,
            "capability_id": capability_id,
            "available_artifacts": descriptor.get("available_artifacts", []),
            "artifact_batches": response.get("artifact_batches", []),
            "content_policy": {
                "content_included": False,
                "retrieval": (
                    "An authenticated client downloads available files from "
                    "/api/v1/artifacts/{artifact_id}."
                ),
            },
        }

    def _render_result_artifacts(self, arguments: JsonObject) -> JsonObject:
        job_id = _required_string(arguments, "job_id")
        contract_version = arguments.get("contract_version", "1")
        if not isinstance(contract_version, str) or not contract_version:
            raise ValueError("contract_version must be a non-empty string")
        if contract_version != "1":
            raise ValueError("unsupported artifact contract version")
        requests = _object_list(arguments, "requests", minimum=1, maximum=8)
        response = self._request(
            "POST",
            f"/api/v1/jobs/{quote(job_id, safe='')}/artifacts",
            {
                "contract_version": contract_version,
                "requests": requests,
            },
        )
        return {
            "ok": True,
            "artifact_batch": response,
            "content_policy": {
                "content_included": False,
                "next_step": "Poll optees_list_result_artifacts for metadata.",
            },
        }

    def _cancel_artifact(self, arguments: JsonObject) -> JsonObject:
        artifact_id = _required_string(arguments, "artifact_id")
        response = self._request(
            "POST",
            f"/api/v1/artifacts/{quote(artifact_id, safe='')}/cancel",
            {},
        )
        return {"ok": True, "artifact": response}

    def _get_report_backends(self, _arguments: JsonObject) -> JsonObject:
        response = self._request("GET", "/api/v1/reports/backends")
        return {"ok": True, "backends": response.get("backends", [])}

    def _compose_report(self, arguments: JsonObject) -> JsonObject:
        request: object = arguments.get("request", arguments)
        if isinstance(request, str):
            try:
                request = json.loads(request)
            except json.JSONDecodeError as exc:
                raise ValueError("request must contain valid JSON") from exc
        if not isinstance(request, dict):
            raise ValueError("report request must be a JSON object")
        response = self._request(
            "POST",
            "/api/v1/reports",
            _normalize_agent_report_request(request),
        )
        return {
            "ok": True,
            "report": response,
            "content_policy": {
                "content_included": False,
                "next_step": "Poll optees_get_report_status for metadata.",
            },
        }

    def _get_report_status(self, arguments: JsonObject) -> JsonObject:
        report_id = _required_string(arguments, "report_id")
        response = self._request(
            "GET",
            f"/api/v1/reports/{quote(report_id, safe='')}",
        )
        payload: JsonObject = {
            "ok": True,
            "report": response,
            "content_included": False,
        }
        if response.get("status") == "available":
            payload["download_endpoint"] = (
                f"/api/v1/reports/{quote(report_id, safe='')}/download"
            )
        return payload

    def _cancel_report(self, arguments: JsonObject) -> JsonObject:
        report_id = _required_string(arguments, "report_id")
        response = self._request(
            "POST",
            f"/api/v1/reports/{quote(report_id, safe='')}/cancel",
            {},
        )
        return {"ok": True, "report": response}

    def _problem_arguments(self, arguments: JsonObject) -> tuple[str, JsonObject]:
        capability_id = _required_string(arguments, "capability_id")
        problem = arguments.get("problem")
        if not isinstance(problem, dict):
            raise ValueError("problem must be a JSON object")
        return capability_id, problem

    def _batch_arguments(
        self,
        arguments: JsonObject,
    ) -> tuple[str, list[JsonObject]]:
        version = _required_string(arguments, "version")
        if version != "1":
            raise ValueError("unsupported batch version")
        raw_items = arguments.get("items")
        if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 32:
            raise ValueError("items must contain between 1 and 32 objects")
        items: list[JsonObject] = []
        identifiers: set[str] = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                raise ValueError("every batch item must be an object")
            client_item_id = _required_string(raw_item, "client_item_id")
            capability_id = _required_string(raw_item, "capability_id")
            problem = raw_item.get("problem")
            if not isinstance(problem, dict):
                raise ValueError("batch problem must be a JSON object")
            if client_item_id in identifiers:
                raise ValueError("batch client_item_id values must be unique")
            identifiers.add(client_item_id)
            items.append(
                {
                    "client_item_id": client_item_id,
                    "capability_id": capability_id,
                    "problem": problem,
                }
            )
        return version, items

    def _request(
        self,
        method: str,
        path: str,
        payload: JsonObject | None = None,
    ) -> JsonObject:
        return self._transport.request(
            method,
            f"{self._base_url}{path}",
            headers=self._headers,
            payload=payload,
            timeout=self._timeout,
        )


@dataclass(frozen=True)
class ToolEvent:
    name: str
    arguments: JsonObject
    result: JsonObject

    def to_dict(self) -> JsonObject:
        return {
            "name": self.name,
            "arguments": _redact(self.arguments),
            "result": _redact(self.result),
        }


@dataclass(frozen=True)
class AgentRun:
    model: str
    model_digest: str
    prompt: str
    final_response: str
    tool_events: tuple[ToolEvent, ...]

    def to_dict(self) -> JsonObject:
        return {
            "model": self.model,
            "model_digest": self.model_digest,
            "prompt": self.prompt,
            "final_response": self.final_response,
            "tool_events": [event.to_dict() for event in self.tool_events],
        }


class OllamaAgentHarness:
    def __init__(
        self,
        *,
        ollama: OllamaClient,
        tools: OpteesToolFacade,
        model: str = "qwen2.5-coder:7b",
        max_tool_calls: int = 24,
        max_run_seconds: float = 600.0,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        if isinstance(max_tool_calls, bool) or max_tool_calls < 1:
            raise ValueError("max_tool_calls must be a positive integer")
        if (
            isinstance(max_run_seconds, bool)
            or not isinstance(max_run_seconds, (int, float))
            or not math.isfinite(float(max_run_seconds))
            or max_run_seconds <= 0
        ):
            raise ValueError("max_run_seconds must be finite and positive")
        self._ollama = ollama
        self._tools = tools
        self._model = model
        self._max_tool_calls = max_tool_calls
        self._max_run_seconds = float(max_run_seconds)
        self._progress = progress

    def run(self, prompt: str) -> AgentRun:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        self._tools.reset_session()
        deadline = monotonic() + self._max_run_seconds
        self._emit(f"Loading model {self._model}...")
        model_info = self._ollama.model_info(self._model)
        digest = str(model_info.get("digest", ""))
        self._emit(f"Model ready: {self._model} ({digest[:12]})")
        messages: list[JsonObject] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        events: list[ToolEvent] = []
        tool_call_count = 0

        while True:
            if monotonic() > deadline:
                raise RuntimeError("Ollama exceeded the configured run-time limit.")
            self._emit("Waiting for Ollama...")
            response = self._ollama.chat(
                model=self._model,
                messages=messages,
                tools=self._tools.tool_definitions,
            )
            message = response.get("message")
            if not isinstance(message, dict):
                raise RuntimeError("Ollama returned a response without a message.")
            messages.append(message)
            tool_calls = message.get("tool_calls")
            if not isinstance(tool_calls, list) or not tool_calls:
                return AgentRun(
                    model=self._model,
                    model_digest=digest,
                    prompt=prompt,
                    final_response=str(message.get("content", "")),
                    tool_events=tuple(events),
                )

            for tool_call in tool_calls:
                if monotonic() > deadline:
                    raise RuntimeError("Ollama exceeded the configured run-time limit.")
                tool_call_count += 1
                if tool_call_count > self._max_tool_calls:
                    raise RuntimeError("Ollama exceeded the configured tool-call limit.")
                name, arguments = _parse_tool_call(tool_call)
                self._emit(f"Calling tool: {name}")
                result = self._tools.execute(name, arguments)
                self._emit(
                    f"Tool completed: {name} ({'ok' if result.get('ok') else 'error'})"
                )
                if result.get("ok") is not True:
                    self._emit(
                        "Tool error: "
                        + json.dumps(_redact(result.get("error")), sort_keys=True)
                    )
                events.append(ToolEvent(name, arguments, result))
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(result, sort_keys=True),
                    }
                )

    def _emit(self, message: str) -> None:
        if self._progress is not None:
            self._progress(message)


_SYSTEM_PROMPT = """You are a local operations-research assistant using Optees.
Use Optees tools instead of calculating a supported final answer yourself.
First list capabilities, then inspect the selected capability descriptor and its
JSON schema. State material assumptions and ask the user for missing information
instead of inventing values. Validate the exact problem before creating a job.
For multiple independent scenarios, use the batch tools: inspect every distinct
capability, validate the exact batch, create it once, poll its aggregate status,
then retrieve the aggregate result. Do not replace a dependent multi-stage
workflow with a batch.
Poll a created job until it reaches a terminal state, retrieve its result, and
report mathematical status and independent validation status separately. Never
claim global optimality unless the Optees result does. Never request, reveal, or
repeat authentication credentials. For LP results, always report the
optimal_face analysis_status. Call the optimum unique only when that analysis
is computed, has_alternate_optimum is false, and dimension is zero. Report
alternate-optimum ranges when available; for partial, skipped, or unavailable
analysis, state that uniqueness could not be established.
When the user requests visual artifacts or a report, first discover the job's
available artifact contract, request only advertised outputs, and poll metadata
until terminal. Check report backend diagnostics before requesting PDF; use
Markdown when PDF is unavailable. Compose reports only from safe Markdown, job
status, and artifact IDs returned by Optees. Tool results never contain binary
file bytes: report the authenticated relative download endpoint to the user
instead of attempting to read or reproduce file content."""


def _tool(
    name: str,
    description: str,
    properties: JsonObject,
    required: list[str],
) -> JsonObject:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def _parse_tool_call(tool_call: object) -> tuple[str, JsonObject]:
    if not isinstance(tool_call, dict) or not isinstance(tool_call.get("function"), dict):
        raise RuntimeError("Ollama returned an invalid tool call.")
    function = tool_call["function"]
    name = function.get("name")
    arguments = function.get("arguments", {})
    if not isinstance(name, str) or not name:
        raise RuntimeError("Ollama returned a tool call without a name.")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned invalid JSON tool arguments.") from exc
    if not isinstance(arguments, dict):
        raise RuntimeError("Ollama tool arguments must be a JSON object.")
    return name, arguments


def _problem_key(capability_id: str, problem: JsonObject) -> str:
    canonical = json.dumps(
        {"capability_id": capability_id, "problem": problem},
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _batch_key(payload: JsonObject) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _required_string(arguments: JsonObject, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _object_list(
    arguments: JsonObject,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> list[JsonObject]:
    value = arguments.get(name)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{name} must contain valid JSON") from exc
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(
            f"{name} must contain between {minimum} and {maximum} objects"
        )
    if any(not isinstance(item, dict) for item in value):
        raise ValueError(f"every {name} item must be an object")
    return value


def _normalize_agent_report_request(request: JsonObject) -> JsonObject:
    normalized = dict(request)
    normalized.setdefault("contract_version", "1")
    metadata = normalized.get("metadata")
    if metadata in (None, ""):
        normalized["metadata"] = {}
    elif isinstance(metadata, str):
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise ValueError("metadata must contain valid JSON") from exc
        if not isinstance(parsed_metadata, dict):
            raise ValueError("metadata must be a JSON object")
        normalized["metadata"] = parsed_metadata
    sections = normalized.get("sections")
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except json.JSONDecodeError as exc:
            raise ValueError("sections must contain valid JSON") from exc
        normalized["sections"] = sections
    if not isinstance(sections, list):
        return normalized
    normalized_sections: list[object] = []
    for section in sections:
        if not isinstance(section, dict):
            normalized_sections.append(section)
            continue
        normalized_section = dict(section)
        blocks = normalized_section.get("blocks")
        if not isinstance(blocks, list):
            normalized_sections.append(normalized_section)
            continue
        normalized_blocks: list[object] = []
        for block in blocks:
            if not isinstance(block, dict) or "value" not in block:
                normalized_blocks.append(block)
                continue
            block_type = block.get("type")
            value = block.get("value")
            if block_type == "markdown":
                normalized_blocks.append({"type": "markdown", "content": value})
            elif block_type == "job_status":
                normalized_blocks.append({"type": "job_status", "job_id": value})
            elif block_type == "artifact":
                normalized_block: JsonObject = {
                    "type": "artifact",
                    "artifact_id": value,
                }
                caption = block.get("caption")
                if isinstance(caption, str) and caption:
                    normalized_block["caption"] = caption
                views = block.get("views")
                if isinstance(views, list) and views:
                    normalized_block["views"] = views
                normalized_blocks.append(normalized_block)
            else:
                normalized_blocks.append(block)
        normalized_section["blocks"] = normalized_blocks
        normalized_sections.append(normalized_section)
    normalized["sections"] = normalized_sections
    return normalized


def _tool_error(code: str, message: str) -> JsonObject:
    return {"ok": False, "error": {"code": code, "message": message}}


def _json_object(raw: bytes) -> JsonObject:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Remote API returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Remote API response must be a JSON object.")
    return payload


def _error_payload(raw: bytes) -> JsonObject:
    try:
        return _json_object(raw)
    except RuntimeError:
        return {"code": "remote_error", "message": "Remote API request failed."}


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if any(marker in key.lower() for marker in ("token", "authorization", "secret", "api_key"))
            else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
