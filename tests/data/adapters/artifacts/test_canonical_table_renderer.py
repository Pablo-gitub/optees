from __future__ import annotations

import csv
import io
import json
from dataclasses import replace

import pytest

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    ArtifactRenderOptions,
)
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    ExecutionMetadata,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.application.contracts.solution_validation import (
    SolutionValidation,
    ValidationCheck,
    ValidationCheckStatus,
)
from optees.application.services.canonical_artifact_tables import (
    canonical_table_definition,
    canonical_table_definitions,
    canonical_table_definitions_for,
)
from optees.data.adapters.artifacts.canonical_table_renderer import (
    CanonicalTableRenderer,
)


_RESULTS = {
    "lp.continuous": {
        "objective": 7.0,
        "objective_sense": "max",
        "variables": [{"name": "x, primary", "value": 2.0}],
    },
    "milp.linear": {
        "objective": 7.0,
        "variables": [{"name": "x", "value": 2.0}],
    },
    "knapsack.zero_one": {
        "objective": 9.0,
        "selected_items": [{"index": 1, "name": "B"}],
        "total_value": 9.0,
        "total_weight": 3,
        "remaining_capacity": 1,
    },
    "knapsack.bounded": {
        "objective": 9.0,
        "selected_items": [{"index": 1, "name": "B", "quantity": 2}],
        "total_value": 9.0,
    },
    "knapsack.unbounded": {
        "objective": 9.0,
        "selected_items": [{"index": 1, "name": "B", "quantity": 2}],
        "total_value": 9.0,
    },
    "knapsack.fractional": {
        "objective": 9.0,
        "selected_items": [{"index": 1, "name": "B", "fraction": 0.5}],
        "total_value": 9.0,
    },
    "knapsack.multi_dimensional": {
        "objective": 9.0,
        "selected_items": [{"index": 1, "name": "B", "quantity": 1.0}],
        "total_value": 9.0,
    },
    "graph.shortest_path.dijkstra": {
        "distance": 3.0,
        "path": ["A", "B"],
        "hop_count": 1,
    },
    "nlp.continuous_local": {
        "objective": 1.0,
        "variables": [{"name": "x", "value": 2.0}],
        "local_candidate": True,
    },
    "ml.regression.linear": {
        "trained_model": True,
        "intercept": 1.0,
        "coefficients": [{"feature": "sales", "value": 2.0}],
        "train_metrics": {
            "mae": 0.08,
            "mse": 0.01,
            "rmse": 0.1,
            "r_squared": 0.98,
        },
        "test_metrics": {
            "mae": 0.15,
            "mse": 0.04,
            "rmse": 0.2,
            "r_squared": 0.91,
        },
        "predictions": [
            {
                "row_index": 0,
                "actual": 3.0,
                "predicted": 3.1,
                "residual": -0.1,
                "partition": "train",
            }
        ],
    },
    "ml.classification.binary_logistic": {
        "trained_model": True,
        "negative_label": "no",
        "positive_label": "yes",
        "intercept": -1.0,
        "coefficients": [{"feature": "risk", "value": 2.0}],
        "decision_threshold": 0.5,
        "train_metrics": {
            "accuracy": 0.9,
            "precision": 0.8,
            "recall": 1.0,
            "f1": 0.89,
        },
        "test_metrics": {
            "accuracy": 0.8,
            "precision": 0.75,
            "recall": 0.75,
            "f1": 0.75,
        },
        "train_confusion": {
            "true_negative": 4,
            "false_positive": 1,
            "false_negative": 0,
            "true_positive": 5,
        },
        "test_confusion": {
            "true_negative": 2,
            "false_positive": 1,
            "false_negative": 1,
            "true_positive": 4,
        },
        "predictions": [
            {
                "row_index": 0,
                "actual": "yes",
                "predicted": "yes",
                "probability_positive": 0.9,
                "partition": "train",
            }
        ],
    },
    "packing.single_container_3d": {
        "requested": {
            "objective": 5.0,
            "total_value": 5.0,
            "used_volume": 24.0,
            "placements": [
                {
                    "instance_id": "box-1",
                    "item_id": "box",
                    "item_name": "Box",
                    "unit_index": 0,
                    "orientation_code": "LWH",
                    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "dimensions": {
                        "length": 2.0,
                        "width": 3.0,
                        "height": 4.0,
                    },
                    "value": 5.0,
                }
            ],
            "excluded_instance_ids": [],
        },
        "recovery": None,
    },
}


def _context(
    capability_id: str,
    format_: ArtifactFormat,
    *,
    artifact_type: str | None = None,
) -> ArtifactRenderContext:
    definition = canonical_table_definition(capability_id)
    assert definition is not None
    diagnostics = {}
    if capability_id == "graph.shortest_path.dijkstra":
        diagnostics = {
            "settled_order": ["A", "B"],
            "settled_distances": {"A": 0.0, "B": 3.0},
            "settled_count": 2,
        }
    envelope = ExecutionEnvelope(
        job_id="job-table",
        capability_id=capability_id,
        job_status=JobStatus.COMPLETED,
        mathematical_status=MathematicalStatus.OPTIMAL,
        termination_reason=TerminationReason.COMPLETED,
        result=_RESULTS[capability_id],
        diagnostics=diagnostics,
        metadata=ExecutionMetadata(
            optees_version="test",
            api_version="v1",
            problem_schema_version="1",
            result_schema_version="1",
        ),
    )
    return ArtifactRenderContext(
        capability_id=capability_id,
        artifact_type=artifact_type or definition.artifact_type,
        format=format_,
        problem={
            "version": "1",
            "dataset": {"target_name": "target"},
        },
        envelope=envelope,
        options=ArtifactRenderOptions(),
    )


@pytest.mark.parametrize(
    "definition",
    canonical_table_definitions(),
    ids=lambda item: f"{item.capability_id}-{item.artifact_type}",
)
def test_every_public_capability_builds_a_nonempty_canonical_table(definition):
    table = definition.builder(
        _context(
            definition.capability_id,
            ArtifactFormat.JSON,
            artifact_type=definition.artifact_type,
        )
    )

    assert table.artifact_type == definition.artifact_type
    assert table.columns
    assert table.rows
    expected_keys = {column.key for column in table.columns}
    assert all(set(row) == expected_keys for row in table.rows)


def test_renderer_emits_deterministic_structured_json_and_escaped_csv():
    definition = canonical_table_definition("lp.continuous")
    assert definition is not None
    renderer = CanonicalTableRenderer(definition.builder)

    json_result = renderer.render(_context("lp.continuous", ArtifactFormat.JSON))
    repeated = renderer.render(_context("lp.continuous", ArtifactFormat.JSON))
    csv_result = renderer.render(_context("lp.continuous", ArtifactFormat.CSV))

    assert json_result.media_type == "application/json"
    assert json_result.content == repeated.content
    payload = json.loads(json_result.content)
    assert payload["artifact_type"] == "solution_table"
    assert payload["rows"] == [{"name": "x, primary", "value": 2.0}]
    assert payload["summary"]["objective"] == 7.0

    assert csv_result.media_type == "text/csv; charset=utf-8"
    rows = list(csv.DictReader(io.StringIO(csv_result.content.decode("utf-8"))))
    assert rows == [{"name": "x, primary", "value": "2.0"}]


def test_definitions_advertise_only_formats_implemented_by_the_renderer():
    for definition in canonical_table_definitions():
        descriptor = definition.descriptor()
        assert descriptor.formats == (
            ArtifactFormat.JSON,
            ArtifactFormat.CSV,
            ArtifactFormat.MARKDOWN,
        )
        if definition.artifact_type not in {
            "validation_summary",
            "diagnostics_table",
        }:
            assert descriptor.required_mathematical_statuses


def test_markdown_declares_truncation_and_escapes_table_content():
    definition = canonical_table_definition("lp.continuous")
    assert definition is not None
    context = _context("lp.continuous", ArtifactFormat.MARKDOWN)
    context = replace(
        context,
        envelope=replace(
            context.envelope,
            result={
                **context.envelope.result,
                "variables": [
                    {"name": "first|variable", "value": 1.0},
                    {"name": "second\nvariable", "value": 2.0},
                    {"name": "third", "value": 3.0},
                ],
            },
        ),
        options=replace(context.options, locale="it", extra={"max_rows": 2}),
    )

    rendered = CanonicalTableRenderer(definition.builder).render(context)
    markdown = rendered.content.decode("utf-8")

    assert rendered.media_type == "text/markdown; charset=utf-8"
    assert "first\\|variable" in markdown
    assert "second<br>variable" in markdown
    assert '"total_rows": 3' in markdown
    assert '"displayed_rows": 2' in markdown
    assert '"truncated": true' in markdown
    assert "Mostrate 2 righe su 3" in markdown
    assert "third" not in markdown


def test_milp_validation_and_diagnostics_preserve_machine_readable_semantics():
    context = _context(
        "milp.linear",
        ArtifactFormat.JSON,
        artifact_type="validation_summary",
    )
    validation = SolutionValidation.from_checks(
        (
            ValidationCheck(
                code="milp.integrality",
                status=ValidationCheckStatus.PASSED,
                description="Integer variables satisfy integrality tolerance.",
                measurements={"maximum_violation": 0.0},
            ),
        ),
        tolerances={"integrality": 1e-7},
    )
    context = replace(
        context,
        envelope=replace(
            context.envelope,
            validation=validation,
            diagnostics={"mip_gap": 0.0, "node_count": 3},
            warnings=("A bounded diagnostic warning.",),
        ),
    )

    validation_definition = next(
        item
        for item in canonical_table_definitions_for("milp.linear")
        if item.artifact_type == "validation_summary"
    )
    diagnostics_definition = next(
        item
        for item in canonical_table_definitions_for("milp.linear")
        if item.artifact_type == "diagnostics_table"
    )
    validation_payload = json.loads(
        CanonicalTableRenderer(validation_definition.builder)
        .render(context)
        .content
    )
    diagnostics_payload = json.loads(
        CanonicalTableRenderer(diagnostics_definition.builder)
        .render(replace(context, artifact_type="diagnostics_table"))
        .content
    )

    assert validation_payload["rows"][1]["code"] == "milp.integrality"
    assert validation_payload["rows"][1]["status"] == "passed"
    assert '"maximum_violation":0.0' in validation_payload["rows"][1]["details"]
    assert diagnostics_payload["rows"] == [
        {"field": "mathematical_status", "value": "optimal"},
        {"field": "termination_reason", "value": "completed"},
        {"field": "mip_gap", "value": 0.0},
        {"field": "node_count", "value": 3},
    ]
    assert diagnostics_payload["summary"]["warning_count"] == 1
