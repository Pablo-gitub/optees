from __future__ import annotations

import io
import struct

import matplotlib.image as mpimg
import numpy as np
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
from optees.data.adapters.artifacts.lp_feasible_region_renderer import (
    LPFeasibleRegionRenderer,
)


def _context(
    *,
    dimension: int,
    format_: ArtifactFormat,
    width: int = 640,
    height: int = 420,
) -> ArtifactRenderContext:
    names = [f"x{index + 1}" for index in range(dimension)]
    variables = [
        {"name": name, "label": f"Decision {index + 1}", "lb": 0, "ub": 6}
        for index, name in enumerate(names)
    ]
    result_variables = [
        {"name": name, "value": float(index + 1)}
        for index, name in enumerate(names)
    ]
    envelope = ExecutionEnvelope(
        job_id="job-lp-visual",
        capability_id="lp.continuous",
        job_status=JobStatus.COMPLETED,
        mathematical_status=MathematicalStatus.OPTIMAL,
        termination_reason=TerminationReason.COMPLETED,
        result={
            "objective": 1.0,
            "variables": result_variables,
            "optimal_face": {},
        },
        diagnostics={},
        metadata=ExecutionMetadata(
            optees_version="test",
            api_version="v1",
            problem_schema_version="1",
            result_schema_version="1",
        ),
    )
    return ArtifactRenderContext(
        capability_id="lp.continuous",
        artifact_type="feasible_region",
        format=format_,
        problem={
            "version": "1",
            "variables": variables,
            "objective": {
                "sense": "max",
                "coefficients": [1] * dimension,
                "offset": 0,
            },
            "constraints": [
                {
                    "coefficients": [1] * dimension,
                    "relation": "<=",
                    "rhs": 6,
                }
            ],
        },
        envelope=envelope,
        options=ArtifactRenderOptions(
            locale="en",
            theme="dark",
            width=width,
            height=height,
        ),
    )


def test_lp_2d_png_has_requested_dimensions_and_nonblank_pixels():
    rendered = LPFeasibleRegionRenderer().render(
        _context(dimension=2, format_=ArtifactFormat.PNG)
    )

    assert rendered.media_type == "image/png"
    assert rendered.content.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", rendered.content[16:24])
    image = mpimg.imread(io.BytesIO(rendered.content), format="png")

    assert (width, height) == (640, 420)
    assert image.shape[:2] == (420, 640)
    assert float(np.std(image[:, :, :3])) > 0.02


def test_lp_3d_svg_is_structured_and_contains_axis_labels():
    rendered = LPFeasibleRegionRenderer().render(
        _context(dimension=3, format_=ArtifactFormat.SVG)
    )
    svg = rendered.content.decode("utf-8")

    assert rendered.media_type == "image/svg+xml"
    assert "<svg" in svg
    assert "Decision 1" in svg
    assert "Decision 2" in svg
    assert "Decision 3" in svg
    assert "Optees" in svg
    assert len(rendered.content) > 10_000


def test_lp_visual_rejects_dimensions_outside_the_documented_slice():
    with pytest.raises(ValueError, match="2 or 3 variables"):
        LPFeasibleRegionRenderer().render(
            _context(dimension=4, format_=ArtifactFormat.PNG)
        )
