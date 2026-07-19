from __future__ import annotations

from pathlib import Path
from typing import Protocol

from optees.domain.entities.update import UpdatePlan


class UpdateHandoffPort(Protocol):
    """Start the operating-system action described by an update plan."""

    def start(self, plan: UpdatePlan, local_path: Path) -> bool:
        """Return true only when the operating system accepted the handoff."""
        ...
