from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from optees.data.adapters.artifacts.configured_local_export_adapter import (
    ConfiguredLocalExportAdapter,
)
from optees.data.adapters.settings import LocalExportSettings


def _adapter(tmp_path: Path) -> ConfiguredLocalExportAdapter:
    settings = LocalExportSettings(tmp_path / "settings.json")
    settings.set_directory(tmp_path / "exports")
    return ConfiguredLocalExportAdapter(settings)


def test_export_writes_verified_content_inside_configured_directory(tmp_path: Path):
    content = b"verified artifact"
    result = _adapter(tmp_path).export(
        content,
        suggested_filename="result.md",
        media_type="text/markdown",
        expected_sha256=hashlib.sha256(content).hexdigest(),
    )

    assert Path(result.path).read_bytes() == content
    assert Path(result.path).parent == tmp_path / "exports"
    assert result.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize("filename", ("../result.md", "nested/result.md", "/tmp/x"))
def test_export_rejects_paths_instead_of_file_names(tmp_path: Path, filename: str):
    content = b"x"

    with pytest.raises(ValueError, match="safe file name"):
        _adapter(tmp_path).export(
            content,
            suggested_filename="result.md",
            filename=filename,
            media_type="text/markdown",
            expected_sha256=hashlib.sha256(content).hexdigest(),
        )


def test_export_rejects_modified_content_and_refuses_overwrite(tmp_path: Path):
    adapter = _adapter(tmp_path)
    content = b"original"
    digest = hashlib.sha256(content).hexdigest()
    adapter.export(
        content,
        suggested_filename="result.md",
        media_type="text/markdown",
        expected_sha256=digest,
    )

    with pytest.raises(FileExistsError):
        adapter.export(
            content,
            suggested_filename="result.md",
            media_type="text/markdown",
            expected_sha256=digest,
        )
    with pytest.raises(ValueError, match="integrity"):
        adapter.export(
            b"changed",
            suggested_filename="other.md",
            media_type="text/markdown",
            expected_sha256=digest,
        )
