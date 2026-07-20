from __future__ import annotations

import asyncio
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_TOOL = "optees_list_capabilities"


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


if __name__ == "__main__":
    raise SystemExit(main())
