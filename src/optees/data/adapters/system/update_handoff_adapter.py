from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from optees.application.ports.update_handoff_port import UpdateHandoffPort
from optees.domain.entities.update import UpdatePlan, UpdatePlatform


class DesktopUpdateHandoffAdapter(UpdateHandoffPort):
    """Open a verified release package with the native desktop handler."""

    def __init__(self, *, system_name: str | None = None) -> None:
        self._system_name = system_name

    def start(self, plan: UpdatePlan, local_path: Path) -> bool:
        current = _platform_from_system_name(self._system_name or platform.system())
        if current is not plan.platform:
            raise RuntimeError(
                f"Update plan targets {plan.platform.value}, not the current platform."
            )

        path = str(Path(local_path).resolve())
        if current is UpdatePlatform.WINDOWS:
            startfile = getattr(os, "startfile", None)
            if startfile is None:
                raise RuntimeError("Windows shell handoff is unavailable.")
            startfile(path)
            return True

        command = ["open", path] if current is UpdatePlatform.MACOS else ["xdg-open", path]
        subprocess.Popen(
            command,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True


def _platform_from_system_name(value: str) -> UpdatePlatform:
    normalized = (value or "").strip().lower()
    aliases = {
        "darwin": UpdatePlatform.MACOS,
        "macos": UpdatePlatform.MACOS,
        "windows": UpdatePlatform.WINDOWS,
        "linux": UpdatePlatform.LINUX,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported update platform: {value}") from exc
