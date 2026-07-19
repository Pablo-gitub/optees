from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

from optees.data.adapters.github.update_provider_adapter import (
    GitHubUpdateProvider,
    parse_sha256sums,
    release_from_github_json,
)
from optees.domain.entities.update import ReleaseAsset


def test_release_from_github_json_maps_assets():
    release = release_from_github_json(
        {
            "tag_name": "v0.2.0",
            "html_url": "https://github.com/Pablo-gitub/optees/releases/tag/v0.2.0",
            "body": "notes",
            "prerelease": False,
            "assets": [
                {
                    "name": "optees-macos-arm64.dmg",
                    "browser_download_url": "https://example.test/optees.dmg",
                    "size": 42,
                },
                {
                    "name": "SHA256SUMS",
                    "browser_download_url": "https://example.test/SHA256SUMS",
                    "size": 128,
                },
            ],
        }
    )

    assert release.version == "0.2.0"
    assert release.asset_named("optees-macos-arm64.dmg") is not None
    assert release.asset_named("SHA256SUMS") is not None


def test_parse_sha256sums_supports_standard_output():
    digest = "a" * 64
    checksums = parse_sha256sums(
        f"{digest}  optees-macos-arm64.dmg\n"
        f"{'b' * 64} *optees-linux-x86_64.AppImage\n"
    )

    assert checksums["optees-macos-arm64.dmg"] == digest
    assert checksums["optees-linux-x86_64.AppImage"] == "b" * 64


def test_download_verifies_checksum_and_replaces_partial_file(monkeypatch, tmp_path):
    payload = b"verified release"
    digest = hashlib.sha256(payload).hexdigest()
    responses = {
        "https://example.test/package": payload,
        "https://example.test/checksums": f"{digest}  package.bin\n".encode(),
    }
    provider = GitHubUpdateProvider(max_asset_bytes=1024)
    monkeypatch.setattr(provider, "_open", lambda url: BytesIO(responses[url]))
    (tmp_path / "package.bin.part").write_bytes(b"stale")

    path = provider.download_asset(
        ReleaseAsset("package.bin", "https://example.test/package", size=len(payload)),
        tmp_path,
        checksum_asset=ReleaseAsset("SHA256SUMS", "https://example.test/checksums"),
    )

    assert path.read_bytes() == payload
    assert not (tmp_path / "package.bin.part").exists()


def test_download_fails_closed_when_checksum_entry_is_missing(monkeypatch, tmp_path):
    provider = GitHubUpdateProvider(max_asset_bytes=1024)
    responses = {
        "https://example.test/package": b"release",
        "https://example.test/checksums": f"{'a' * 64}  another.bin\n".encode(),
    }
    monkeypatch.setattr(provider, "_open", lambda url: BytesIO(responses[url]))

    with pytest.raises(ValueError, match="no entry"):
        provider.download_asset(
            ReleaseAsset("package.bin", "https://example.test/package"),
            tmp_path,
            checksum_asset=ReleaseAsset("SHA256SUMS", "https://example.test/checksums"),
        )

    assert not (tmp_path / "package.bin.part").exists()


@pytest.mark.parametrize("name", ["../package.bin", "/tmp/package.bin", "dir/package.bin"])
def test_download_rejects_unsafe_asset_names(name, tmp_path):
    with pytest.raises(ValueError, match="safe filename"):
        GitHubUpdateProvider().download_asset(
            ReleaseAsset(name, "https://example.test/package"), tmp_path
        )


def test_download_rejects_asset_larger_than_limit(tmp_path):
    with pytest.raises(ValueError, match="download limit"):
        GitHubUpdateProvider(max_asset_bytes=4).download_asset(
            ReleaseAsset("package.bin", "https://example.test/package", size=5),
            tmp_path,
        )


def test_download_removes_partial_file_on_size_mismatch(monkeypatch, tmp_path):
    provider = GitHubUpdateProvider(max_asset_bytes=1024)
    monkeypatch.setattr(provider, "_open", lambda _url: BytesIO(b"short"))

    with pytest.raises(ValueError, match="size mismatch"):
        provider.download_asset(
            ReleaseAsset("package.bin", "https://example.test/package", size=10),
            tmp_path,
        )

    assert not (tmp_path / "package.bin.part").exists()
