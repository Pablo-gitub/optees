from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from optees.application.contracts.errors import StructuredError
from optees.application.contracts.json_value import JsonValue, require_json_value


MAX_REPORT_SECTIONS = 32
MAX_REPORT_BLOCKS = 64
MAX_REPORT_MARKDOWN_CHARS = 128 * 1024
MAX_REPORT_METADATA_ENTRIES = 20

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_RAW_HTML = re.compile(r"<\s*(?:!|/?[A-Za-z])[^>]*>")
_UNSAFE_TARGET = re.compile(
    r"\]\(\s*(?:https?://|file:|data:|javascript:)",
    re.IGNORECASE,
)
_MARKDOWN_TARGET = re.compile(r"!?\[[^\]]*\]\(\s*([^)]+)\)")
_REFERENCE_TARGET = re.compile(r"^\s*\[[^\]]+\]:\s*\S+", re.MULTILINE)


class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"


class ReportStatus(str, Enum):
    QUEUED = "queued"
    COMPOSING = "composing"
    AVAILABLE = "available"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True)
class MarkdownReportBlock:
    content: str
    type: str = field(default="markdown", init=False)

    def __post_init__(self) -> None:
        _validate_markdown(self.content)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"type": self.type, "content": self.content}


@dataclass(frozen=True)
class JobStatusReportBlock:
    job_id: str
    type: str = field(default="job_status", init=False)

    def __post_init__(self) -> None:
        _require_identifier(self.job_id, "job_id")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"type": self.type, "job_id": self.job_id}


@dataclass(frozen=True)
class ArtifactReportBlock:
    artifact_id: str
    caption: str | None = None
    views: tuple[str, ...] = ()
    type: str = field(default="artifact", init=False)

    def __post_init__(self) -> None:
        _require_identifier(self.artifact_id, "artifact_id")
        if self.caption is not None:
            _require_text(self.caption, "artifact caption", maximum=500)
        allowed_views = {"isometric", "front", "side", "top"}
        if len(self.views) > 4 or len(set(self.views)) != len(self.views):
            raise ValueError("artifact report views must contain at most four unique values")
        if any(view not in allowed_views for view in self.views):
            raise ValueError("artifact report views contain an unsupported camera")

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "type": self.type,
            "artifact_id": self.artifact_id,
            "caption": self.caption,
        }
        if self.views:
            payload["views"] = list(self.views)
        return payload


ReportBlock = MarkdownReportBlock | JobStatusReportBlock | ArtifactReportBlock


@dataclass(frozen=True)
class ReportSection:
    section_id: str
    heading: str
    blocks: tuple[ReportBlock, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.section_id, "section_id")
        _require_text(self.heading, "section heading", maximum=200)
        if not self.blocks:
            raise ValueError("report sections must contain at least one block")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "section_id": self.section_id,
            "heading": self.heading,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True)
class ReportRequest:
    title: str
    sections: tuple[ReportSection, ...]
    locale: str = "en"
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    format: ReportFormat = ReportFormat.MARKDOWN
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if self.contract_version != "1":
            raise ValueError("unsupported report contract version")
        if not isinstance(self.format, ReportFormat):
            raise ValueError("report format must use a ReportFormat value")
        if self.locale not in {"en", "it"}:
            raise ValueError("report locale must be 'en' or 'it'")
        _require_text(self.title, "report title", maximum=200)
        if not self.sections:
            raise ValueError("report requests must contain at least one section")
        if len(self.sections) > MAX_REPORT_SECTIONS:
            raise ValueError(
                f"report requests accept at most {MAX_REPORT_SECTIONS} sections"
            )
        section_ids = [section.section_id for section in self.sections]
        if len(set(section_ids)) != len(section_ids):
            raise ValueError("report section IDs must be unique")
        block_count = sum(len(section.blocks) for section in self.sections)
        if block_count > MAX_REPORT_BLOCKS:
            raise ValueError(
                f"report requests accept at most {MAX_REPORT_BLOCKS} blocks"
            )
        markdown_chars = sum(
            len(block.content)
            for section in self.sections
            for block in section.blocks
            if isinstance(block, MarkdownReportBlock)
        )
        if markdown_chars > MAX_REPORT_MARKDOWN_CHARS:
            raise ValueError(
                "report Markdown content exceeds the configured character limit"
            )
        if len(self.metadata) > MAX_REPORT_METADATA_ENTRIES:
            raise ValueError(
                f"report metadata accepts at most {MAX_REPORT_METADATA_ENTRIES} entries"
            )
        for key, value in self.metadata.items():
            _require_identifier(key, "metadata key")
            if isinstance(value, (dict, list)):
                raise ValueError("report metadata values must be JSON scalars")
        require_json_value(self.metadata, path="$.metadata")

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "format": self.format.value,
            "locale": self.locale,
            "title": self.title,
            "sections": [section.to_dict() for section in self.sections],
            "metadata": self.metadata,
        }
        normalized = require_json_value(payload, path="$.report_request")
        assert isinstance(normalized, dict)
        return normalized


@dataclass(frozen=True)
class ReportManifest:
    report_id: str
    title: str
    locale: str
    format: ReportFormat
    media_type: str
    status: ReportStatus
    created_at: str
    expires_at: str
    source_job_ids: tuple[str, ...] = ()
    source_artifact_ids: tuple[str, ...] = ()
    size_bytes: int | None = None
    sha256: str | None = None
    unsupported_block_count: int = 0
    progress_percent: int = 0
    progress_stage: str = "queued"
    backend_id: str | None = None
    error: StructuredError | None = None
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if self.contract_version != "1":
            raise ValueError("unsupported report contract version")
        _require_identifier(self.report_id, "report_id")
        _require_text(self.title, "report title", maximum=200)
        if self.locale not in {"en", "it"}:
            raise ValueError("report locale must be 'en' or 'it'")
        if not self.media_type.strip():
            raise ValueError("report media type must not be empty")
        if self.unsupported_block_count < 0:
            raise ValueError("unsupported_block_count must be non-negative")
        if (
            isinstance(self.progress_percent, bool)
            or not isinstance(self.progress_percent, int)
            or not 0 <= self.progress_percent <= 100
        ):
            raise ValueError("report progress_percent must be between 0 and 100")
        _require_identifier(self.progress_stage, "progress_stage")
        if self.backend_id is not None:
            _require_identifier(self.backend_id, "backend_id")
        if self.status is ReportStatus.AVAILABLE:
            if self.size_bytes is None or self.sha256 is None:
                raise ValueError("available reports require size_bytes and sha256")
        if self.status is ReportStatus.FAILED and self.error is None:
            raise ValueError("failed reports require a structured error")

    def to_dict(self) -> dict[str, JsonValue]:
        error_payload = None if self.error is None else self.error.to_dict()["error"]
        payload: dict[str, object] = {
            "contract_version": self.contract_version,
            "report_id": self.report_id,
            "title": self.title,
            "locale": self.locale,
            "format": self.format.value,
            "media_type": self.media_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "source_job_ids": list(self.source_job_ids),
            "source_artifact_ids": list(self.source_artifact_ids),
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "unsupported_block_count": self.unsupported_block_count,
            "progress_percent": self.progress_percent,
            "progress_stage": self.progress_stage,
            "backend_id": self.backend_id,
            "error": error_payload,
        }
        normalized = require_json_value(payload, path="$.report_manifest")
        assert isinstance(normalized, dict)
        return normalized


def _validate_markdown(content: str) -> None:
    _require_text(content, "Markdown content", maximum=MAX_REPORT_MARKDOWN_CHARS)
    if _RAW_HTML.search(content):
        raise ValueError("report Markdown must not contain raw HTML")
    if _UNSAFE_TARGET.search(content):
        raise ValueError("report Markdown must not contain external or unsafe targets")
    if _REFERENCE_TARGET.search(content):
        raise ValueError("report Markdown must not contain reference targets")
    for match in _MARKDOWN_TARGET.finditer(content):
        if not match.group(1).strip().startswith("#"):
            raise ValueError(
                "report Markdown must not contain filesystem or relative targets"
            )


def _require_identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded identifier")


def _require_text(value: str, name: str, *, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{name} must contain at most {maximum} characters")
