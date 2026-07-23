from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_ARTIFACT_TTL_SECONDS = 60 * 60
DEFAULT_MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_SESSION_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_SESSION_ARTIFACTS = 128


@dataclass(frozen=True)
class StoredArtifact:
    """Transport-neutral metadata for one materialized artifact."""

    artifact_id: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: str
    expires_at: str

    def __post_init__(self) -> None:
        if not re.fullmatch(
            r"artifact-[A-Za-z0-9][A-Za-z0-9_-]{0,127}", self.artifact_id
        ):
            raise ValueError("stored artifact_id must be an opaque artifact identifier")
        if not self.media_type.strip():
            raise ValueError("stored artifact media_type must not be empty")
        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes < 1
        ):
            raise ValueError("stored artifact size_bytes must be positive")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("stored artifact sha256 must be lowercase hexadecimal")
        if not self.created_at.strip() or not self.expires_at.strip():
            raise ValueError("stored artifact timestamps must not be empty")


@dataclass(frozen=True)
class StoredArtifactPayload:
    artifact: StoredArtifact
    content: bytes


@dataclass(frozen=True)
class ArtifactStorageStats:
    artifact_count: int
    total_bytes: int
    pinned_count: int
    max_artifacts: int
    max_total_bytes: int
    max_artifact_bytes: int
    default_ttl_seconds: int


@dataclass(frozen=True)
class ArtifactCleanupResult:
    removed_count: int
    removed_bytes: int


class ArtifactStorageError(RuntimeError):
    """Base class for local artifact-storage failures."""


class ArtifactNotFoundError(ArtifactStorageError):
    pass


class ArtifactExpiredError(ArtifactStorageError):
    pass


class ArtifactCapacityError(ArtifactStorageError):
    pass


class ArtifactIntegrityError(ArtifactStorageError):
    pass


class ArtifactStorageClosedError(ArtifactStorageError):
    pass
