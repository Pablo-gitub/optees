from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Sequence

from optees.application.services.local_server_process import (
    DEFAULT_LOCAL_SERVER_PORT,
    LOCAL_SERVER_TOKEN_ENV,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="optees-server",
        description="Run the authenticated Optees solver API on loopback.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_LOCAL_SERVER_PORT)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args(argv)

    token = os.environ.get(LOCAL_SERVER_TOKEN_ENV, "")
    if len(token) < 32:
        print(
            f"optees-server: {LOCAL_SERVER_TOKEN_ENV} must contain a session token.",
            file=sys.stderr,
        )
        return 2

    if any(
        importlib.util.find_spec(module_name) is None
        for module_name in ("fastapi", "pydantic", "uvicorn")
    ):
        print(
            "The optional local-service dependency is missing. Install optees[local-service].",
            file=sys.stderr,
        )
        return 2
    from optees.interfaces.http import run_local_api

    try:
        run_local_api(token=token, port=args.port, log_level=args.log_level)
    except ValueError as exc:
        print(f"optees-server: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
