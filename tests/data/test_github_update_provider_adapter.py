from __future__ import annotations

from optees.data.adapters.github.update_provider_adapter import (
    parse_sha256sums,
    release_from_github_json,
)


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
