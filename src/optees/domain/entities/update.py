from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: Optional[int] = None


@dataclass(frozen=True)
class AppRelease:
    tag_name: str
    version: str
    html_url: str
    body: str = ""
    prerelease: bool = False
    assets: Tuple[ReleaseAsset, ...] = tuple()

    def asset_named(self, name: str) -> Optional[ReleaseAsset]:
        for asset in self.assets:
            if asset.name == name:
                return asset
        return None


class UpdatePlatform(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class CpuArchitecture(str, Enum):
    X86_64 = "x86_64"
    ARM64 = "arm64"


class UpdateArtifactKind(str, Enum):
    WINDOWS_INSTALLER = "windows_installer"
    WINDOWS_PORTABLE_ZIP = "windows_portable_zip"
    MACOS_DMG = "macos_dmg"
    LINUX_APPIMAGE = "linux_appimage"


class UpdateHandoffMethod(str, Enum):
    LAUNCH_INSTALLER = "launch_installer"
    OPEN_DISK_IMAGE = "open_disk_image"
    OPEN_ARCHIVE = "open_archive"
    OPEN_PORTABLE_PACKAGE = "open_portable_package"


class UpdateExecutionState(str, Enum):
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    VERIFICATION_FAILED = "verification_failed"
    INSTALLER_LAUNCHED = "installer_launched"
    MANUAL_ACTION_REQUIRED = "manual_action_required"
    REPLACEMENT_SCHEDULED = "replacement_scheduled"


@dataclass(frozen=True)
class UpdatePlan:
    """Deterministic platform contract for one release artifact.

    The plan describes what Optees may download and how control is handed to
    the operating system. `manual_action_required` remains true for every
    current package: opening a file is not equivalent to installing an update.
    """

    platform: UpdatePlatform
    architecture: CpuArchitecture
    artifact: ReleaseAsset
    artifact_kind: UpdateArtifactKind
    handoff_method: UpdateHandoffMethod
    staging_subdirectory: str
    checksum_asset: Optional[ReleaseAsset] = None
    manual_action_required: bool = True


@dataclass(frozen=True)
class UpdateHandoffResult:
    plan: UpdatePlan
    local_path: str
    state: UpdateExecutionState
    started: bool


@dataclass(frozen=True)
class UpdateExecutionSnapshot:
    plan: UpdatePlan
    state: UpdateExecutionState
    local_path: Optional[str] = None
    bytes_downloaded: int = 0
    total_bytes: Optional[int] = None
    message: str = ""


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: Optional[str]
    update_available: bool
    release: Optional[AppRelease] = None
    asset: Optional[ReleaseAsset] = None
    plan: Optional[UpdatePlan] = None
    message: str = ""

    @staticmethod
    def unavailable(current_version: str, message: str = "") -> "UpdateCheckResult":
        return UpdateCheckResult(
            current_version=current_version,
            latest_version=None,
            update_available=False,
            message=message,
        )
