from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from optees.application.contracts.artifact import (
    ArtifactFormat,
    AvailableArtifact,
)
from optees.application.contracts.artifact_rendering import ArtifactRenderContext
from optees.application.contracts.artifact_table import (
    ArtifactTable,
    ArtifactTableColumn,
    TableCell,
)
from optees.application.contracts.execution import MathematicalStatus
from optees.application.contracts.json_value import JsonValue


TableBuilder = Callable[[ArtifactRenderContext], ArtifactTable]

_SOLVED = (MathematicalStatus.OPTIMAL, MathematicalStatus.FEASIBLE)


@dataclass(frozen=True)
class CanonicalTableDefinition:
    capability_id: str
    artifact_type: str
    title: str
    builder: TableBuilder
    statuses: tuple[MathematicalStatus, ...] = _SOLVED

    def descriptor(self) -> AvailableArtifact:
        return AvailableArtifact(
            artifact_type=self.artifact_type,
            title=self.title,
            formats=(
                ArtifactFormat.JSON,
                ArtifactFormat.CSV,
                ArtifactFormat.MARKDOWN,
            ),
            required_mathematical_statuses=self.statuses,
            options_schema={
                "type": "object",
                "properties": {
                    "locale": {"enum": ["en", "it"]},
                    "max_rows": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                },
                "additionalProperties": False,
            },
        )


def canonical_table_definition(
    capability_id: str,
) -> CanonicalTableDefinition | None:
    definitions = canonical_table_definitions_for(capability_id)
    return definitions[0] if definitions else None


def canonical_table_definitions_for(
    capability_id: str,
) -> tuple[CanonicalTableDefinition, ...]:
    return _DEFINITIONS_BY_CAPABILITY.get(capability_id, ())


def canonical_table_definitions() -> tuple[CanonicalTableDefinition, ...]:
    return _DEFINITIONS


def _variables(context: ArtifactRenderContext) -> ArtifactTable:
    return _table_from_object_rows(
        context,
        columns=(("name", "Variable"), ("value", "Value")),
        rows=_object_rows(context.envelope.result.get("variables")),
        summary=_objective_summary(context),
    )


def _selection(context: ArtifactRenderContext) -> ArtifactTable:
    selected = _object_rows(context.envelope.result.get("selected_items"))
    keys = _union_keys(selected)
    preferred = tuple(
        key for key in ("index", "name", "quantity", "fraction") if key in keys
    )
    if not preferred:
        preferred = ("index", "name")
    return _table_from_object_rows(
        context,
        columns=tuple((key, _title(key)) for key in preferred),
        rows=selected,
        summary={
            **_objective_summary(context),
            "total_value": context.envelope.result.get("total_value"),
            "total_weight": context.envelope.result.get("total_weight"),
            "remaining_capacity": context.envelope.result.get(
                "remaining_capacity"
            ),
        },
    )


def _path(context: ArtifactRenderContext) -> ArtifactTable:
    raw_path = context.envelope.result.get("path")
    path = raw_path if isinstance(raw_path, list) else []
    rows = tuple({"step": index, "node": _scalar(node)} for index, node in enumerate(path))
    return _table(
        context,
        columns=(("step", "Step"), ("node", "Node")),
        rows=rows,
        summary={
            "distance": context.envelope.result.get("distance"),
            "hop_count": context.envelope.result.get("hop_count"),
        },
    )


def _settled_trace(context: ArtifactRenderContext) -> ArtifactTable:
    raw_order = context.envelope.diagnostics.get("settled_order")
    order = raw_order if isinstance(raw_order, list) else []
    raw_distances = context.envelope.diagnostics.get("settled_distances")
    distances = raw_distances if isinstance(raw_distances, dict) else {}
    rows = tuple(
        {
            "step": index,
            "node": _scalar(node),
            "distance": _scalar(distances.get(str(node))),
        }
        for index, node in enumerate(order)
    )
    return _table(
        context,
        columns=(
            ("step", "Step"),
            ("node", "Settled node"),
            ("distance", "Final distance"),
        ),
        rows=rows,
        summary={
            "settled_count": context.envelope.diagnostics.get("settled_count"),
            "destination_distance": context.envelope.result.get("distance"),
        },
    )


def _coefficients(context: ArtifactRenderContext) -> ArtifactTable:
    rows: list[dict[str, TableCell]] = [
        {
            "term": "intercept",
            "feature": None,
            "value": _scalar(context.envelope.result.get("intercept")),
        }
    ]
    for raw in _object_rows(context.envelope.result.get("coefficients")):
        rows.append(
            {
                "term": "coefficient",
                "feature": _scalar(raw.get("feature")),
                "value": _scalar(raw.get("value")),
            }
        )
    return _table(
        context,
        columns=(
            ("term", "Term"),
            ("feature", "Feature"),
            ("value", "Value"),
        ),
        rows=tuple(rows),
        summary={
            "trained_model": context.envelope.result.get("trained_model"),
            "train_metrics": context.envelope.result.get("train_metrics"),
            "test_metrics": context.envelope.result.get("test_metrics"),
        },
    )


def _regression_metrics(context: ArtifactRenderContext) -> ArtifactTable:
    return _partitioned_metrics(
        context,
        keys=("mae", "mse", "rmse", "r_squared"),
    )


def _classification_metrics(context: ArtifactRenderContext) -> ArtifactTable:
    return _partitioned_metrics(
        context,
        keys=("accuracy", "precision", "recall", "f1"),
    )


def _partitioned_metrics(
    context: ArtifactRenderContext,
    *,
    keys: tuple[str, ...],
) -> ArtifactTable:
    rows: list[dict[str, TableCell]] = []
    for partition in ("train", "test"):
        raw_metrics = context.envelope.result.get(f"{partition}_metrics")
        metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
        rows.append(
            {
                "partition": partition,
                **{key: _scalar(metrics.get(key)) for key in keys},
            }
        )
    return _table(
        context,
        columns=(("partition", "Partition"),)
        + tuple((key, _title(key)) for key in keys),
        rows=tuple(rows),
        summary={
            "trained_model": context.envelope.result.get("trained_model"),
        },
    )


def _regression_predictions(context: ArtifactRenderContext) -> ArtifactTable:
    return _table_from_object_rows(
        context,
        columns=(
            ("row_index", "Row"),
            ("partition", "Partition"),
            ("actual", "Actual"),
            ("predicted", "Predicted"),
            ("residual", "Residual"),
        ),
        rows=_object_rows(context.envelope.result.get("predictions")),
        summary={
            "target": _dataset_value(context, "target_name"),
        },
    )


def _classification_confusion(context: ArtifactRenderContext) -> ArtifactTable:
    keys = (
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
    )
    rows: list[dict[str, TableCell]] = []
    for partition in ("train", "test"):
        raw_confusion = context.envelope.result.get(f"{partition}_confusion")
        confusion = raw_confusion if isinstance(raw_confusion, dict) else {}
        rows.append(
            {
                "partition": partition,
                **{key: _scalar(confusion.get(key)) for key in keys},
            }
        )
    return _table(
        context,
        columns=(("partition", "Partition"),)
        + tuple((key, _title(key)) for key in keys),
        rows=tuple(rows),
        summary={
            "negative_label": context.envelope.result.get("negative_label"),
            "positive_label": context.envelope.result.get("positive_label"),
        },
    )


def _classification_predictions(context: ArtifactRenderContext) -> ArtifactTable:
    return _table_from_object_rows(
        context,
        columns=(
            ("row_index", "Row"),
            ("partition", "Partition"),
            ("actual", "Actual"),
            ("predicted", "Predicted"),
            ("probability_positive", "Positive probability"),
        ),
        rows=_object_rows(context.envelope.result.get("predictions")),
        summary={
            "target": _dataset_value(context, "target_name"),
            "decision_threshold": context.envelope.result.get(
                "decision_threshold"
            ),
        },
    )


def _placements(context: ArtifactRenderContext) -> ArtifactTable:
    result = context.envelope.result
    requested = result.get("requested")
    source = requested if isinstance(requested, dict) else {}
    placements = _object_rows(source.get("placements"))
    rows: list[dict[str, TableCell]] = []
    for placement in placements:
        position = placement.get("position")
        dimensions = placement.get("dimensions")
        position = position if isinstance(position, dict) else {}
        dimensions = dimensions if isinstance(dimensions, dict) else {}
        rows.append(
            {
                "instance_id": _scalar(placement.get("instance_id")),
                "item_id": _scalar(placement.get("item_id")),
                "item_name": _scalar(placement.get("item_name")),
                "unit_index": _scalar(placement.get("unit_index")),
                "orientation_code": _scalar(placement.get("orientation_code")),
                "x": _scalar(position.get("x")),
                "y": _scalar(position.get("y")),
                "z": _scalar(position.get("z")),
                "length": _scalar(dimensions.get("length")),
                "width": _scalar(dimensions.get("width")),
                "height": _scalar(dimensions.get("height")),
                "value": _scalar(placement.get("value")),
            }
        )
    columns = tuple(
        (key, _title(key))
        for key in (
            "instance_id",
            "item_id",
            "item_name",
            "unit_index",
            "orientation_code",
            "x",
            "y",
            "z",
            "length",
            "width",
            "height",
            "value",
        )
    )
    return _table(
        context,
        columns=columns,
        rows=tuple(rows),
        summary={
            "objective": source.get("objective"),
            "total_value": source.get("total_value"),
            "used_volume": source.get("used_volume"),
            "excluded_instance_ids": source.get("excluded_instance_ids"),
        },
    )


def _table_from_object_rows(
    context: ArtifactRenderContext,
    *,
    columns: tuple[tuple[str, str], ...],
    rows: tuple[dict[str, JsonValue], ...],
    summary: dict[str, JsonValue],
) -> ArtifactTable:
    normalized = tuple(
        {key: _scalar(row.get(key)) for key, _title_value in columns}
        for row in rows
    )
    return _table(context, columns=columns, rows=normalized, summary=summary)


def _table(
    context: ArtifactRenderContext,
    *,
    columns: tuple[tuple[str, str], ...],
    rows: tuple[dict[str, TableCell], ...],
    summary: dict[str, JsonValue],
) -> ArtifactTable:
    definition = _DEFINITIONS_BY_KEY.get(
        (context.capability_id, context.artifact_type)
    )
    if definition is None:
        raise ValueError("canonical table definition is not registered")
    return ArtifactTable(
        artifact_type=context.artifact_type,
        title=definition.title,
        columns=tuple(
            ArtifactTableColumn(key=key, title=title) for key, title in columns
        ),
        rows=rows,
        summary=_without_missing(summary),
    )


def _objective_summary(context: ArtifactRenderContext) -> dict[str, JsonValue]:
    return _without_missing(
        {
            "objective": context.envelope.result.get("objective"),
            "objective_sense": context.envelope.result.get("objective_sense"),
        }
    )


def _object_rows(value: JsonValue | None) -> tuple[dict[str, JsonValue], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _union_keys(rows: tuple[dict[str, JsonValue], ...]) -> set[str]:
    return {key for row in rows for key in row}


def _scalar(value: JsonValue | None) -> TableCell:
    return value if value is None or isinstance(value, (str, int, float, bool)) else None


def _without_missing(values: dict[str, JsonValue | None]) -> dict[str, JsonValue]:
    return {key: value for key, value in values.items() if value is not None}


def _title(key: str) -> str:
    return key.replace("_", " ").title()


def _dataset_value(
    context: ArtifactRenderContext,
    key: str,
) -> JsonValue | None:
    raw_dataset = context.problem.get("dataset")
    dataset = raw_dataset if isinstance(raw_dataset, dict) else {}
    return dataset.get(key)


_DEFINITIONS = (
    CanonicalTableDefinition(
        "lp.continuous", "solution_table", "LP solution", _variables
    ),
    CanonicalTableDefinition(
        "milp.linear", "solution_table", "MILP solution", _variables
    ),
    CanonicalTableDefinition(
        "knapsack.zero_one", "selection_table", "Selected items", _selection
    ),
    CanonicalTableDefinition(
        "knapsack.bounded", "selection_table", "Selected quantities", _selection
    ),
    CanonicalTableDefinition(
        "knapsack.unbounded",
        "selection_table",
        "Selected quantities",
        _selection,
    ),
    CanonicalTableDefinition(
        "knapsack.fractional",
        "selection_table",
        "Selected fractions",
        _selection,
    ),
    CanonicalTableDefinition(
        "knapsack.multi_dimensional",
        "selection_table",
        "Selected quantities",
        _selection,
    ),
    CanonicalTableDefinition(
        "graph.shortest_path.dijkstra",
        "path_table",
        "Shortest path",
        _path,
    ),
    CanonicalTableDefinition(
        "graph.shortest_path.dijkstra",
        "settled_trace_table",
        "Dijkstra settled-node trace",
        _settled_trace,
    ),
    CanonicalTableDefinition(
        "nlp.continuous_local",
        "candidate_table",
        "Local candidate",
        _variables,
    ),
    CanonicalTableDefinition(
        "ml.regression.linear",
        "coefficient_table",
        "Regression coefficients",
        _coefficients,
    ),
    CanonicalTableDefinition(
        "ml.regression.linear",
        "metrics_table",
        "Regression metrics",
        _regression_metrics,
    ),
    CanonicalTableDefinition(
        "ml.regression.linear",
        "prediction_table",
        "Regression predictions",
        _regression_predictions,
    ),
    CanonicalTableDefinition(
        "ml.classification.binary_logistic",
        "coefficient_table",
        "Classification coefficients",
        _coefficients,
    ),
    CanonicalTableDefinition(
        "ml.classification.binary_logistic",
        "metrics_table",
        "Classification metrics",
        _classification_metrics,
    ),
    CanonicalTableDefinition(
        "ml.classification.binary_logistic",
        "confusion_table",
        "Classification confusion counts",
        _classification_confusion,
    ),
    CanonicalTableDefinition(
        "ml.classification.binary_logistic",
        "prediction_table",
        "Classification predictions",
        _classification_predictions,
    ),
    CanonicalTableDefinition(
        "packing.single_container_3d",
        "placement_table",
        "Packing placements",
        _placements,
    ),
)

_DEFINITIONS_BY_CAPABILITY = {
    capability_id: tuple(
        definition
        for definition in _DEFINITIONS
        if definition.capability_id == capability_id
    )
    for capability_id in {definition.capability_id for definition in _DEFINITIONS}
}
_DEFINITIONS_BY_KEY = {
    (definition.capability_id, definition.artifact_type): definition
    for definition in _DEFINITIONS
}
