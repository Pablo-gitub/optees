from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Callable
from uuid import uuid4

from optees.application.contracts.artifact_storage import (
    DEFAULT_ARTIFACT_TTL_SECONDS,
    DEFAULT_MAX_ARTIFACT_BYTES,
    DEFAULT_MAX_SESSION_ARTIFACTS,
    DEFAULT_MAX_SESSION_BYTES,
    ArtifactCapacityError,
    ArtifactCleanupResult,
    ArtifactExpiredError,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStorageClosedError,
    ArtifactStorageError,
    ArtifactStorageStats,
    StoredArtifact,
    StoredArtifactPayload,
)


_ARTIFACT_ID_PATTERN = re.compile(r"artifact-[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
_ID_ATTEMPTS = 8


@dataclass
class _StoredRecord:
    metadata: StoredArtifact
    file_name: str
    expires_at_epoch: float
    pin_count: int = 0


class LocalArtifactStore:
    """Session-scoped filesystem storage with bounded retention and integrity checks."""

    def __init__(
        self,
        *,
        parent_directory: Path | None = None,
        max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
        max_total_bytes: int = DEFAULT_MAX_SESSION_BYTES,
        max_artifacts: int = DEFAULT_MAX_SESSION_ARTIFACTS,
        default_ttl_seconds: int = DEFAULT_ARTIFACT_TTL_SECONDS,
        clock: Callable[[], float] = time.time,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        _require_positive_int(max_artifact_bytes, "max_artifact_bytes")
        _require_positive_int(max_total_bytes, "max_total_bytes")
        _require_positive_int(max_artifacts, "max_artifacts")
        _require_positive_int(default_ttl_seconds, "default_ttl_seconds")
        if max_artifact_bytes > max_total_bytes:
            raise ValueError("max_artifact_bytes must not exceed max_total_bytes")

        parent = None if parent_directory is None else str(parent_directory)
        self._root = Path(tempfile.mkdtemp(prefix="optees-artifacts-", dir=parent))
        self._root.chmod(0o700)
        self._max_artifact_bytes = max_artifact_bytes
        self._max_total_bytes = max_total_bytes
        self._max_artifacts = max_artifacts
        self._default_ttl_seconds = default_ttl_seconds
        self._clock = clock
        self._id_factory = id_factory or (lambda: f"artifact-{uuid4()}")
        self._records: OrderedDict[str, _StoredRecord] = OrderedDict()
        self._total_bytes = 0
        self._closed = False
        self._lock = RLock()

    def __enter__(self) -> LocalArtifactStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def store(
        self,
        content: bytes,
        *,
        media_type: str,
        ttl_seconds: int | None = None,
    ) -> StoredArtifact:
        if not isinstance(content, bytes) or not content:
            raise ValueError("artifact content must be non-empty bytes")
        if not media_type.strip():
            raise ValueError("artifact media_type must not be empty")
        effective_ttl = (
            self._default_ttl_seconds if ttl_seconds is None else ttl_seconds
        )
        _require_positive_int(effective_ttl, "ttl_seconds")
        size_bytes = len(content)
        if size_bytes > self._max_artifact_bytes:
            raise ArtifactCapacityError(
                f"artifact exceeds the {self._max_artifact_bytes}-byte file limit"
            )

        with self._lock:
            self._require_open()
            now = self._clock()
            self._cleanup_expired_locked(now)
            self._make_space_locked(size_bytes)
            artifact_id = self._new_artifact_id_locked()
            file_name = f"{artifact_id}.bin"
            destination = self._root / file_name
            digest = hashlib.sha256(content).hexdigest()
            self._write_atomic(destination, content)

            metadata = StoredArtifact(
                artifact_id=artifact_id,
                media_type=media_type,
                size_bytes=size_bytes,
                sha256=digest,
                created_at=_iso_timestamp(now),
                expires_at=_iso_timestamp(now + effective_ttl),
            )
            self._records[artifact_id] = _StoredRecord(
                metadata=metadata,
                file_name=file_name,
                expires_at_epoch=now + effective_ttl,
            )
            self._total_bytes += size_bytes
            return metadata

    def get(self, artifact_id: str) -> StoredArtifactPayload:
        with self._lock:
            record = self._record_for_access_locked(artifact_id)
            path = self._root / record.file_name
            try:
                content = self._read_regular_file(path)
            except (OSError, ArtifactIntegrityError) as exc:
                self._remove_locked(artifact_id)
                raise ArtifactIntegrityError(
                    "artifact content is missing or is not a regular file"
                ) from exc

            digest = hashlib.sha256(content).hexdigest()
            if (
                len(content) != record.metadata.size_bytes
                or digest != record.metadata.sha256
            ):
                self._remove_locked(artifact_id)
                raise ArtifactIntegrityError(
                    "artifact content failed its size or SHA-256 integrity check"
                )
            return StoredArtifactPayload(record.metadata, content)

    def describe(self, artifact_id: str) -> StoredArtifact:
        with self._lock:
            return self._record_for_access_locked(artifact_id).metadata

    def pin(self, artifact_id: str) -> None:
        with self._lock:
            record = self._record_for_access_locked(artifact_id)
            record.pin_count += 1

    def unpin(self, artifact_id: str) -> None:
        with self._lock:
            self._require_open()
            _validate_lookup_id(artifact_id)
            record = self._records.get(artifact_id)
            if record is None:
                raise ArtifactNotFoundError("artifact was not found")
            if record.pin_count < 1:
                raise ValueError("artifact is not pinned")
            record.pin_count -= 1
            if record.pin_count == 0 and record.expires_at_epoch <= self._clock():
                self._remove_locked(artifact_id)

    def cleanup_expired(self) -> ArtifactCleanupResult:
        with self._lock:
            self._require_open()
            return self._cleanup_expired_locked(self._clock())

    def stats(self) -> ArtifactStorageStats:
        with self._lock:
            self._require_open()
            self._cleanup_expired_locked(self._clock())
            return ArtifactStorageStats(
                artifact_count=len(self._records),
                total_bytes=self._total_bytes,
                pinned_count=sum(
                    1 for record in self._records.values() if record.pin_count > 0
                ),
                max_artifacts=self._max_artifacts,
                max_total_bytes=self._max_total_bytes,
                max_artifact_bytes=self._max_artifact_bytes,
                default_ttl_seconds=self._default_ttl_seconds,
            )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                shutil.rmtree(self._root)
            except FileNotFoundError:
                pass
            self._records.clear()
            self._total_bytes = 0
            self._closed = True

    def _record_for_access_locked(self, artifact_id: str) -> _StoredRecord:
        self._require_open()
        _validate_lookup_id(artifact_id)
        record = self._records.get(artifact_id)
        if record is None:
            raise ArtifactNotFoundError("artifact was not found")
        if record.pin_count == 0 and record.expires_at_epoch <= self._clock():
            self._remove_locked(artifact_id)
            raise ArtifactExpiredError("artifact has expired")
        return record

    def _cleanup_expired_locked(self, now: float) -> ArtifactCleanupResult:
        expired = [
            artifact_id
            for artifact_id, record in self._records.items()
            if record.pin_count == 0 and record.expires_at_epoch <= now
        ]
        removed_bytes = sum(
            self._records[artifact_id].metadata.size_bytes for artifact_id in expired
        )
        for artifact_id in expired:
            self._remove_locked(artifact_id)
        return ArtifactCleanupResult(len(expired), removed_bytes)

    def _make_space_locked(self, incoming_bytes: int) -> None:
        candidates: list[str] = []
        projected_count = len(self._records) + 1
        projected_bytes = self._total_bytes + incoming_bytes
        for artifact_id, record in self._records.items():
            if (
                projected_count <= self._max_artifacts
                and projected_bytes <= self._max_total_bytes
            ):
                break
            if record.pin_count > 0:
                continue
            candidates.append(artifact_id)
            projected_count -= 1
            projected_bytes -= record.metadata.size_bytes

        if (
            projected_count > self._max_artifacts
            or projected_bytes > self._max_total_bytes
        ):
            raise ArtifactCapacityError(
                "artifact session capacity is occupied by pinned artifacts"
            )
        for artifact_id in candidates:
            self._remove_locked(artifact_id)

    def _new_artifact_id_locked(self) -> str:
        for _ in range(_ID_ATTEMPTS):
            artifact_id = self._id_factory()
            if (
                isinstance(artifact_id, str)
                and _ARTIFACT_ID_PATTERN.fullmatch(artifact_id)
                and artifact_id not in self._records
            ):
                return artifact_id
        raise ArtifactStorageError("could not allocate a unique artifact identifier")

    def _write_atomic(self, destination: Path, content: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".pending-",
            dir=self._root,
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            destination.chmod(0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    def _read_regular_file(self, path: Path) -> bytes:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            file_stat = os.fstat(handle.fileno())
            if not stat.S_ISREG(file_stat.st_mode):
                raise ArtifactIntegrityError("artifact content is not a regular file")
            return handle.read(self._max_artifact_bytes + 1)

    def _remove_locked(self, artifact_id: str) -> None:
        record = self._records.pop(artifact_id, None)
        if record is None:
            return
        self._total_bytes -= record.metadata.size_bytes
        path = self._root / record.file_name
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
            shutil.rmtree(path)
        else:
            path.unlink()

    def _require_open(self) -> None:
        if self._closed:
            raise ArtifactStorageClosedError("artifact storage session is closed")


def _validate_lookup_id(artifact_id: str) -> None:
    if not isinstance(artifact_id, str) or not _ARTIFACT_ID_PATTERN.fullmatch(
        artifact_id
    ):
        raise ArtifactNotFoundError("artifact was not found")


def _require_positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _iso_timestamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
