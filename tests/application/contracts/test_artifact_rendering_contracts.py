from __future__ import annotations

import pytest

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    ArtifactRenderOptions,
    RenderedArtifact,
)
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    ExecutionMetadata,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)


def _envelope(capability_id: str = "lp.continuous") -> ExecutionEnvelope:
    return ExecutionEnvelope(
        job_id="job-1",
        capability_id=capability_id,
        job_status=JobStatus.COMPLETED,
        mathematical_status=MathematicalStatus.OPTIMAL,
        termination_reason=TerminationReason.COMPLETED,
        result={"objective": 10.0},
        diagnostics={},
        metadata=ExecutionMetadata("0.9.0", "v1", "1", "1"),
    )


def test_render_options_are_deterministic_and_strict_json():
    options = ArtifactRenderOptions(locale="it", theme="dark", width=800, height=600)

    assert options.to_dict() == {
        "locale": "it",
        "theme": "dark",
        "width": 800,
        "height": 600,
        "font_family": "DejaVu Sans",
        "extra": {},
    }


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"locale": "fr"}, "locale"),
        ({"theme": "blue"}, "theme"),
        ({"width": 319}, "width"),
        ({"height": 4097}, "height"),
        ({"width": 4096, "height": 4096}, "megapixels"),
        ({"font_family": "Arial"}, "bundled deterministic font"),
    ],
)
def test_render_options_reject_non_deterministic_or_oversized_values(changes, message):
    with pytest.raises(ValueError, match=message):
        ArtifactRenderOptions(**changes)


def test_render_context_requires_problem_and_result_for_same_capability():
    context = ArtifactRenderContext(
        capability_id="lp.continuous",
        artifact_type="solution_table",
        format=ArtifactFormat.CSV,
        problem={"version": "1"},
        envelope=_envelope(),
        options=ArtifactRenderOptions(),
    )

    assert context.problem == {"version": "1"}

    with pytest.raises(ValueError, match="must match"):
        ArtifactRenderContext(
            capability_id="milp.linear",
            artifact_type="solution_table",
            format=ArtifactFormat.CSV,
            problem={"version": "1"},
            envelope=_envelope(),
            options=ArtifactRenderOptions(),
        )


def test_rendered_artifact_rejects_empty_binary_output():
    assert RenderedArtifact("text/csv", b"name,value\nx,1\n").content

    with pytest.raises(ValueError, match="content"):
        RenderedArtifact("text/csv", b"")
