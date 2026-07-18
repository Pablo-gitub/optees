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

    @property
    def tool_definitions(self) -> list[JsonObject]:
        problem_properties = {
            "capability_id": {"type": "string"},
            "problem": {"type": "object", "additionalProperties": True},
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

    def _problem_arguments(self, arguments: JsonObject) -> tuple[str, JsonObject]:
        capability_id = _required_string(arguments, "capability_id")
        problem = arguments.get("problem")
        if not isinstance(problem, dict):
            raise ValueError("problem must be a JSON object")
        return capability_id, problem

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
        max_tool_calls: int = 16,
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
Poll a created job until it reaches a terminal state, retrieve its result, and
report mathematical status and independent validation status separately. Never
claim global optimality unless the Optees result does. Never request, reveal, or
repeat authentication credentials. For LP results, always report the
optimal_face analysis_status. Call the optimum unique only when that analysis
is computed, has_alternate_optimum is false, and dimension is zero. Report
alternate-optimum ranges when available; for partial, skipped, or unavailable
analysis, state that uniqueness could not be established."""


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


def _required_string(arguments: JsonObject, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


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
