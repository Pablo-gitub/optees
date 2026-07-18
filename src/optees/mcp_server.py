from __future__ import annotations

import sys

from optees.composition.local_agent import create_local_job_service
from optees.interfaces.mcp.local_server import create_mcp_server


def main() -> None:
    """Run one private Optees MCP session over standard input and output."""

    service = create_local_job_service()
    try:
        create_mcp_server(service).run(transport="stdio")
    except ImportError:
        print(
            "The optional MCP dependency is missing. Install optees[mcp].",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    finally:
        service.shutdown(wait=True, cancel_pending=True)


if __name__ == "__main__":
    main()
