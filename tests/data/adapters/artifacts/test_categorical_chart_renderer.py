from __future__ import annotations

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
from optees.application.services.categorical_artifact_visuals import (
    categorical_visual_definitions,
)
from optees.data.adapters.artifacts.categorical_chart_renderer import (
    CategoricalChartRenderer,
)


def _context(definition, *, max_items: int = 40) -> ArtifactRenderContext:
    if definition.chart_kind == "variables":
        problem = {"version": "1"}
        result = {
            "variables": [
                {"name": f"x{index}", "value": float(index)}
                for index in range(45)
            ]
        }
    elif definition.chart_kind == "items":
        problem = {
            "version": "1",
            "items": [
                {"name": f"Item {index}", "value": index + 1, "weight": index + 2}
                for index in range(45)
            ],
        }
        result = {"selected_indices": [1, 3, 5]}
    elif definition.chart_kind == "capacity":
        problem = {"version": "1", "capacity": 10}
        result = {"total_weight": 7}
    else:
        problem = {"version": "1"}
        result = {
            "resources": [
                {"name": "Weight", "used": 7, "remaining": 3, "capacity": 10},
                {"name": "Volume", "used": 4, "remaining": 4, "capacity": 8},
            ]
        }
    envelope = ExecutionEnvelope(
        job_id="job-chart",
        capability_id=definition.capability_id,
        job_status=JobStatus.COMPLETED,
        mathematical_status=MathematicalStatus.OPTIMAL,
        termination_reason=TerminationReason.COMPLETED,
        result=result,
        diagnostics={},
        metadata=ExecutionMetadata(
            optees_version="test",
            api_version="v1",
            problem_schema_version="1",
            result_schema_version="1",
        ),
    )
    return ArtifactRenderContext(
        capability_id=definition.capability_id,
        artifact_type=definition.artifact_type,
        format=ArtifactFormat.SVG,
        problem=problem,
        envelope=envelope,
        options=ArtifactRenderOptions(
            locale="en",
            theme="dark",
            width=640,
            height=420,
            extra={"max_items": max_items}
            if definition.bounded_categories
            else {},
        ),
    )


@pytest.mark.parametrize(
    "definition",
    categorical_visual_definitions(),
    ids=lambda item: f"{item.capability_id}-{item.artifact_type}",
)
def test_every_categorical_visual_renders_headless_svg(definition):
    rendered = CategoricalChartRenderer(definition).render(_context(definition))

    assert rendered.media_type == "image/svg+xml"
    assert b"<svg" in rendered.content
    assert b"Optees" in rendered.content
    assert len(rendered.content) > 5_000


def test_large_milp_chart_declares_visible_truncation():
    definition = categorical_visual_definitions()[0]
    rendered = CategoricalChartRenderer(definition).render(
        _context(definition, max_items=10)
    )

    assert b"Showing 10 of 45 categories" in rendered.content
