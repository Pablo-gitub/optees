from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import PurePath

from optees.application.contracts.local_export import LocalExportResult
from optees.data.adapters.settings import LocalExportSettings


class ConfiguredLocalExportAdapter:
    """Atomically exports verified bytes inside the configured directory only."""

    def __init__(self, settings: LocalExportSettings | None = None) -> None:
        self._settings = settings or LocalExportSettings()

    def export(
        self,
        content: bytes,
        *,
        suggested_filename: str,
        media_type: str,
        expected_sha256: str,
        filename: str | None = None,
        overwrite: bool = False,
    ) -> LocalExportResult:
        digest = hashlib.sha256(content).hexdigest()
        if digest != expected_sha256:
            raise ValueError("export content failed its SHA-256 integrity check")
        chosen = filename or suggested_filename
        if not _is_safe_filename(chosen):
            raise ValueError("filename must be a safe file name without a path")

        root = self._settings.get_directory()
        root.mkdir(parents=True, exist_ok=True)
        destination = root / chosen
        if destination.exists() and not overwrite:
            raise FileExistsError(f"export already exists: {chosen}")
        temporary = root / f".{chosen}.{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return LocalExportResult(
            filename=chosen,
            path=str(destination),
            media_type=media_type,
            size_bytes=len(content),
            sha256=digest,
        )


def _is_safe_filename(value: str) -> bool:
    path = PurePath(value)
    return (
        bool(value)
        and len(value) <= 180
        and path.name == value
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]*", value) is not None
    )
