from __future__ import annotations

import platform
import re
from typing import Optional

from optees.application.ports.update_provider_port import UpdateProviderPort
from optees.domain.entities.update import AppRelease, ReleaseAsset, UpdateCheckResult


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
        asset = select_platform_asset(
            release,
            system_name=self._system_name or platform.system(),
            machine=self._machine or platform.machine(),
        )
        available = is_newer_version(latest, self._current_version)

        if available and asset is None:
            return UpdateCheckResult(
                current_version=self._current_version,
                latest_version=latest,
                update_available=False,
                release=release,
                message="A newer release exists, but no compatible installer asset was found.",
            )

        return UpdateCheckResult(
            current_version=self._current_version,
            latest_version=latest,
            update_available=available,
            release=release,
            asset=asset if available else None,
        )


def select_platform_asset(
    release: AppRelease,
    *,
    system_name: str,
    machine: str,
) -> Optional[ReleaseAsset]:
    system = (system_name or "").lower()
    arch = (machine or "").lower()

    if system == "darwin":
        if arch in {"arm64", "aarch64"}:
            return release.asset_named("optees-macos-arm64.dmg")
        return None
    if system == "windows":
        return release.asset_named("optees-windows-x64.zip")
    if system == "linux":
        return release.asset_named("optees-linux-x86_64.AppImage")
    return None


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
