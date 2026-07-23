from __future__ import annotations

from dataclasses import dataclass, field

from optees.application.contracts.json_value import JsonValue, require_json_value


TableCell = str | int | float | bool | None


@dataclass(frozen=True)
class ArtifactTableColumn:
    """Stable machine key and human-readable label for one artifact column."""

    key: str
    title: str

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.title.strip():
            raise ValueError("artifact table column key and title must not be empty")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"key": self.key, "title": self.title}


@dataclass(frozen=True)
class ArtifactTable:
    """Transport-neutral tabular projection of a solver result."""

    artifact_type: str
    title: str
    columns: tuple[ArtifactTableColumn, ...]
    rows: tuple[dict[str, TableCell], ...]
    summary: dict[str, JsonValue] = field(default_factory=dict)
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if self.contract_version != "1":
            raise ValueError("unsupported artifact table contract version")
        if not self.artifact_type.strip() or not self.title.strip():
            raise ValueError("artifact table identifiers must not be empty")
        if not self.columns:
            raise ValueError("artifact table must contain at least one column")
        keys = tuple(column.key for column in self.columns)
        if len(set(keys)) != len(keys):
            raise ValueError("artifact table column keys must be unique")
        expected = set(keys)
        for index, row in enumerate(self.rows):
            if set(row) != expected:
                raise ValueError(
                    f"artifact table row {index} must match the declared columns"
                )
            require_json_value(row, path=f"$.rows[{index}]")
        require_json_value(self.summary, path="$.summary")

    def to_dict(self) -> dict[str, JsonValue]:
        payload = require_json_value(
            {
                "contract_version": self.contract_version,
                "artifact_type": self.artifact_type,
                "title": self.title,
                "columns": [column.to_dict() for column in self.columns],
                "rows": list(self.rows),
                "summary": self.summary,
            },
            path="$.artifact_table",
        )
        assert isinstance(payload, dict)
        return payload
