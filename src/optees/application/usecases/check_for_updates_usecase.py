from __future__ import annotations

import platform
from typing import Optional

from optees.application.ports.update_provider_port import UpdateProviderPort
from optees.core.release_version import release_version_key
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

    Release tags use `vMAJOR.MINOR.PATCH` or `vMAJOR.MINOR.PATCH-rc.N`.
    Comparison is strict and deterministic, including release-candidate order;
    a stable release follows every candidate with the same numeric base.
    """

    def __init__(
        self,
        provider: UpdateProviderPort,
        *,
        current_version: str,
        system_name: Optional[str] = None,
        machine: Optional[str] = None,
        linux_distribution: Optional[str] = None,
    ) -> None:
        self._provider = provider
        self._current_version = current_version
        self._system_name = system_name
        self._machine = machine
        self._linux_distribution = linux_distribution

    def execute(self) -> UpdateCheckResult:
        release = self._provider.get_latest_release()
        latest = release.version or release.tag_name
        system_name = self._system_name or platform.system()
        plan = build_update_plan(
            release,
            system_name=system_name,
            machine=self._machine or platform.machine(),
            linux_distribution=(
                self._linux_distribution
                if self._linux_distribution is not None
                else _detect_linux_distribution(system_name)
            ),
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
    linux_distribution: Optional[str] = None,
) -> Optional[ReleaseAsset]:
    plan = build_update_plan(
        release,
        system_name=system_name,
        machine=machine,
        linux_distribution=linux_distribution,
    )
    return plan.artifact if plan is not None else None


def build_update_plan(
    release: AppRelease,
    *,
    system_name: str,
    machine: str,
    linux_distribution: Optional[str] = None,
) -> Optional[UpdatePlan]:
    platform_value = _normalize_platform(system_name)
    architecture = _normalize_architecture(machine)
    if platform_value is None or architecture is None:
        return None

    selection = _select_artifact_contract(
        release,
        platform_value,
        architecture,
        linux_distribution=linux_distribution,
    )
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
    *,
    linux_distribution: Optional[str] = None,
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
        if _is_debian_family(linux_distribution):
            installer = release.asset_named("optees-linux-x86_64.deb")
            if installer is not None:
                return (
                    installer,
                    UpdateArtifactKind.LINUX_DEB,
                    UpdateHandoffMethod.LAUNCH_INSTALLER,
                )
        asset = release.asset_named("optees-linux-x86_64.AppImage")
        if asset is not None:
            return (
                asset,
                UpdateArtifactKind.LINUX_APPIMAGE,
                UpdateHandoffMethod.OPEN_PORTABLE_PACKAGE,
            )
    return None


def _detect_linux_distribution(system_name: str) -> Optional[str]:
    if system_name.strip().lower() != "linux":
        return None
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        return None
    detected = " ".join(
        value.strip().lower()
        for value in (release.get("ID", ""), release.get("ID_LIKE", ""))
        if value.strip()
    )
    return detected or None


def _is_debian_family(linux_distribution: Optional[str]) -> bool:
    if not linux_distribution:
        return False
    tokens = {
        token.strip().lower()
        for token in linux_distribution.replace(",", " ").split()
        if token.strip()
    }
    return bool(tokens & {"debian", "ubuntu"})


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
    return release_version_key(candidate) > release_version_key(current)
