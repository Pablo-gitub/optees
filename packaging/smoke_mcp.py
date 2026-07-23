from __future__ import annotations

import asyncio
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_TOOL = "optees_list_capabilities"
LP_PROBLEM = {
    "version": "1",
    "variables": [
        {"name": "x", "label": "Product", "lb": 0, "ub": 4},
    ],
    "objective": {
        "sense": "max",
        "coefficients": [3],
        "offset": 0,
    },
    "constraints": [],
}


def main(argv: list[str] | None = None) -> int:
    command = list(sys.argv[1:] if argv is None else argv)
    if not command:
        print(
            "usage: python packaging/smoke_mcp.py COMMAND [ARG ...]",
            file=sys.stderr,
        )
        return 2
    asyncio.run(_smoke(command[0], command[1:]))
    return 0


async def _smoke(command: str, arguments: list[str]) -> None:
    parameters = StdioServerParameters(command=command, args=arguments)
    timeout = timedelta(seconds=30)
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            if EXPECTED_TOOL not in names:
                raise RuntimeError(f"packaged MCP tools are incomplete: {sorted(names)}")
            listed = await session.call_tool(
                EXPECTED_TOOL,
                {},
                read_timeout_seconds=timeout,
            )
            if listed.isError:
                raise RuntimeError("packaged MCP capability discovery failed")
            payload = listed.structuredContent
            if not isinstance(payload, dict) or payload.get("ok") is not True:
                raise RuntimeError(f"unexpected MCP response: {payload!r}")
            capabilities = payload.get("capabilities")
            if not isinstance(capabilities, list) or not capabilities:
                raise RuntimeError("packaged MCP returned no capabilities")
            lp = next(
                (
                    item
                    for item in capabilities
                    if isinstance(item, dict) and item.get("id") == "lp.continuous"
                ),
                None,
            )
            if not isinstance(lp, dict) or lp.get("available") is not True:
                raise RuntimeError(
                    f"packaged continuous LP backend is unavailable: {lp!r}"
                )
            await _solve_lp(session, timeout)


async def _solve_lp(session: ClientSession, timeout: timedelta) -> None:
    inspected = await session.call_tool(
        "optees_get_capability",
        {"capability_id": "lp.continuous"},
        read_timeout_seconds=timeout,
    )
    _require_ok(inspected, "capability inspection")
    validated = await session.call_tool(
        "optees_validate_problem",
        {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
        read_timeout_seconds=timeout,
    )
    validation = _require_ok(validated, "LP validation")
    if validation.get("validation", {}).get("valid") is not True:
        raise RuntimeError(f"packaged LP validation failed: {validation!r}")
    created = await session.call_tool(
        "optees_create_job",
        {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
        read_timeout_seconds=timeout,
    )
    job_id = _require_ok(created, "LP job creation").get("job", {}).get("job_id")
    if not isinstance(job_id, str):
        raise RuntimeError(f"packaged LP returned no job id: {created!r}")
    job: dict[str, object] = {}
    for _ in range(100):
        status = await session.call_tool(
            "optees_get_job_status",
            {"job_id": job_id},
            read_timeout_seconds=timeout,
        )
        job = _require_ok(status, "LP status").get("job", {})
        if job.get("job_status") in {"completed", "failed", "cancelled"}:
            break
        await asyncio.sleep(0.01)
    if job.get("job_status") != "completed":
        raise RuntimeError(f"packaged LP job did not complete: {job!r}")
    result = await session.call_tool(
        "optees_get_job_result",
        {"job_id": job_id},
        read_timeout_seconds=timeout,
    )
    envelope = _require_ok(result, "LP result").get("result", {})
    if (
        envelope.get("mathematical_status") != "optimal"
        or envelope.get("validation", {}).get("status") != "verified"
        or envelope.get("result", {}).get("objective") != 12.0
    ):
        raise RuntimeError(f"packaged LP solve failed: {envelope!r}")


def _require_ok(result, operation: str) -> dict[str, object]:
    if result.isError or not isinstance(result.structuredContent, dict):
        raise RuntimeError(f"packaged MCP {operation} failed: {result!r}")
    payload = result.structuredContent
    if payload.get("ok") is not True:
        raise RuntimeError(f"packaged MCP {operation} failed: {payload!r}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
