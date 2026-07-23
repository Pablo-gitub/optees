from __future__ import annotations

from typing import Protocol

from optees.application.contracts.artifact_storage import (
    ArtifactCleanupResult,
    ArtifactStorageStats,
    StoredArtifact,
    StoredArtifactPayload,
)


class ArtifactStoragePort(Protocol):
    """Bounded, session-local storage addressed only by opaque artifact IDs."""

    def store(
        self,
        content: bytes,
        *,
        media_type: str,
        ttl_seconds: int | None = None,
    ) -> StoredArtifact:
        ...

    def get(self, artifact_id: str) -> StoredArtifactPayload:
        ...

    def describe(self, artifact_id: str) -> StoredArtifact:
        ...

    def pin(self, artifact_id: str) -> None:
        ...

    def unpin(self, artifact_id: str) -> None:
        ...

    def cleanup_expired(self) -> ArtifactCleanupResult:
        ...

    def stats(self) -> ArtifactStorageStats:
        ...

    def close(self) -> None:
        ...
