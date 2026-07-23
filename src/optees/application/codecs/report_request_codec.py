from __future__ import annotations

from collections.abc import Mapping, Sequence

from optees.application.contracts.json_value import require_json_value
from optees.application.contracts.report import (
    ArtifactReportBlock,
    JobStatusReportBlock,
    MarkdownReportBlock,
    ReportFormat,
    ReportRequest,
    ReportSection,
)


def report_request_from_dict(payload: Mapping[str, object]) -> ReportRequest:
    _reject_extra(
        payload,
        {"contract_version", "format", "locale", "title", "sections", "metadata"},
        "$",
    )
    sections_value = payload.get("sections")
    if not isinstance(sections_value, Sequence) or isinstance(
        sections_value, (str, bytes)
    ):
        raise ValueError("$.sections must be an array")
    metadata_value = payload.get("metadata", {})
    if not isinstance(metadata_value, Mapping):
        raise ValueError("$.metadata must be an object")
    metadata = require_json_value(dict(metadata_value), path="$.metadata")
    assert isinstance(metadata, dict)
    try:
        format_ = ReportFormat(str(payload.get("format", "markdown")))
    except ValueError as exc:
        raise ValueError("$.format must be 'markdown'") from exc
    return ReportRequest(
        contract_version=_string(payload, "contract_version", default="1"),
        format=format_,
        locale=_string(payload, "locale", default="en"),
        title=_string(payload, "title"),
        sections=tuple(
            _section(value, index)
            for index, value in enumerate(sections_value)
        ),
        metadata=metadata,
    )


def _section(value: object, index: int) -> ReportSection:
    path = f"$.sections[{index}]"
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    _reject_extra(value, {"section_id", "heading", "blocks"}, path)
    blocks_value = value.get("blocks")
    if not isinstance(blocks_value, Sequence) or isinstance(
        blocks_value, (str, bytes)
    ):
        raise ValueError(f"{path}.blocks must be an array")
    return ReportSection(
        section_id=_string(value, "section_id", path=path),
        heading=_string(value, "heading", path=path),
        blocks=tuple(
            _block(block, f"{path}.blocks[{block_index}]")
            for block_index, block in enumerate(blocks_value)
        ),
    )


def _block(value: object, path: str):
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    type_ = _string(value, "type", path=path)
    if type_ == "markdown":
        _reject_extra(value, {"type", "content"}, path)
        return MarkdownReportBlock(_string(value, "content", path=path))
    if type_ == "job_status":
        _reject_extra(value, {"type", "job_id"}, path)
        return JobStatusReportBlock(_string(value, "job_id", path=path))
    if type_ == "artifact":
        _reject_extra(value, {"type", "artifact_id", "caption"}, path)
        caption = value.get("caption")
        if caption is not None and not isinstance(caption, str):
            raise ValueError(f"{path}.caption must be a string or null")
        return ArtifactReportBlock(
            _string(value, "artifact_id", path=path),
            caption=caption,
        )
    raise ValueError(f"{path}.type is not a supported report block type")


def _string(
    payload: Mapping[str, object],
    key: str,
    *,
    path: str = "$",
    default: str | None = None,
) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"{path}.{key} must be a string")
    return value


def _reject_extra(
    payload: Mapping[str, object],
    allowed: set[str],
    path: str,
) -> None:
    extras = sorted(str(key) for key in payload if key not in allowed)
    if extras:
        raise ValueError(f"{path} contains unsupported fields: {', '.join(extras)}")
