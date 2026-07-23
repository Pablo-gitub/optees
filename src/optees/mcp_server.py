from __future__ import annotations

from contextlib import contextmanager
import os
import sys
from typing import Iterator, TextIO

from optees.composition.local_agent import (
    create_local_artifact_service,
    create_local_job_service,
    create_local_report_service,
)
from optees.interfaces.mcp.local_server import create_mcp_server


def main() -> None:
    """Run one private Optees MCP session over standard input and output."""

    service = create_local_job_service()
    artifacts = create_local_artifact_service(service)
    reports = create_local_report_service(service, artifacts)
    try:
        with _isolated_frozen_stdio():
            create_mcp_server(service, artifacts, reports).run(transport="stdio")
    except ImportError:
        print(
            "The optional MCP dependency is missing. Install optees[mcp].",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    finally:
        reports.close(wait=True)
        artifacts.close(wait=True)
        service.shutdown(wait=True, cancel_pending=True)


@contextmanager
def _isolated_frozen_stdio() -> Iterator[None]:
    """Prevent the MCP transport from closing PyInstaller-owned stdio buffers."""

    if not getattr(sys, "frozen", False):
        yield
        return

    original_stdin = sys.stdin
    original_stdout = sys.stdout
    duplicate_stdin = _duplicate_text_stream(original_stdin, "r")
    duplicate_stdout = _duplicate_text_stream(original_stdout, "w")
    sys.stdin = duplicate_stdin
    sys.stdout = duplicate_stdout
    try:
        yield
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout
        if not duplicate_stdin.closed:
            duplicate_stdin.close()
        if not duplicate_stdout.closed:
            duplicate_stdout.close()


def _duplicate_text_stream(stream: TextIO, mode: str) -> TextIO:
    descriptor = os.dup(stream.fileno())
    return os.fdopen(
        descriptor,
        mode,
        encoding="utf-8",
        errors="replace",
        closefd=True,
    )


if __name__ == "__main__":
    main()
