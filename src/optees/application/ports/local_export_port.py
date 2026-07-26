from __future__ import annotations

from typing import Protocol

from optees.application.contracts.local_export import LocalExportResult


class LocalExportPort(Protocol):
    def export(
        self,
        content: bytes,
        *,
        suggested_filename: str,
        media_type: str,
        expected_sha256: str,
        filename: str | None = None,
        overwrite: bool = False,
    ) -> LocalExportResult: ...
