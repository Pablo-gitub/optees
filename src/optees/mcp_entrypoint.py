from __future__ import annotations

import importlib.util
import sys


def main() -> None:
    """Load the optional MCP runtime with a bounded missing-extra diagnostic."""

    if importlib.util.find_spec("mcp") is None:
        print(
            "The optional MCP dependency is missing. Install optees[mcp].",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    from optees.mcp_server import main as run_mcp_server

    run_mcp_server()


if __name__ == "__main__":
    main()
