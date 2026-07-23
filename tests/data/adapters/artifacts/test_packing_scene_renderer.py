from __future__ import annotations

import json
import struct
from dataclasses import replace
from io import BytesIO
from zipfile import ZipFile

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
from optees.application.services.canonical_artifact_tables import (
    canonical_table_definitions_for,
)
from optees.application.services.packing_artifact_scene import (
    packing_scene_definitions,
)
from optees.data.adapters.artifacts.packing_scene_renderer import (
    PackingSceneRenderer,
)


def _problem() -> dict:
    return {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": "optional",
        "gravity_mode": "simple",
        "container": {
            "id": "container-1",
            "name": "Demo Container",
            "dimensions": {"length": 10, "width": 8, "height": 6},
            "capacities": [{"name": "weight", "limit": 30}],
        },
        "items": [
            {
                "id": "box-a",
                "name": "Box A",
                "dimensions": {"length": 4, "width": 3, "height": 2},
                "value": 8,
                "quantity": 2,
                "rotation_policy": "fixed",
                "allowed_orientations": [],
                "consumptions": [{"name": "weight", "amount": 7}],
            },
            {
                "id": "box-b",
                "name": "Box B",
                "dimensions": {"length": 2, "width": 2, "height": 2},
                "value": 5,
                "quantity": 1,
                "rotation_policy": "fixed",
                "allowed_orientations": [],
                "consumptions": [{"name": "weight", "amount": 4}],
            },
        ],
    }


def _result() -> dict:
    placements = [
        {
            "instance_id": "box-a#1",
            "item_id": "box-a",
            "item_name": "Box A",
            "unit_index": 1,
            "orientation_code": "LWH",
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "dimensions": {"length": 4.0, "width": 3.0, "height": 2.0},
            "value": 8.0,
        },
        {
            "instance_id": "unsafe / box-b#1",
            "item_id": "box-b",
            "item_name": "Box B",
            "unit_index": 1,
            "orientation_code": "LWH",
            "position": {"x": 4.0, "y": 0.0, "z": 0.0},
            "dimensions": {"length": 2.0, "width": 2.0, "height": 2.0},
            "value": 5.0,
        },
    ]
    return {
        "requested": {
            "objective": 13.0,
            "total_value": 13.0,
            "used_volume": 32.0,
            "placements": placements,
            "excluded_instance_ids": ["box-a#2"],
        },
        "recovery": None,
    }


def _context(
    artifact_type: str,
    format_: ArtifactFormat,
    *,
    view: str = "isometric",
) -> ArtifactRenderContext:
    return ArtifactRenderContext(
        capability_id="packing.single_container_3d",
        artifact_type=artifact_type,
        format=format_,
        problem=_problem(),
        envelope=ExecutionEnvelope(
            job_id="job-packing-artifact",
            capability_id="packing.single_container_3d",
            job_status=JobStatus.COMPLETED,
            mathematical_status=MathematicalStatus.OPTIMAL,
            termination_reason=TerminationReason.COMPLETED,
            result=_result(),
            diagnostics={},
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
            width=800,
            height=600,
            extra={"view": view, "labels": "items", "max_labels": 10},
        ),
    )


def test_capacity_table_reports_volume_and_custom_resource_usage():
    definition = next(
        item
        for item in canonical_table_definitions_for("packing.single_container_3d")
        if item.artifact_type == "capacity_table"
    )

    table = definition.builder(_context("capacity_table", ArtifactFormat.JSON))

    assert table.rows == (
        {
            "resource": "volume",
            "used": 32.0,
            "limit": 480.0,
            "remaining": 448.0,
            "utilization_percent": pytest.approx(6.6666666667),
        },
        {
            "resource": "weight",
            "used": 11.0,
            "limit": 30.0,
            "remaining": 19.0,
            "utilization_percent": pytest.approx(36.6666666667),
        },
    )


@pytest.mark.parametrize("view", ("isometric", "front", "side", "top", "all"))
def test_named_camera_views_render_bounded_headless_png(view):
    rendered = PackingSceneRenderer().render(
        _context("scene_views", ArtifactFormat.PNG, view=view)
    )

    assert rendered.media_type == "image/png"
    assert rendered.content.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", rendered.content[16:24])
    assert (width, height) == (800, 600)
    pixels = mpimg.imread(BytesIO(rendered.content), format="png")
    assert float(np.ptp(pixels[:, :, :3])) > 0.4
    assert float(np.std(pixels[:, :, :3])) > 0.03


def test_obj_mtl_bundle_is_deterministic_safe_and_self_describing():
    context = replace(
        _context("scene_model", ArtifactFormat.OBJ_MTL_ZIP),
        options=ArtifactRenderOptions(locale="it"),
    )
    renderer = PackingSceneRenderer()

    first = renderer.render(context)
    second = renderer.render(context)

    assert first.media_type == "application/zip"
    assert first.content == second.content
    with ZipFile(BytesIO(first.content)) as archive:
        assert archive.namelist() == [
            "packing_scene.obj",
            "packing_scene.mtl",
            "manifest.json",
        ]
        assert all(
            info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()
        )
        obj = archive.read("packing_scene.obj").decode("utf-8")
        mtl = archive.read("packing_scene.mtl").decode("utf-8")
        manifest = json.loads(archive.read("manifest.json"))

    assert "o unsafe_box-b_1" in obj
    assert "../" not in obj
    assert obj.count("\nv ") == 24
    assert obj.count("\nf ") == 12
    assert obj.count("\nl ") == 12
    assert "newmtl container_wire" in mtl
    assert mtl.count("newmtl material_") == 2
    assert manifest["placement_count"] == 2
    assert manifest["coordinate_system"]["z_axis"] == "height"
    assert manifest["container"]["dimensions"] == {
        "height": 6.0,
        "length": 10.0,
        "width": 8.0,
    }


def test_scene_renderer_rejects_empty_or_unsupported_outputs():
    context = _context("scene_views", ArtifactFormat.PNG)
    empty_result = {
        "requested": {
            **context.envelope.result["requested"],
            "placements": [],
        },
        "recovery": None,
    }
    empty = replace(
        context,
        envelope=replace(context.envelope, result=empty_result),
    )

    with pytest.raises(ValueError, match="at least one placement"):
        PackingSceneRenderer().render(empty)
    with pytest.raises(ValueError, match="unsupported output"):
        PackingSceneRenderer().render(replace(context, format=ArtifactFormat.SVG))


def test_packing_scene_descriptors_expose_bounded_options_and_formats():
    descriptors = {
        definition.artifact_type: definition.descriptor()
        for definition in packing_scene_definitions()
    }

    assert descriptors["scene_views"].formats == (ArtifactFormat.PNG,)
    assert descriptors["scene_model"].formats == (ArtifactFormat.OBJ_MTL_ZIP,)
    properties = descriptors["scene_views"].options_schema["properties"]
    assert properties["view"]["enum"] == [
        "isometric",
        "front",
        "side",
        "top",
        "all",
    ]
    assert properties["max_labels"]["maximum"] == 100
