from __future__ import annotations

from typing import Any, Dict, Protocol


class ShortestPathSolverPort(Protocol):
    """Abstraction over a non-negative shortest-path implementation."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Return status, distance, path, and settled-node diagnostics."""
        ...
