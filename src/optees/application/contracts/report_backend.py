from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from optees.application.contracts.json_value import JsonValue, require_json_value


_ASSET_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
MAX_REPORT_BACKEND_INPUT_BYTES = 64 * 1024 * 1024
MAX_REPORT_BACKEND_OUTPUT_BYTES = 64 * 1024 * 1024


class ReportBackendUnavailableError(RuntimeError):
    """Raised when an optional local report backend cannot be executed."""


class ReportBackendCancelledError(RuntimeError):
    """Raised when report conversion is cancelled before publication."""


@dataclass(frozen=True)
class ReportBackendDiagnostic:
    backend_id: str
    available: bool
    engine: str
    reason: str | None = None
    pandoc_version: str | None = None
    engine_version: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        payload = require_json_value(
            {
                "backend_id": self.backend_id,
                "available": self.available,
                "engine": self.engine,
                "reason": self.reason,
                "pandoc_version": self.pandoc_version,
                "engine_version": self.engine_version,
            },
            path="$.report_backend_diagnostic",
        )
        assert isinstance(payload, dict)
        return payload


@dataclass(frozen=True)
class ReportBackendAsset:
    asset_id: str
    media_type: str
    suffix: str
    content: bytes

    def __post_init__(self) -> None:
        if _ASSET_ID.fullmatch(self.asset_id) is None:
            raise ValueError("report backend asset_id must be a bounded identifier")
        if not self.media_type.strip():
            raise ValueError("report backend asset media_type must not be empty")
        if self.suffix not in {".png", ".svg"}:
            raise ValueError("report backend assets support only PNG and SVG")
        if not self.content:
            raise ValueError("report backend asset content must not be empty")
        if len(self.content) > MAX_REPORT_BACKEND_INPUT_BYTES:
            raise ValueError("report backend asset exceeds the input size limit")
        if self.suffix == ".png" and (
            self.media_type != "image/png"
            or not self.content.startswith(b"\x89PNG\r\n\x1a\n")
        ):
            raise ValueError("report backend PNG asset is inconsistent")
        if self.suffix == ".svg":
            stripped = self.content.lstrip()
            if self.media_type != "image/svg+xml" or not (
                stripped.startswith(b"<svg")
                or (
                    stripped.startswith(b"<?xml")
                    and b"<svg" in stripped[:4096]
                )
            ):
                raise ValueError("report backend SVG asset is inconsistent")


@dataclass(frozen=True)
class ReportBackendRequest:
    markdown: bytes
    title: str
    locale: str
    assets: tuple[ReportBackendAsset, ...] = ()

    def __post_init__(self) -> None:
        if not self.markdown:
            raise ValueError("report backend Markdown must not be empty")
        if not self.title.strip():
            raise ValueError("report backend title must not be empty")
        if self.locale not in {"en", "it"}:
            raise ValueError("report backend locale must be 'en' or 'it'")
        asset_ids = [asset.asset_id for asset in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("report backend asset IDs must be unique")
        input_bytes = len(self.markdown) + sum(
            len(asset.content) for asset in self.assets
        )
        if input_bytes > MAX_REPORT_BACKEND_INPUT_BYTES:
            raise ValueError("report backend input exceeds the configured size limit")


@dataclass(frozen=True)
class RenderedReport:
    media_type: str
    content: bytes
    backend_id: str

    def __post_init__(self) -> None:
        if self.media_type != "application/pdf":
            raise ValueError("the PDF backend must return application/pdf")
        if not self.content.startswith(b"%PDF-"):
            raise ValueError("the PDF backend returned invalid PDF bytes")
        if len(self.content) > MAX_REPORT_BACKEND_OUTPUT_BYTES:
            raise ValueError("the PDF backend output exceeds the configured size limit")
        if not self.backend_id.strip():
            raise ValueError("report backend_id must not be empty")


ReportProgressCallback = Callable[[int, str], None]
ReportCancellation = Event
