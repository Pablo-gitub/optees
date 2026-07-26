from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalExportResult:
    """Metadata for one explicit export into the user-authorized directory."""

    filename: str
    path: str
    media_type: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "path": self.path,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }
