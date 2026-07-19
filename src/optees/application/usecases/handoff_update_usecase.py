from __future__ import annotations

from pathlib import Path

from optees.application.ports.update_handoff_port import UpdateHandoffPort
from optees.domain.entities.update import (
    UpdateExecutionState,
    UpdateHandoffMethod,
    UpdateHandoffResult,
    UpdatePlan,
)


class HandoffUpdateUseCase:
    """Validate a downloaded artifact before starting its native handoff."""

    def __init__(self, handoff: UpdateHandoffPort) -> None:
        self._handoff = handoff

    def execute(self, plan: UpdatePlan, local_path: Path) -> UpdateHandoffResult:
        path = Path(local_path).resolve()
        if not path.is_file():
            raise ValueError(f"Downloaded update does not exist: {path}")
        if path.name != plan.artifact.name:
            raise ValueError(
                "Downloaded update filename does not match the selected release asset."
            )
        if not self._handoff.start(plan, path):
            raise RuntimeError("The operating system did not accept the update handoff.")

        state = (
            UpdateExecutionState.INSTALLER_LAUNCHED
            if plan.handoff_method is UpdateHandoffMethod.LAUNCH_INSTALLER
            else UpdateExecutionState.MANUAL_ACTION_REQUIRED
        )
        return UpdateHandoffResult(
            plan=plan,
            local_path=str(path),
            state=state,
            started=True,
        )
