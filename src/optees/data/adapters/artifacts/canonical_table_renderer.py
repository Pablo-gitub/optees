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
    """Render one stable semantic table as deterministic JSON or RFC 4180 CSV."""

    renderer_version = "canonical-table-1"

    def __init__(self, builder: TableBuilder) -> None:
        self._builder = builder

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        table = self._builder(context)
        if context.format is ArtifactFormat.JSON:
            content = (dumps_json(table.to_dict(), indent=2) + "\n").encode("utf-8")
            return RenderedArtifact("application/json", content)
        if context.format is ArtifactFormat.CSV:
            return RenderedArtifact("text/csv; charset=utf-8", _csv_bytes(table))
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
