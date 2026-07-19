from __future__ import annotations

import os
import platform
from collections.abc import Mapping
from pathlib import Path

from optees.domain.entities.update import UpdatePlan, UpdatePlatform


class UpdateStagingService:
    """Resolve a persistent, user-owned staging directory for update assets."""

    def __init__(
        self,
        *,
        system_name: str | None = None,
        environment: Mapping[str, str] | None = None,
        home: Path | None = None,
    ) -> None:
        self._system_name = system_name
        self._environment = environment
        self._home = home

    def directory_for(self, plan: UpdatePlan) -> Path:
        root = self._root_for(plan.platform)
        return root / Path(plan.staging_subdirectory)

    def _root_for(self, target_platform: UpdatePlatform) -> Path:
        current = _platform_from_system_name(self._system_name or platform.system())
        if current is not target_platform:
            raise RuntimeError("Cannot stage an update for another platform.")

        environment = self._environment if self._environment is not None else os.environ
        home = Path(self._home) if self._home is not None else Path.home()
        if current is UpdatePlatform.WINDOWS:
            local_app_data = environment.get("LOCALAPPDATA")
            base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
            return base / "Optees" / "updates"
        if current is UpdatePlatform.MACOS:
            return home / "Library" / "Caches" / "Optees" / "updates"

        xdg_cache = environment.get("XDG_CACHE_HOME")
        base = Path(xdg_cache) if xdg_cache else home / ".cache"
        return base / "optees" / "updates"


def _platform_from_system_name(value: str) -> UpdatePlatform:
    aliases = {
        "darwin": UpdatePlatform.MACOS,
        "macos": UpdatePlatform.MACOS,
        "windows": UpdatePlatform.WINDOWS,
        "linux": UpdatePlatform.LINUX,
    }
    try:
        return aliases[(value or "").strip().lower()]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported update platform: {value}") from exc
