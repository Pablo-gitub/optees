from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from optees.application.usecases.check_for_updates_usecase import (
    CheckForUpdatesUseCase,
    build_update_plan,
    is_newer_version,
)
from optees.application.usecases.download_update_usecase import DownloadUpdateUseCase
from optees.domain.entities.update import (
    AppRelease,
    CpuArchitecture,
    ReleaseAsset,
    UpdateArtifactKind,
    UpdateHandoffMethod,
    UpdatePlatform,
)


class FakeUpdateProvider:
    def __init__(self, release: AppRelease):
        self.release = release
        self.downloaded = None
        self.checksum = None

    def get_latest_release(self) -> AppRelease:
        return self.release

    def download_asset(
        self,
        asset: ReleaseAsset,
        destination_dir: Path,
        *,
        checksum_asset: ReleaseAsset | None = None,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> Path:
        self.downloaded = asset
        self.checksum = checksum_asset
        destination_dir.mkdir(parents=True, exist_ok=True)
        path = destination_dir / asset.name
        path.write_bytes(b"installer")
        if progress is not None:
            progress(len(b"installer"), len(b"installer"))
        return path


def _release(version: str, *asset_names: str) -> AppRelease:
    return AppRelease(
        tag_name=f"v{version}",
        version=version,
        html_url="https://github.com/Pablo-gitub/optees/releases/latest",
        assets=tuple(
            ReleaseAsset(name=name, download_url=f"https://example.test/{name}")
            for name in asset_names
        ),
    )


def test_check_detects_newer_macos_arm_release():
    provider = FakeUpdateProvider(
        _release("0.2.0", "optees-macos-arm64.dmg", "SHA256SUMS")
    )
    result = CheckForUpdatesUseCase(
        provider,
        current_version="0.1.0",
        system_name="Darwin",
        machine="arm64",
    ).execute()

    assert result.update_available is True
    assert result.latest_version == "0.2.0"
    assert result.asset is not None
    assert result.asset.name == "optees-macos-arm64.dmg"
    assert result.plan is not None
    assert result.plan.platform is UpdatePlatform.MACOS
    assert result.plan.architecture is CpuArchitecture.ARM64
    assert result.plan.artifact_kind is UpdateArtifactKind.MACOS_DMG
    assert result.plan.handoff_method is UpdateHandoffMethod.OPEN_DISK_IMAGE
    assert result.plan.staging_subdirectory == "0.2.0/macos-arm64"
    assert result.plan.checksum_asset is not None
    assert result.plan.manual_action_required is True


def test_check_hides_update_when_current_version_is_latest():
    provider = FakeUpdateProvider(_release("0.1.0", "optees-macos-arm64.dmg"))
    result = CheckForUpdatesUseCase(
        provider,
        current_version="0.1.0",
        system_name="Darwin",
        machine="arm64",
    ).execute()

    assert result.update_available is False
    assert result.asset is None


def test_check_reports_no_update_when_platform_asset_is_missing():
    provider = FakeUpdateProvider(_release("0.2.0", "optees-windows-x64.zip"))
    result = CheckForUpdatesUseCase(
        provider,
        current_version="0.1.0",
        system_name="Darwin",
        machine="arm64",
    ).execute()

    assert result.update_available is False
    assert result.latest_version == "0.2.0"
    assert "no compatible release package" in result.message


@pytest.mark.parametrize(
    ("system_name", "machine"),
    [
        ("Darwin", "x86_64"),
        ("Windows", "arm64"),
        ("Linux", "aarch64"),
        ("FreeBSD", "x86_64"),
        ("Windows", "i686"),
    ],
)
def test_update_plan_rejects_unsupported_platform_architecture_pairs(
    system_name,
    machine,
):
    release = _release(
        "0.2.0",
        "optees-macos-arm64.dmg",
        "optees-windows-x64.zip",
        "optees-linux-x86_64.AppImage",
    )

    assert (
        build_update_plan(release, system_name=system_name, machine=machine) is None
    )


def test_windows_plan_prefers_native_installer_over_portable_zip():
    release = _release(
        "0.2.0",
        "optees-windows-x64.zip",
        "optees-windows-x64-setup.exe",
        "SHA256SUMS",
    )

    plan = build_update_plan(release, system_name="Windows", machine="AMD64")

    assert plan is not None
    assert plan.artifact.name == "optees-windows-x64-setup.exe"
    assert plan.artifact_kind is UpdateArtifactKind.WINDOWS_INSTALLER
    assert plan.handoff_method is UpdateHandoffMethod.LAUNCH_INSTALLER


def test_windows_plan_labels_zip_as_portable_fallback():
    release = _release("0.2.0", "optees-windows-x64.zip")

    plan = build_update_plan(release, system_name="Windows", machine="x64")

    assert plan is not None
    assert plan.artifact_kind is UpdateArtifactKind.WINDOWS_PORTABLE_ZIP
    assert plan.handoff_method is UpdateHandoffMethod.OPEN_ARCHIVE


def test_linux_plan_accepts_amd64_alias_and_describes_appimage_handoff():
    release = _release("0.2.0", "optees-linux-x86_64.AppImage")

    plan = build_update_plan(release, system_name="Linux", machine="amd64")

    assert plan is not None
    assert plan.platform is UpdatePlatform.LINUX
    assert plan.architecture is CpuArchitecture.X86_64
    assert plan.artifact_kind is UpdateArtifactKind.LINUX_APPIMAGE
    assert plan.handoff_method is UpdateHandoffMethod.OPEN_PORTABLE_PACKAGE


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("v0.2.0", "0.1.9", True),
        ("0.1.0", "0.1.0", False),
        ("0.1.0", "0.1.1", False),
        ("1.0", "0.9.9", True),
    ],
)
def test_is_newer_version(candidate, current, expected):
    assert is_newer_version(candidate, current) is expected


def test_download_update_uses_checksum_asset(tmp_path):
    provider = FakeUpdateProvider(
        _release("0.2.0", "optees-linux-x86_64.AppImage", "SHA256SUMS")
    )
    result = CheckForUpdatesUseCase(
        provider,
        current_version="0.1.0",
        system_name="Linux",
        machine="x86_64",
    ).execute()

    path = DownloadUpdateUseCase(provider).execute(result, tmp_path)

    assert path.name == "optees-linux-x86_64.AppImage"
    assert provider.downloaded is not None
    assert provider.downloaded.name == "optees-linux-x86_64.AppImage"
    assert provider.checksum is not None
    assert provider.checksum.name == "SHA256SUMS"
