from __future__ import annotations

import asyncio
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from optees.composition.local_agent import create_local_job_service
from optees.interfaces.mcp.local_server import (
    LocalMcpToolFacade,
    create_mcp_server,
)


ROOT = Path(__file__).resolve().parents[3]
LP_PROBLEM = {
    "version": "1",
    "variables": [
        {"name": "product_a", "label": "Product A", "lb": 0, "ub": 4},
        {"name": "product_b", "label": "Product B", "lb": 0, "ub": 5},
    ],
    "objective": {
        "sense": "max",
        "coefficients": [30, 40],
        "offset": 0,
    },
    "constraints": [
        {"coefficients": [2, 4], "relation": "<=", "rhs": 18},
    ],
}
TOOL_NAMES = {
    "optees_list_capabilities",
    "optees_get_capability",
    "optees_validate_problem",
    "optees_create_job",
    "optees_get_job_status",
    "optees_get_job_result",
    "optees_cancel_job",
    "optees_validate_batch",
    "optees_create_batch",
    "optees_get_batch_status",
    "optees_get_batch_result",
    "optees_cancel_batch",
}


def test_facade_requires_descriptor_and_exact_validation_before_job():
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    try:
        before_descriptor = facade.validate_problem("lp.continuous", LP_PROBLEM)
        descriptor = facade.get_capability("lp.continuous")
        before_validation = facade.create_job("lp.continuous", LP_PROBLEM)
        validation = facade.validate_problem("lp.continuous", LP_PROBLEM)
        changed = facade.create_job(
            "lp.continuous",
            {**LP_PROBLEM, "constraints": []},
        )
        created = facade.create_job("lp.continuous", LP_PROBLEM)
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert before_descriptor["error"]["code"] == "capability_not_inspected"
    assert descriptor["capability"]["input_schema"]["type"] == "object"
    assert before_validation["error"]["code"] == "problem_not_validated"
    assert validation["validation"]["valid"] is True
    assert changed["error"]["code"] == "problem_not_validated"
    assert created["job"]["capability_id"] == "lp.continuous"


def test_mcp_tools_publish_expected_names_and_problem_schemas():
    async def inspect_tools():
        service = create_local_job_service()
        try:
            return await create_mcp_server(service).list_tools()
        finally:
            service.shutdown(wait=True, cancel_pending=True)

    tools = asyncio.run(inspect_tools())
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == TOOL_NAMES
    validate_schema = by_name["optees_validate_problem"].inputSchema
    assert set(validate_schema["required"]) == {"capability_id", "problem"}
    assert validate_schema["properties"]["problem"]["type"] == "object"
    assert by_name["optees_get_job_result"].outputSchema["type"] == "object"
    batch_schema = by_name["optees_validate_batch"].inputSchema
    assert batch_schema["properties"]["items"]["maxItems"] == 32


def test_facade_requires_inspection_and_exact_validation_before_batch():
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    items = [
        {
            "client_item_id": f"scenario-{index}",
            "capability_id": "lp.continuous",
            "problem": LP_PROBLEM,
        }
        for index in range(1, 3)
    ]
    try:
        before_descriptor = facade.validate_batch("1", items)
        facade.get_capability("lp.continuous")
        before_validation = facade.create_batch("1", items)
        validation = facade.validate_batch("1", items)
        changed = facade.create_batch(
            "1",
            [
                items[0],
                {
                    **items[1],
                    "problem": {**LP_PROBLEM, "constraints": []},
                },
            ],
        )
        created = facade.create_batch("1", items)
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert before_descriptor["error"]["code"] == "capability_not_inspected"
    assert before_validation["error"]["code"] == "batch_not_validated"
    assert validation["validation"]["valid"] is True
    assert changed["error"]["code"] == "batch_not_validated"
    assert created["batch"]["item_count"] == 2


def test_stdio_mcp_client_completes_local_lp_workflow():
    asyncio.run(_run_stdio_lp_workflow())


async def _run_stdio_lp_workflow() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "optees.mcp_server"],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    timeout = timedelta(seconds=20)
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == TOOL_NAMES

            listed = await session.call_tool(
                "optees_list_capabilities",
                {},
                read_timeout_seconds=timeout,
            )
            assert _structured(listed)["ok"] is True
            await session.call_tool(
                "optees_get_capability",
                {"capability_id": "lp.continuous"},
                read_timeout_seconds=timeout,
            )
            validated = await session.call_tool(
                "optees_validate_problem",
                {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
                read_timeout_seconds=timeout,
            )
            assert _structured(validated)["validation"]["valid"] is True
            created = await session.call_tool(
                "optees_create_job",
                {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
                read_timeout_seconds=timeout,
            )
            job_id = _structured(created)["job"]["job_id"]

            for _ in range(100):
                status = await session.call_tool(
                    "optees_get_job_status",
                    {"job_id": job_id},
                    read_timeout_seconds=timeout,
                )
                job = _structured(status)["job"]
                if job["job_status"] in {"completed", "failed", "cancelled"}:
                    break
                await asyncio.sleep(0.01)
            assert job["job_status"] == "completed"

            result = await session.call_tool(
                "optees_get_job_result",
                {"job_id": job_id},
                read_timeout_seconds=timeout,
            )
            envelope = _structured(result)["result"]
            assert envelope["mathematical_status"] == "optimal"
            assert envelope["validation"]["status"] == "verified"
            assert envelope["result"]["objective"] == 220.0


def _structured(result) -> dict[str, object]:
    assert result.isError is False
    assert isinstance(result.structuredContent, dict)
    return result.structuredContent
