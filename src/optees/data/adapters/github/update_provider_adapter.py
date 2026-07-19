from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from optees.application.ports.update_provider_port import UpdateProviderPort
from optees.domain.entities.update import AppRelease, ReleaseAsset


class GitHubUpdateProvider(UpdateProviderPort):
    """GitHub Releases adapter for Optees updates."""

    DEFAULT_MAX_ASSET_BYTES = 512 * 1024 * 1024
    MAX_CHECKSUM_BYTES = 1024 * 1024

    def __init__(
        self,
        *,
        repository: str = "Pablo-gitub/optees",
        timeout_seconds: float = 8.0,
        max_asset_bytes: int = DEFAULT_MAX_ASSET_BYTES,
    ) -> None:
        self._repository = repository
        self._timeout_seconds = float(timeout_seconds)
        self._max_asset_bytes = int(max_asset_bytes)
        if self._max_asset_bytes <= 0:
            raise ValueError("max_asset_bytes must be positive.")

    def get_latest_release(self) -> AppRelease:
        url = f"https://api.github.com/repos/{self._repository}/releases/latest"
        data = self._read_json(url)
        return release_from_github_json(data)

    def download_asset(
        self,
        asset: ReleaseAsset,
        destination_dir: Path,
        *,
        checksum_asset: Optional[ReleaseAsset] = None,
    ) -> Path:
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        _validate_asset_name(asset.name)
        if asset.size is not None and asset.size > self._max_asset_bytes:
            raise ValueError(
                f"Update asset exceeds the {self._max_asset_bytes}-byte download limit."
            )

        target = destination_dir / asset.name
        temp = target.with_suffix(target.suffix + ".part")
        temp.unlink(missing_ok=True)

        downloaded = 0
        try:
            with self._open(asset.download_url) as response:
                with temp.open("wb") as fh:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > self._max_asset_bytes:
                            raise ValueError("Update download exceeded its maximum size.")
                        fh.write(chunk)

            if asset.size is not None and downloaded != asset.size:
                raise ValueError(
                    f"Update size mismatch for {asset.name}: "
                    f"expected {asset.size}, got {downloaded}."
                )

            if checksum_asset is not None:
                expected = self._expected_sha256(checksum_asset, asset.name)
                if expected is None:
                    raise ValueError(
                        f"SHA256SUMS has no entry for update asset {asset.name}."
                    )
                actual = _sha256_file(temp)
                if actual.lower() != expected.lower():
                    raise ValueError(
                        f"Checksum mismatch for {asset.name}: expected {expected}, got {actual}"
                    )

            temp.replace(target)
        except Exception:
            temp.unlink(missing_ok=True)
            raise

        if target.suffix == ".AppImage":
            current_mode = target.stat().st_mode
            target.chmod(current_mode | 0o111)
        return target

    def _expected_sha256(self, checksum_asset: ReleaseAsset, target_name: str) -> Optional[str]:
        with self._open(checksum_asset.download_url) as response:
            payload = response.read(self.MAX_CHECKSUM_BYTES + 1)
        if len(payload) > self.MAX_CHECKSUM_BYTES:
            raise ValueError("SHA256SUMS exceeds the maximum supported size.")
        text = payload.decode("utf-8", errors="replace")
        return parse_sha256sums(text).get(target_name)

    def _read_json(self, url: str) -> dict[str, Any]:
        with self._open(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def _open(self, url: str):
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "optees-update-checker",
            },
        )
        try:
            return urlopen(request, timeout=self._timeout_seconds)
        except HTTPError as exc:
            raise RuntimeError(f"GitHub release request failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub release request failed: {exc.reason}") from exc


def release_from_github_json(data: dict[str, Any]) -> AppRelease:
    assets = tuple(
        ReleaseAsset(
            name=str(item.get("name", "")),
            download_url=str(item.get("browser_download_url", "")),
            size=_optional_int(item.get("size")),
        )
        for item in data.get("assets", [])
        if item.get("name") and item.get("browser_download_url")
    )
    tag = str(data.get("tag_name") or "")
    return AppRelease(
        tag_name=tag,
        version=tag[1:] if tag.startswith(("v", "V")) else tag,
        html_url=str(data.get("html_url") or ""),
        body=str(data.get("body") or ""),
        prerelease=bool(data.get("prerelease", False)),
        assets=assets,
    )


def parse_sha256sums(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        digest = parts[0]
        name = os.path.basename(parts[-1].lstrip("*"))
        if len(digest) == 64:
            checksums[name] = digest
    return checksums


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 256)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _validate_asset_name(name: str) -> None:
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError("Update asset name is not a safe filename.")
    if "/" in name or "\\" in name:
        raise ValueError("Update asset name is not a safe filename.")


def _optional_int(value: object) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
