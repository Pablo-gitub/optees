from __future__ import annotations

import hashlib
import io
from pathlib import Path
import zipfile

import pytest

from scripts import fetch_maros_meszaros_benchmark as acquisition


def _archive_bytes(filename: str, content: bytes) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, content)
    return stream.getvalue()


def test_selected_extraction_verifies_bytes_and_repairs_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = b"NAME TEST\r\nENDATA\r\n"
    digest = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(
        acquisition,
        "SELECTED_INSTANCE_MANIFEST",
        {"TEST.QPS": ("DATA.ZIP", digest)},
    )
    archive = _archive_bytes("nested/TEST.QPS", content)

    assert acquisition._safe_extract_selected(archive, "DATA.ZIP", tmp_path) == 1
    assert (tmp_path / "TEST.QPS").read_bytes() == content

    (tmp_path / "TEST.QPS").unlink()
    assert acquisition._safe_extract_selected(archive, "DATA.ZIP", tmp_path) == 1
    assert acquisition.verify_selected_instances(tmp_path, verbose=False)


def test_selected_extraction_rejects_tampering_and_duplicate_basename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = b"expected"
    monkeypatch.setattr(
        acquisition,
        "SELECTED_INSTANCE_MANIFEST",
        {"TEST.QPS": ("DATA.ZIP", hashlib.sha256(expected).hexdigest())},
    )
    with pytest.raises(ValueError, match="Checksum error"):
        acquisition._safe_extract_selected(
            _archive_bytes("TEST.QPS", b"tampered"), "DATA.ZIP", tmp_path
        )

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("a/TEST.QPS", expected)
        archive.writestr("b/TEST.QPS", expected)
    with pytest.raises(ValueError, match="Duplicate selected archive entry"):
        acquisition._safe_extract_selected(stream.getvalue(), "DATA.ZIP", tmp_path)


def test_selected_extraction_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Insecure zip entry"):
        acquisition._safe_extract_selected(
            _archive_bytes("../TEST.QPS", b"data"), "DATA.ZIP", tmp_path
        )


def test_check_only_is_read_only_for_missing_and_invalid_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(acquisition, "ARCHIVES_MANIFEST", {})
    monkeypatch.setattr(acquisition, "SELECTED_INSTANCE_MANIFEST", {})
    assert acquisition.fetch_and_verify(missing, check_only=True, verbose=False)
    assert not missing.exists()

    target = tmp_path / "existing"
    archive_path = target / "archives" / "DATA.ZIP"
    archive_path.parent.mkdir(parents=True)
    archive_path.write_bytes(b"invalid")
    monkeypatch.setattr(
        acquisition,
        "ARCHIVES_MANIFEST",
        {
            "DATA.ZIP": {
                "url": "http://www.doc.ic.ac.uk/~im/DATA.ZIP",
                "sha256": hashlib.sha256(b"expected").hexdigest(),
                "max_bytes": 100,
                "is_zip": True,
            }
        },
    )
    assert not acquisition.fetch_and_verify(target, check_only=True, verbose=False)
    assert archive_path.read_bytes() == b"invalid"
