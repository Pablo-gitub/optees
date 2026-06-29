from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol

from optees.domain.entities.update import AppRelease, ReleaseAsset


class UpdateProviderPort(Protocol):
    """Abstraction over the remote release provider."""

    def get_latest_release(self) -> AppRelease:
        """Return the latest non-draft release known by the provider."""
        ...

    def download_asset(
        self,
        asset: ReleaseAsset,
        destination_dir: Path,
        *,
        checksum_asset: Optional[ReleaseAsset] = None,
    ) -> Path:
        """Download an update asset and optionally verify it with a checksum file."""
        ...
