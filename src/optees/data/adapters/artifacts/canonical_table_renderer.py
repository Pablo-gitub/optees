from __future__ import annotations

import csv
import io

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)
from optees.application.contracts.artifact_table import ArtifactTable, TableCell
from optees.application.contracts.json_value import dumps_json
from optees.application.services.canonical_artifact_tables import TableBuilder


class CanonicalTableRenderer:
    """Render a stable semantic table without GUI or external document tools."""

    renderer_version = "canonical-table-2"

    def __init__(self, builder: TableBuilder) -> None:
        self._builder = builder

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        table = self._builder(context)
        if context.format is ArtifactFormat.JSON:
            content = (dumps_json(table.to_dict(), indent=2) + "\n").encode("utf-8")
            return RenderedArtifact("application/json", content)
        if context.format is ArtifactFormat.CSV:
            return RenderedArtifact("text/csv; charset=utf-8", _csv_bytes(table))
        if context.format is ArtifactFormat.MARKDOWN:
            return RenderedArtifact(
                "text/markdown; charset=utf-8",
                _markdown_bytes(table, context),
            )
        raise ValueError("canonical table renderer received an unsupported format")


def _csv_bytes(table: ArtifactTable) -> bytes:
    stream = io.StringIO(newline="")
    keys = [column.key for column in table.columns]
    writer = csv.DictWriter(
        stream,
        fieldnames=keys,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in table.rows:
        writer.writerow({key: _csv_cell(row[key]) for key in keys})
    return stream.getvalue().encode("utf-8")


def _csv_cell(value: TableCell) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _markdown_bytes(
    table: ArtifactTable,
    context: ArtifactRenderContext,
) -> bytes:
    extra = context.options.extra or {}
    max_rows = extra.get("max_rows", 100)
    if isinstance(max_rows, bool) or not isinstance(max_rows, int):
        raise ValueError("max_rows must be an integer")
    visible_rows = table.rows[:max_rows]
    total_rows = len(table.rows)
    truncated = len(visible_rows) < total_rows
    metadata = dumps_json(
        {
            "artifact_table_contract_version": table.contract_version,
            "total_rows": total_rows,
            "displayed_rows": len(visible_rows),
            "truncated": truncated,
        }
    )
    lines = [
        f"# {table.title}",
        "",
        "| " + " | ".join(_markdown_cell(column.title) for column in table.columns) + " |",
        "| " + " | ".join("---" for _column in table.columns) + " |",
    ]
    for row in visible_rows:
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(row[column.key]) for column in table.columns
            )
            + " |"
        )
    lines.extend(["", f"<!-- optees-table-metadata: {metadata} -->"])
    if truncated:
        if context.options.locale == "it":
            lines.append(
                f"_Mostrate {len(visible_rows)} righe su {total_rows}; "
                "tabella troncata._"
            )
        else:
            lines.append(
                f"_Showing {len(visible_rows)} of {total_rows} rows; "
                "table truncated._"
            )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _markdown_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
