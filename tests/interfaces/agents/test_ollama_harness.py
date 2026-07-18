from __future__ import annotations

import json

import pytest

from optees.interfaces.agents.ollama_harness import (
    OllamaAgentHarness,
    OllamaClient,
    OpteesToolFacade,
)
from optees.ollama_chat import _connection_token


TOKEN = "local-test-token-" + "x" * 32
PROBLEM = {
    "version": "1",
    "variables": [{"name": "x", "label": "", "lb": 0, "ub": 1}],
    "objective": {"sense": "max", "coefficients": [1], "offset": 0},
    "constraints": [],
}


class FakeOpteesTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def request(
        self,
        method,
        url,
        *,
        headers=None,
        payload=None,
        timeout=30.0,
    ):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        if url.endswith("/api/v1/capabilities"):
            return {
                "capabilities": [
                    {
                        "id": "lp.continuous",
                        "title": "Linear programming",
                        "problem_type": "linear_programming",
                        "available": True,
                        "problem_schema_version": "1",
                        "result_schema_version": "1",
                    }
                ]
            }
        if url.endswith("/api/v1/capabilities/lp.continuous"):
            return {
                "id": "lp.continuous",
                "available": True,
                "input_schema": {"type": "object"},
            }
        if url.endswith("/api/v1/problems/validate"):
            return {
                "valid": True,
                "available": True,
                "capability_id": "lp.continuous",
                "problem_schema_version": "1",
            }
        if url.endswith("/api/v1/jobs"):
            return {"job_id": "job-1", "job_status": "queued"}
        if url.endswith("/api/v1/jobs/job-1/result"):
            return {
                "job_id": "job-1",
                "mathematical_status": "optimal",
                "result": {"objective": 1.0, "variables": [{"name": "x", "value": 1.0}]},
                "validation": {"status": "verified"},
            }
        if url.endswith("/api/v1/jobs/job-1"):
            return {
                "job_id": "job-1",
                "job_status": "completed",
                "result_available": True,
            }
        raise AssertionError(f"Unexpected request: {method} {url}")


class FakeOllama:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.requests: list[dict[str, object]] = []

    def model_info(self, model):
        return {"name": model, "digest": "frozen-test-digest", "capabilities": ["tools"]}

    def chat(self, *, model, messages, tools):
        self.requests.append({"model": model, "messages": list(messages), "tools": tools})
        return next(self._responses)


def _call(name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": name, "arguments": arguments}}],
        }
    }


def test_tool_facade_requires_descriptor_and_exact_validation_before_job():
    transport = FakeOpteesTransport()
    facade = OpteesToolFacade(
        base_url="http://127.0.0.1:8765",
        token=TOKEN,
        transport=transport,
    )
    arguments = {"capability_id": "lp.continuous", "problem": PROBLEM}

    before_descriptor = facade.execute("optees_validate_problem", arguments)
    facade.execute("optees_get_capability", {"capability_id": "lp.continuous"})
    before_validation = facade.execute("optees_create_job", arguments)
    validation = facade.execute("optees_validate_problem", arguments)
    changed = facade.execute(
        "optees_create_job",
        {
            "capability_id": "lp.continuous",
            "problem": {**PROBLEM, "constraints": [{"coefficients": [1], "relation": "<=", "rhs": 0}]},
        },
    )
    created = facade.execute("optees_create_job", arguments)

    assert before_descriptor["error"]["code"] == "capability_not_inspected"
    assert before_validation["error"]["code"] == "problem_not_validated"
    assert validation["ok"] is True
    assert changed["error"]["code"] == "problem_not_validated"
    assert created["job"]["job_id"] == "job-1"
    assert all(
        call["headers"] == {"Authorization": f"Bearer {TOKEN}"}
        for call in transport.calls
    )


def test_complete_ollama_agent_loop_records_redacted_reproducible_events():
    transport = FakeOpteesTransport()
    facade = OpteesToolFacade(
        base_url="http://127.0.0.1:8765",
        token=TOKEN,
        transport=transport,
    )
    problem_arguments = {"capability_id": "lp.continuous", "problem": PROBLEM}
    ollama = FakeOllama(
        [
            _call("optees_list_capabilities", {}),
            _call("optees_get_capability", {"capability_id": "lp.continuous"}),
            _call("optees_validate_problem", problem_arguments),
            _call("optees_create_job", problem_arguments),
            _call("optees_get_job_status", {"job_id": "job-1"}),
            _call("optees_get_job_result", {"job_id": "job-1"}),
            {"message": {"role": "assistant", "content": "x = 1; validation verified."}},
        ]
    )

    run = OllamaAgentHarness(
        ollama=ollama,  # type: ignore[arg-type]
        tools=facade,
        model="qwen2.5-coder:7b",
    ).run("Solve this small production problem with Optees.")

    assert run.model_digest == "frozen-test-digest"
    assert run.final_response == "x = 1; validation verified."
    assert [event.name for event in run.tool_events] == [
        "optees_list_capabilities",
        "optees_get_capability",
        "optees_validate_problem",
        "optees_create_job",
        "optees_get_job_status",
        "optees_get_job_result",
    ]
    serialized = json.dumps(run.to_dict())
    assert TOKEN not in serialized
    assert all(request["tools"] for request in ollama.requests)
    system_prompt = ollama.requests[0]["messages"][0]["content"]
    assert "optimal_face" in system_prompt
    assert "Call the optimum unique only when" in system_prompt


def test_harness_stops_runaway_tool_calling():
    facade = OpteesToolFacade(
        base_url="http://127.0.0.1:8765",
        token=TOKEN,
        transport=FakeOpteesTransport(),
    )
    ollama = FakeOllama(
        [
            _call("optees_list_capabilities", {}),
            _call("optees_list_capabilities", {}),
        ]
    )

    with pytest.raises(RuntimeError, match="tool-call limit"):
        OllamaAgentHarness(
            ollama=ollama,  # type: ignore[arg-type]
            tools=facade,
            max_tool_calls=1,
        ).run("Find a solver.")


def test_json_looking_assistant_text_is_not_executed_as_a_tool_call():
    transport = FakeOpteesTransport()
    facade = OpteesToolFacade(
        base_url="http://127.0.0.1:8765",
        token=TOKEN,
        transport=transport,
    )
    ollama = FakeOllama(
        [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"name":"optees_list_capabilities","arguments":{}}',
                }
            }
        ]
    )

    run = OllamaAgentHarness(
        ollama=ollama,  # type: ignore[arg-type]
        tools=facade,
    ).run("Find a solver.")

    assert run.tool_events == ()
    assert transport.calls == []


def test_ollama_client_rejects_installed_model_without_tool_capability():
    class TagsTransport:
        def request(self, *args, **kwargs):
            return {
                "models": [
                    {
                        "name": "deepseek-coder:6.7b",
                        "digest": "digest",
                        "capabilities": ["completion"],
                    }
                ]
            }

    client = OllamaClient(transport=TagsTransport())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="does not support tools"):
        client.model_info("deepseek-coder:6.7b")


def test_ollama_client_disables_thinking_for_bounded_tool_runs():
    class RecordingTransport:
        def __init__(self):
            self.payload = None

        def request(self, *args, **kwargs):
            self.payload = kwargs["payload"]
            return {"message": {"role": "assistant", "content": "done"}}

    transport = RecordingTransport()
    client = OllamaClient(transport=transport)  # type: ignore[arg-type]

    client.chat(model="model", messages=[], tools=[])

    assert transport.payload["think"] is False


def test_cli_accepts_hidden_token_or_copied_connection_configuration():
    assert _connection_token(TOKEN) == TOKEN
    assert _connection_token(f"Bearer {TOKEN}") == TOKEN
    assert (
        _connection_token(
            json.dumps(
                {
                    "base_url": "http://127.0.0.1:8765",
                    "authorization": f"Bearer {TOKEN}",
                }
            )
        )
        == TOKEN
    )
