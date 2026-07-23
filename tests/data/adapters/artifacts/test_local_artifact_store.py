from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from optees.application.contracts.artifact_storage import (
    ArtifactCapacityError,
    ArtifactExpiredError,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStorageClosedError,
)
from optees.data.adapters.artifacts.local_artifact_store import LocalArtifactStore


class FakeClock:
    def __init__(self, value: float = 1_700_000_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _ids(*values: str):
    iterator = iter(values)
    return lambda: next(iterator)


def _session_directory(parent: Path) -> Path:
    children = [
        path
        for path in parent.iterdir()
        if path.is_dir() and path.name.startswith("optees-artifacts-")
    ]
    assert len(children) == 1
    return children[0]


def test_store_is_session_isolated_private_hashed_and_removed_on_close(tmp_path):
    clock = FakeClock()
    store = LocalArtifactStore(
        parent_directory=tmp_path,
        clock=clock,
        id_factory=_ids("artifact-alpha"),
    )
    session_directory = _session_directory(tmp_path)

    metadata = store.store(b"name,value\nx,1\n", media_type="text/csv")
    payload = store.get(metadata.artifact_id)

    assert metadata.sha256 == hashlib.sha256(payload.content).hexdigest()
    assert metadata.size_bytes == len(payload.content)
    assert metadata.created_at == "2023-11-14T22:13:20Z"
    assert metadata.expires_at == "2023-11-14T23:13:20Z"
    assert payload.artifact == metadata
    assert session_directory.stat().st_mode & 0o777 == 0o700
    assert len(list(session_directory.iterdir())) == 1
    assert next(session_directory.iterdir()).stat().st_mode & 0o777 == 0o600

    store.close()

    assert not session_directory.exists()
    with pytest.raises(ArtifactStorageClosedError):
        store.stats()


def test_per_file_limit_rejects_content_without_writing(tmp_path):
    with LocalArtifactStore(
        parent_directory=tmp_path,
        max_artifact_bytes=4,
        max_total_bytes=8,
    ) as store:
        with pytest.raises(ArtifactCapacityError, match="file limit"):
            store.store(b"12345", media_type="application/octet-stream")

        assert store.stats().artifact_count == 0
        assert not list(_session_directory(tmp_path).iterdir())


def test_capacity_evicts_oldest_unpinned_artifacts_by_count_and_bytes(tmp_path):
    with LocalArtifactStore(
        parent_directory=tmp_path,
        max_artifact_bytes=6,
        max_total_bytes=6,
        max_artifacts=2,
        id_factory=_ids("artifact-one", "artifact-two", "artifact-three"),
    ) as store:
        first = store.store(b"111", media_type="text/plain")
        second = store.store(b"22", media_type="text/plain")
        third = store.store(b"3333", media_type="text/plain")

        with pytest.raises(ArtifactNotFoundError):
            store.get(first.artifact_id)
        assert store.get(second.artifact_id).content == b"22"
        assert store.get(third.artifact_id).content == b"3333"
        assert store.stats().artifact_count == 2
        assert store.stats().total_bytes == 6


def test_capacity_failure_does_not_evict_when_pins_make_request_impossible(tmp_path):
    with LocalArtifactStore(
        parent_directory=tmp_path,
        max_artifact_bytes=4,
        max_total_bytes=5,
        max_artifacts=3,
        id_factory=_ids("artifact-old", "artifact-pinned", "artifact-new"),
    ) as store:
        old = store.store(b"1", media_type="text/plain")
        pinned = store.store(b"2222", media_type="text/plain")
        store.pin(pinned.artifact_id)

        with pytest.raises(ArtifactCapacityError, match="pinned"):
            store.store(b"33", media_type="text/plain")

        assert store.get(old.artifact_id).content == b"1"
        assert store.get(pinned.artifact_id).content == b"2222"


def test_expiration_cleanup_is_deterministic_and_respects_pins(tmp_path):
    clock = FakeClock()
    with LocalArtifactStore(
        parent_directory=tmp_path,
        default_ttl_seconds=10,
        clock=clock,
        id_factory=_ids("artifact-free", "artifact-pinned"),
    ) as store:
        free = store.store(b"free", media_type="text/plain")
        pinned = store.store(b"pin", media_type="text/plain")
        store.pin(pinned.artifact_id)
        clock.advance(10)

        with pytest.raises(ArtifactExpiredError):
            store.describe(free.artifact_id)
        assert store.get(pinned.artifact_id).content == b"pin"
        assert store.cleanup_expired().removed_count == 0

        store.unpin(pinned.artifact_id)
        with pytest.raises(ArtifactNotFoundError):
            store.describe(pinned.artifact_id)


@pytest.mark.parametrize(
    "artifact_id",
    (
        "../secret",
        "artifact-../../secret",
        "/absolute/path",
        "artifact-valid/child",
        "artifact-",
        "",
    ),
)
def test_lookup_accepts_only_opaque_artifact_ids(tmp_path, artifact_id):
    outside = tmp_path / "secret"
    outside.write_text("unchanged", encoding="utf-8")
    with LocalArtifactStore(parent_directory=tmp_path) as store:
        with pytest.raises(ArtifactNotFoundError):
            store.get(artifact_id)
        assert outside.read_text(encoding="utf-8") == "unchanged"


def test_tampered_content_is_rejected_and_quarantined(tmp_path):
    with LocalArtifactStore(
        parent_directory=tmp_path,
        id_factory=_ids("artifact-tampered"),
    ) as store:
        artifact = store.store(b"trusted", media_type="text/plain")
        stored_file = next(_session_directory(tmp_path).iterdir())
        stored_file.write_bytes(b"changed")

        with pytest.raises(ArtifactIntegrityError, match="SHA-256"):
            store.get(artifact.artifact_id)
        with pytest.raises(ArtifactNotFoundError):
            store.get(artifact.artifact_id)
        assert store.stats().total_bytes == 0


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
def test_symlink_replacement_never_reads_outside_session(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("outside secret", encoding="utf-8")
    with LocalArtifactStore(
        parent_directory=tmp_path,
        id_factory=_ids("artifact-link"),
    ) as store:
        artifact = store.store(b"trusted", media_type="text/plain")
        stored_file = next(_session_directory(tmp_path).iterdir())
        stored_file.unlink()
        stored_file.symlink_to(outside)

        with pytest.raises(ArtifactIntegrityError):
            store.get(artifact.artifact_id)
        assert outside.read_text(encoding="utf-8") == "outside secret"


def test_explicit_cleanup_reports_removed_count_and_bytes(tmp_path):
    clock = FakeClock()
    with LocalArtifactStore(
        parent_directory=tmp_path,
        clock=clock,
        id_factory=_ids("artifact-short", "artifact-long"),
    ) as store:
        store.store(b"12", media_type="text/plain", ttl_seconds=2)
        store.store(b"345", media_type="text/plain", ttl_seconds=20)
        clock.advance(3)

        result = store.cleanup_expired()

        assert result.removed_count == 1
        assert result.removed_bytes == 2
        assert store.stats().artifact_count == 1
        assert store.stats().total_bytes == 3
