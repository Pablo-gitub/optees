from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Protocol

from optees.domain.entities.update import AppRelease, ReleaseAsset

DownloadProgressCallback = Callable[[int, Optional[int]], None]


class UpdateDownloadError(RuntimeError):
    """A release asset could not be downloaded safely."""


class UpdateVerificationError(UpdateDownloadError):
    """A downloaded release asset failed integrity verification."""


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
        progress: Optional[DownloadProgressCallback] = None,
    ) -> Path:
        """Download an update asset and optionally verify it with a checksum file."""
        ...
