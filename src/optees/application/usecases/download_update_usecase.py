from __future__ import annotations

from pathlib import Path

from optees.application.ports.update_provider_port import (
    DownloadProgressCallback,
    UpdateProviderPort,
)
from optees.domain.entities.update import UpdateCheckResult


class DownloadUpdateUseCase:
    """Download the installer selected by an update check result."""

    def __init__(self, provider: UpdateProviderPort) -> None:
        self._provider = provider

    def execute(
        self,
        result: UpdateCheckResult,
        destination_dir: Path,
        *,
        progress: DownloadProgressCallback | None = None,
    ) -> Path:
        if not result.update_available or result.asset is None:
            raise ValueError("No compatible update asset is available.")

        checksum_asset = result.plan.checksum_asset if result.plan is not None else None
        if checksum_asset is None and result.release is not None:
            checksum_asset = result.release.asset_named("SHA256SUMS")

        return self._provider.download_asset(
            result.asset,
            destination_dir,
            checksum_asset=checksum_asset,
            progress=progress,
        )
