from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def default_export_directory() -> Path:
    return Path.home() / "Downloads" / "Optees"


def settings_file_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "Optees" / "settings.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Optees" / "settings.json"
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "optees" / "settings.json"


class LocalExportSettings:
    """Small cross-process JSON setting shared by GUI, REST companions, and MCP."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or settings_file_path()

    def get_directory(self) -> Path:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            value = payload.get("export_directory")
            if isinstance(value, str) and value.strip():
                return Path(value).expanduser()
        except (FileNotFoundError, OSError, ValueError, TypeError):
            pass
        return default_export_directory()

    def set_directory(self, directory: str | Path) -> Path:
        selected = Path(directory).expanduser()
        if not selected.is_absolute():
            raise ValueError("export directory must be absolute")
        selected.mkdir(parents=True, exist_ok=True)
        payload = self._read_payload()
        payload["export_directory"] = str(selected)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._path)
        return selected

    def _read_payload(self) -> dict[str, object]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError, TypeError):
            return {}
        return payload if isinstance(payload, dict) else {}
