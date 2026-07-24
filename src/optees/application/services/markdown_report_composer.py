from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.report import (
    ArtifactReportBlock,
    JobStatusReportBlock,
    MarkdownReportBlock,
)
from optees.application.contracts.report_composition import (
    ComposedReport,
    ReportCompositionContext,
    ResolvedReportArtifact,
)
from optees.application.contracts.report_backend import ReportBackendAsset


class MarkdownReportComposer:
    """Compose a deterministic, tool-free Markdown report."""

    def compose(self, context: ReportCompositionContext) -> ComposedReport:
        request = context.request
        labels = _LABELS[request.locale]
        lines = [f"# {request.title}", ""]
        if request.metadata:
            lines.extend((f"## {labels['metadata']}", ""))
            for key in sorted(request.metadata):
                lines.append(f"- **{_escape(key)}:** {_scalar(request.metadata[key])}")
            lines.append("")

        unsupported = 0
        report_assets: list[ReportBackendAsset] = []
        for section in request.sections:
            lines.extend((f"## {section.heading}", ""))
            for block in section.blocks:
                if isinstance(block, MarkdownReportBlock):
                    lines.extend((block.content.rstrip(), ""))
                elif isinstance(block, JobStatusReportBlock):
                    envelope = context.jobs.get(block.job_id)
                    if envelope is None:
                        unsupported += 1
                        lines.extend(
                            _unsupported(
                                labels,
                                "job_status",
                                block.job_id,
                                context.unavailable_jobs.get(
                                    block.job_id,
                                    labels["not_available"],
                                ),
                            )
                        )
                    else:
                        lines.extend(_job_status(labels, envelope.to_dict()))
                elif isinstance(block, ArtifactReportBlock):
                    artifact = context.artifacts[block.artifact_id]
                    rendered = _artifact(labels, artifact, block.caption)
                    if rendered[1]:
                        unsupported += 1
                    lines.extend(rendered[0])
                    report_assets.extend(rendered[2])

        lines.extend(
            (
                "---",
                "",
                (
                    f"{labels['generated_by']} "
                    f"[Optees · optees.it](https://optees.it) "
                    f"(`{context.optees_version}`)"
                ),
                "",
            )
        )
        content = "\n".join(lines).encode("utf-8")
        return ComposedReport(
            content=content,
            media_type="text/markdown; charset=utf-8",
            source_job_ids=tuple(
                sorted(set(context.jobs) | set(context.unavailable_jobs))
            ),
            source_artifact_ids=tuple(sorted(context.artifacts)),
            unsupported_block_count=unsupported,
            assets=tuple(report_assets),
        )


def _job_status(labels: dict[str, str], payload: dict[str, object]) -> list[str]:
    validation = payload.get("validation")
    validation_status = (
        validation.get("status")
        if isinstance(validation, Mapping)
        else labels["not_available"]
    )
    lines = [f"### {labels['solver_status']}", ""]
    fields = (
        ("job_id", labels["job"]),
        ("capability_id", labels["capability"]),
        ("job_status", labels["lifecycle"]),
        ("mathematical_status", labels["mathematical"]),
        ("termination_reason", labels["termination"]),
    )
    for key, label in fields:
        lines.append(f"- **{label}:** {_scalar(payload.get(key))}")
    lines.append(f"- **{labels['validation']}:** {_scalar(validation_status)}")
    warnings = payload.get("warnings")
    if isinstance(warnings, Sequence) and warnings:
        lines.append(
            f"- **{labels['warnings']}:** "
            + "; ".join(_escape(str(item)) for item in warnings)
        )
    result = payload.get("result")
    if isinstance(result, Mapping):
        objective = next(
            (
                result[key]
                for key in ("objective_value", "objective", "total_value")
                if key in result
            ),
            None,
        )
        if objective is not None:
            lines.append(f"- **{labels['objective']}:** {_scalar(objective)}")
    lines.append("")
    return lines


def _artifact(
    labels: dict[str, str],
    resolved: ResolvedReportArtifact,
    caption: str | None,
) -> tuple[list[str], bool, tuple[ReportBackendAsset, ...]]:
    manifest = resolved.manifest
    if manifest is None or resolved.content is None:
        return (
            _unsupported(
                labels,
                "artifact",
                resolved.artifact_id,
                resolved.unavailable_reason or labels["not_available"],
            ),
            True,
            (),
        )
    title = caption or manifest.artifact_type
    lines = [f"### {_escape(title)}", ""]
    assets: tuple[ReportBackendAsset, ...] = ()
    if manifest.format is ArtifactFormat.MARKDOWN:
        lines.extend((resolved.content.decode("utf-8", errors="replace").rstrip(), ""))
    elif manifest.format is ArtifactFormat.CSV:
        rows = list(csv.reader(io.StringIO(resolved.content.decode("utf-8"))))
        lines.extend(_markdown_table(rows))
    elif manifest.format in {ArtifactFormat.JSON, ArtifactFormat.DATA_JSON}:
        try:
            payload = json.loads(resolved.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return (
                _unsupported(
                    labels,
                    "artifact",
                    resolved.artifact_id,
                    labels["invalid_content"],
                ),
                True,
                (),
            )
        table = _json_table(payload)
        if table is None:
            lines.extend(
                (
                    "```json",
                    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                    "```",
                    "",
                )
            )
        else:
            lines.extend(_markdown_table(table))
    elif manifest.format in {ArtifactFormat.PNG, ArtifactFormat.SVG}:
        suffix = ".png" if manifest.format is ArtifactFormat.PNG else ".svg"
        lines.extend(
            (
                f"![{_escape(title)}](optees-artifact://{manifest.artifact_id})",
                "",
            )
        )
        assets = (
            ReportBackendAsset(
                manifest.artifact_id,
                manifest.media_type,
                suffix,
                resolved.content,
            ),
        )
    elif resolved.conversion is not None:
        conversion = resolved.conversion
        if conversion.markdown is not None:
            lines.extend((conversion.markdown.rstrip(), ""))
        elif conversion.assets:
            for asset in conversion.assets:
                label = asset.asset_id.rsplit("-", 1)[-1].replace("_", " ")
                lines.extend(
                    (
                        f"![{_escape(title)} - {_escape(label)}]"
                        f"(optees-report-asset://{asset.asset_id})",
                        "",
                    )
                )
        else:
            return (
                _unsupported(
                    labels,
                    "artifact",
                    resolved.artifact_id,
                    conversion.unavailable_reason or labels["not_available"],
                ),
                True,
                (),
            )
        assets = conversion.assets
    else:
        return (
            _unsupported(
                labels,
                "artifact",
                resolved.artifact_id,
                labels["format_not_embeddable"].format(format=manifest.format.value),
            ),
            True,
            (),
        )
    lines.extend(
        (
            f"- **{labels['artifact_id']}:** `{manifest.artifact_id}`",
            f"- **{labels['media_type']}:** `{manifest.media_type}`",
            f"- **SHA-256:** `{manifest.sha256}`",
            "",
        )
    )
    return lines, False, assets


def _json_table(payload: object) -> list[list[object]] | None:
    if isinstance(payload, Mapping):
        columns = payload.get("columns")
        rows = payload.get("rows")
        if (
            isinstance(columns, Sequence)
            and not isinstance(columns, (str, bytes))
            and isinstance(rows, Sequence)
            and not isinstance(rows, (str, bytes))
        ):
            return [
                list(columns),
                *(
                    list(row)
                    for row in rows
                    if isinstance(row, Sequence)
                    and not isinstance(row, (str, bytes))
                ),
            ]
    if isinstance(payload, Sequence) and payload and all(
        isinstance(row, Mapping) for row in payload
    ):
        keys = sorted({str(key) for row in payload for key in row})
        return [keys, *[[row.get(key) for key in keys] for row in payload]]
    return None


def _markdown_table(rows: Sequence[Sequence[object]]) -> list[str]:
    if not rows:
        return []
    width = max(len(row) for row in rows)
    normalized = [
        [_escape(str(row[index])) if index < len(row) else "" for index in range(width)]
        for row in rows[:501]
    ]
    lines = [
        "| " + " | ".join(normalized[0]) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    lines.append("")
    return lines


def _unsupported(
    labels: dict[str, str],
    type_: str,
    identifier: str,
    reason: str,
) -> list[str]:
    return [
        f"> **`unsupported_artifact` · {labels['unsupported']}**",
        ">",
        f"> {labels['block_type']}: `{type_}`  ",
        f"> ID: `{identifier}`  ",
        f"> {labels['reason']}: {_escape(reason)}",
        "",
    ]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _scalar(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    return _escape(str(value))


_LABELS = {
    "en": {
        "metadata": "Report metadata",
        "solver_status": "Solver status",
        "job": "Job",
        "capability": "Capability",
        "lifecycle": "Lifecycle status",
        "mathematical": "Mathematical status",
        "termination": "Termination reason",
        "validation": "Independent validation",
        "warnings": "Warnings",
        "objective": "Objective",
        "unsupported": "Unsupported or unavailable report block",
        "block_type": "Block type",
        "reason": "Reason",
        "not_available": "The referenced source is not available.",
        "invalid_content": "The artifact content is not valid JSON.",
        "format_not_embeddable": "Format '{format}' is not embeddable in Markdown.",
        "artifact_id": "Artifact ID",
        "media_type": "Media type",
        "generated_by": "Generated by",
    },
    "it": {
        "metadata": "Metadati del report",
        "solver_status": "Stato del solver",
        "job": "Job",
        "capability": "Capability",
        "lifecycle": "Stato del ciclo di vita",
        "mathematical": "Stato matematico",
        "termination": "Motivo di terminazione",
        "validation": "Validazione indipendente",
        "warnings": "Avvisi",
        "objective": "Obiettivo",
        "unsupported": "Blocco report non supportato o non disponibile",
        "block_type": "Tipo di blocco",
        "reason": "Motivo",
        "not_available": "La sorgente richiesta non e' disponibile.",
        "invalid_content": "Il contenuto dell'artifact non e' JSON valido.",
        "format_not_embeddable": "Il formato '{format}' non e' incorporabile in Markdown.",
        "artifact_id": "ID artifact",
        "media_type": "Media type",
        "generated_by": "Generato da",
    },
}
