from __future__ import annotations

import hashlib
import ssl
from io import BytesIO

import pytest

import optees.data.adapters.github.update_provider_adapter as update_provider_module

from optees.application.ports.update_provider_port import (
    UpdateDownloadError,
    UpdateVerificationError,
)
from optees.data.adapters.github.update_provider_adapter import (
    GitHubUpdateProvider,
    parse_sha256sums,
    release_from_github_json,
)
from optees.domain.entities.update import ReleaseAsset


def test_provider_uses_bundled_ca_context_for_https(monkeypatch):
    captured = {}

    def fake_urlopen(request, *, timeout, context):
        captured.update(request=request, timeout=timeout, context=context)
        return BytesIO(b"{}")

    monkeypatch.setattr(update_provider_module, "urlopen", fake_urlopen)
    provider = GitHubUpdateProvider(timeout_seconds=3)

    with provider._open("https://api.github.com/example") as response:
        assert response.read() == b"{}"

    assert captured["timeout"] == 3
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["context"].check_hostname is True


def test_provider_adds_optional_github_authorization(monkeypatch):
    captured = {}

    def fake_urlopen(request, *, timeout, context):
        captured["request"] = request
        return BytesIO(b"{}")

    monkeypatch.setattr(update_provider_module, "urlopen", fake_urlopen)

    with GitHubUpdateProvider(api_token=" release-token ")._open(
        "https://api.github.com/example"
    ):
        pass

    assert captured["request"].get_header("Authorization") == "Bearer release-token"


def test_provider_omits_authorization_without_token(monkeypatch):
    captured = {}

    def fake_urlopen(request, *, timeout, context):
        captured["request"] = request
        return BytesIO(b"{}")

    monkeypatch.setattr(update_provider_module, "urlopen", fake_urlopen)

    with GitHubUpdateProvider()._open("https://api.github.com/example"):
        pass

    assert captured["request"].get_header("Authorization") is None


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
    progress = []

    path = provider.download_asset(
        ReleaseAsset("package.bin", "https://example.test/package", size=len(payload)),
        tmp_path,
        checksum_asset=ReleaseAsset("SHA256SUMS", "https://example.test/checksums"),
        progress=lambda downloaded, total: progress.append((downloaded, total)),
    )

    assert path.read_bytes() == payload
    assert not (tmp_path / "package.bin.part").exists()
    assert progress == [(0, len(payload)), (len(payload), len(payload))]


def test_download_fails_closed_when_checksum_entry_is_missing(monkeypatch, tmp_path):
    provider = GitHubUpdateProvider(max_asset_bytes=1024)
    responses = {
        "https://example.test/package": b"release",
        "https://example.test/checksums": f"{'a' * 64}  another.bin\n".encode(),
    }
    monkeypatch.setattr(provider, "_open", lambda url: BytesIO(responses[url]))

    with pytest.raises(UpdateVerificationError, match="no entry"):
        provider.download_asset(
            ReleaseAsset("package.bin", "https://example.test/package"),
            tmp_path,
            checksum_asset=ReleaseAsset("SHA256SUMS", "https://example.test/checksums"),
        )

    assert not (tmp_path / "package.bin.part").exists()


@pytest.mark.parametrize("name", ["../package.bin", "/tmp/package.bin", "dir/package.bin"])
def test_download_rejects_unsafe_asset_names(name, tmp_path):
    with pytest.raises(UpdateDownloadError, match="safe filename"):
        GitHubUpdateProvider().download_asset(
            ReleaseAsset(name, "https://example.test/package"), tmp_path
        )


def test_download_rejects_asset_larger_than_limit(tmp_path):
    with pytest.raises(UpdateDownloadError, match="download limit"):
        GitHubUpdateProvider(max_asset_bytes=4).download_asset(
            ReleaseAsset("package.bin", "https://example.test/package", size=5),
            tmp_path,
        )


def test_download_removes_partial_file_on_size_mismatch(monkeypatch, tmp_path):
    provider = GitHubUpdateProvider(max_asset_bytes=1024)
    monkeypatch.setattr(provider, "_open", lambda _url: BytesIO(b"short"))

    with pytest.raises(UpdateDownloadError, match="size mismatch"):
        provider.download_asset(
            ReleaseAsset("package.bin", "https://example.test/package", size=10),
            tmp_path,
        )

    assert not (tmp_path / "package.bin.part").exists()
