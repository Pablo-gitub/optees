from __future__ import annotations

from typing import Any, Dict, Protocol


class PackingSolverPort(Protocol):
    """Boundary for exact single-container orthogonal packing solvers."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Return normalized status, placements, exclusions, and diagnostics."""
        ...

    def cancel(self) -> bool:
        """Request interruption of the active solve, when supported."""
        ...
