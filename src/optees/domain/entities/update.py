from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: Optional[str]
    update_available: bool
    release: Optional[AppRelease] = None
    asset: Optional[ReleaseAsset] = None
    message: str = ""

    @staticmethod
    def unavailable(current_version: str, message: str = "") -> "UpdateCheckResult":
        return UpdateCheckResult(
            current_version=current_version,
            latest_version=None,
            update_available=False,
            message=message,
        )
