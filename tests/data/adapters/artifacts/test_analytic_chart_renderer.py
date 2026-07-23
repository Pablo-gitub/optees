from __future__ import annotations

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
from optees.application.services.analytic_artifact_visuals import (
    analytic_visual_definitions,
)
from optees.data.adapters.artifacts.analytic_chart_renderer import (
    AnalyticChartRenderer,
)


def _context(definition) -> ArtifactRenderContext:
    capability_id = definition.capability_id
    problem, result, diagnostics = _fixtures(capability_id)
    status = (
        MathematicalStatus.OPTIMAL
        if capability_id == "graph.shortest_path.dijkstra"
        else MathematicalStatus.FEASIBLE
    )
    return ArtifactRenderContext(
        capability_id=capability_id,
        artifact_type=definition.artifact_type,
        format=ArtifactFormat.SVG,
        problem=problem,
        envelope=ExecutionEnvelope(
            job_id="job-analytic-chart",
            capability_id=capability_id,
            job_status=JobStatus.COMPLETED,
            mathematical_status=status,
            termination_reason=TerminationReason.COMPLETED,
            result=result,
            diagnostics=diagnostics,
            metadata=ExecutionMetadata(
                optees_version="test",
                api_version="v1",
                problem_schema_version="1",
                result_schema_version="1",
            ),
        ),
        options=ArtifactRenderOptions(
            locale="en",
            theme="dark",
            width=720,
            height=480,
            extra=_options(definition.artifact_type),
        ),
    )


def _fixtures(capability_id: str) -> tuple[dict, dict, dict]:
    if capability_id == "graph.shortest_path.dijkstra":
        return (
            {
                "version": "1",
                "vertices": [
                    {"id": "A", "label": "Depot"},
                    {"id": "B", "label": "Hub"},
                    {"id": "C", "label": "Customer"},
                ],
                "edges": [
                    {"from": "A", "to": "B", "weight": 2},
                    {"from": "B", "to": "C", "weight": 3},
                    {"from": "A", "to": "C", "weight": 9},
                ],
                "source": "A",
                "destination": "C",
                "directed": False,
            },
            {"distance": 5.0, "path": ["A", "B", "C"], "hop_count": 2},
            {
                "settled_order": ["A", "B", "C"],
                "settled_distances": {"A": 0, "B": 2, "C": 5},
            },
        )
    if capability_id == "nlp.continuous_local":
        return (
            {
                "version": "1",
                "variables": [
                    {"name": "x", "label": "X", "lb": -2, "ub": 4, "initial": 0},
                    {"name": "y", "label": "Y", "lb": -3, "ub": 3, "initial": 0},
                ],
                "objective": {
                    "sense": "min",
                    "expression": "(x - 1)**2 + (y + 1)**2",
                },
            },
            {
                "objective": 0.0,
                "variables": [
                    {"name": "x", "value": 1.0},
                    {"name": "y", "value": -1.0},
                ],
                "local_candidate": True,
            },
            {"convergence_history": [8.0, 3.0, 0.5, 0.0]},
        )
    if capability_id == "ml.regression.linear":
        return (
            {
                "version": "1",
                "dataset": {
                    "feature_names": ["area"],
                    "target_name": "price",
                    "rows": [
                        {"features": [1.0], "target": 3.0},
                        {"features": [2.0], "target": 5.0},
                        {"features": [3.0], "target": 7.0},
                    ],
                },
            },
            {
                "trained_model": True,
                "intercept": 1.0,
                "coefficients": [{"feature": "area", "value": 2.0}],
            },
            {},
        )
    return (
        {
            "version": "1",
            "dataset": {
                "feature_names": ["income", "debt"],
                "target_name": "approved",
                "rows": [
                    {"features": [1.0, 4.0], "target": "no"},
                    {"features": [2.0, 3.0], "target": "no"},
                    {"features": [4.0, 2.0], "target": "yes"},
                    {"features": [5.0, 1.0], "target": "yes"},
                ],
            },
        },
        {
            "trained_model": True,
            "negative_label": "no",
            "positive_label": "yes",
            "intercept": 0.0,
            "coefficients": [
                {"feature": "income", "value": 1.0},
                {"feature": "debt", "value": -1.0},
            ],
            "feature_scaling": [
                {"feature": "income", "mean": 3.0, "scale": 1.5},
                {"feature": "debt", "mean": 2.5, "scale": 1.2},
            ],
            "decision_threshold": 0.5,
            "test_confusion": {
                "true_negative": 2,
                "false_positive": 1,
                "false_negative": 0,
                "true_positive": 3,
            },
        },
        {},
    )


def _options(artifact_type: str) -> dict:
    if artifact_type == "objective_landscape":
        return {"view": "surface", "resolution": 30}
    if artifact_type in {
        "convergence_chart",
        "fit_chart",
        "decision_boundary",
    }:
        return {"max_points": 100}
    return {}


@pytest.mark.parametrize(
    "definition",
    analytic_visual_definitions(),
    ids=lambda item: f"{item.capability_id}-{item.artifact_type}",
)
def test_every_analytic_visual_renders_headless_svg(definition):
    rendered = AnalyticChartRenderer(definition).render(_context(definition))

    assert rendered.media_type == "image/svg+xml"
    assert b"<svg" in rendered.content
    assert b"Optees" in rendered.content
    assert len(rendered.content) > 5_000


def test_analytic_visual_renders_png_without_gui_backend():
    definition = next(
        item
        for item in analytic_visual_definitions()
        if item.artifact_type == "confusion_matrix"
    )
    context = replace(_context(definition), format=ArtifactFormat.PNG)

    rendered = AnalyticChartRenderer(definition).render(context)

    assert rendered.media_type == "image/png"
    assert rendered.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(rendered.content) > 5_000


def test_regression_fit_rejects_multivariate_dataset():
    definition = next(
        item
        for item in analytic_visual_definitions()
        if item.artifact_type == "fit_chart"
    )
    context = _context(definition)
    dataset = context.problem["dataset"]
    assert isinstance(dataset, dict)
    context = replace(
        context,
        problem={
            **context.problem,
            "dataset": {
                **dataset,
                "feature_names": ["area", "rooms"],
            },
        },
    )

    with pytest.raises(ValueError, match="exactly one feature"):
        AnalyticChartRenderer(definition).render(context)


def test_decision_boundary_rejects_non_two_feature_dataset():
    definition = next(
        item
        for item in analytic_visual_definitions()
        if item.artifact_type == "decision_boundary"
    )
    context = _context(definition)
    dataset = context.problem["dataset"]
    assert isinstance(dataset, dict)
    context = replace(
        context,
        problem={
            **context.problem,
            "dataset": {
                **dataset,
                "feature_names": ["income"],
            },
        },
    )

    with pytest.raises(ValueError, match="exactly two features"):
        AnalyticChartRenderer(definition).render(context)
