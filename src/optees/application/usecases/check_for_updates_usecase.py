from __future__ import annotations

import platform
import re
from typing import Optional

from optees.application.ports.update_provider_port import UpdateProviderPort
from optees.domain.entities.update import (
    AppRelease,
    CpuArchitecture,
    ReleaseAsset,
    UpdateArtifactKind,
    UpdateCheckResult,
    UpdateHandoffMethod,
    UpdatePlan,
    UpdatePlatform,
)


class CheckForUpdatesUseCase:
    """Compare the local app version with the latest GitHub release.

    Release tags are expected in the CI/CD form `vMAJOR.MINOR.PATCH`. The
    comparison is deliberately small and deterministic: it strips the optional
    leading `v`, ignores build metadata, and compares the numeric release tuple.
    Pre-release ordering is not used here because the GitHub `latest` endpoint
    already ignores pre-releases.
    """

    def __init__(
        self,
        provider: UpdateProviderPort,
        *,
        current_version: str,
        system_name: Optional[str] = None,
        machine: Optional[str] = None,
    ) -> None:
        self._provider = provider
        self._current_version = current_version
        self._system_name = system_name
        self._machine = machine

    def execute(self) -> UpdateCheckResult:
        release = self._provider.get_latest_release()
        latest = release.version or release.tag_name
        plan = build_update_plan(
            release,
            system_name=self._system_name or platform.system(),
            machine=self._machine or platform.machine(),
        )
        available = is_newer_version(latest, self._current_version)

        if available and plan is None:
            return UpdateCheckResult(
                current_version=self._current_version,
                latest_version=latest,
                update_available=False,
                release=release,
                message="A newer release exists, but no compatible release package was found.",
            )

        return UpdateCheckResult(
            current_version=self._current_version,
            latest_version=latest,
            update_available=available,
            release=release,
            asset=plan.artifact if available and plan is not None else None,
            plan=plan if available else None,
        )


def select_platform_asset(
    release: AppRelease,
    *,
    system_name: str,
    machine: str,
) -> Optional[ReleaseAsset]:
    plan = build_update_plan(release, system_name=system_name, machine=machine)
    return plan.artifact if plan is not None else None


def build_update_plan(
    release: AppRelease,
    *,
    system_name: str,
    machine: str,
) -> Optional[UpdatePlan]:
    platform_value = _normalize_platform(system_name)
    architecture = _normalize_architecture(machine)
    if platform_value is None or architecture is None:
        return None

    selection = _select_artifact_contract(release, platform_value, architecture)
    if selection is None:
        return None

    artifact, artifact_kind, handoff_method = selection
    version = release.version or release.tag_name.lstrip("vV") or "unknown"
    return UpdatePlan(
        platform=platform_value,
        architecture=architecture,
        artifact=artifact,
        artifact_kind=artifact_kind,
        handoff_method=handoff_method,
        staging_subdirectory=(
            f"{version}/{platform_value.value}-{architecture.value}"
        ),
        checksum_asset=release.asset_named("SHA256SUMS"),
        manual_action_required=True,
    )


def _select_artifact_contract(
    release: AppRelease,
    platform_value: UpdatePlatform,
    architecture: CpuArchitecture,
) -> Optional[tuple[ReleaseAsset, UpdateArtifactKind, UpdateHandoffMethod]]:
    if platform_value is UpdatePlatform.MACOS and architecture is CpuArchitecture.ARM64:
        asset = release.asset_named("optees-macos-arm64.dmg")
        if asset is not None:
            return (
                asset,
                UpdateArtifactKind.MACOS_DMG,
                UpdateHandoffMethod.OPEN_DISK_IMAGE,
            )

    if platform_value is UpdatePlatform.WINDOWS and architecture is CpuArchitecture.X86_64:
        installer = release.asset_named("optees-windows-x64-setup.exe")
        if installer is not None:
            return (
                installer,
                UpdateArtifactKind.WINDOWS_INSTALLER,
                UpdateHandoffMethod.LAUNCH_INSTALLER,
            )
        portable = release.asset_named(
            "optees-windows-x64-portable.zip"
        ) or release.asset_named("optees-windows-x64.zip")
        if portable is not None:
            return (
                portable,
                UpdateArtifactKind.WINDOWS_PORTABLE_ZIP,
                UpdateHandoffMethod.OPEN_ARCHIVE,
            )

    if platform_value is UpdatePlatform.LINUX and architecture is CpuArchitecture.X86_64:
        asset = release.asset_named("optees-linux-x86_64.AppImage")
        if asset is not None:
            return (
                asset,
                UpdateArtifactKind.LINUX_APPIMAGE,
                UpdateHandoffMethod.OPEN_PORTABLE_PACKAGE,
            )
    return None


def _normalize_platform(value: str) -> Optional[UpdatePlatform]:
    normalized = (value or "").strip().lower()
    aliases = {
        "darwin": UpdatePlatform.MACOS,
        "macos": UpdatePlatform.MACOS,
        "windows": UpdatePlatform.WINDOWS,
        "linux": UpdatePlatform.LINUX,
    }
    return aliases.get(normalized)


def _normalize_architecture(value: str) -> Optional[CpuArchitecture]:
    normalized = (value or "").strip().lower()
    aliases = {
        "amd64": CpuArchitecture.X86_64,
        "x64": CpuArchitecture.X86_64,
        "x86_64": CpuArchitecture.X86_64,
        "aarch64": CpuArchitecture.ARM64,
        "arm64": CpuArchitecture.ARM64,
    }
    return aliases.get(normalized)


def is_newer_version(candidate: str, current: str) -> bool:
    return _version_tuple(candidate) > _version_tuple(current)


def _version_tuple(value: str) -> tuple[int, int, int]:
    text = (value or "").strip()
    if text.startswith(("v", "V")):
        text = text[1:]
    text = text.split("+", 1)[0].split("-", 1)[0]
    nums = [int(part) for part in re.findall(r"\d+", text)[:3]]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])  # type: ignore[return-value]
