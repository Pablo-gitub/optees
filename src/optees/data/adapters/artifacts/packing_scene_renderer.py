from __future__ import annotations

import hashlib
import json
import re
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)


_MAX_PLACEMENTS = 500
_CAMERAS = {
    "isometric": (24, -56),
    "front": (0, -90),
    "side": (0, 0),
    "top": (90, -90),
}
_COLORS = (
    "#4f7cff",
    "#4fd1e5",
    "#f59e0b",
    "#a78bfa",
    "#34d399",
    "#fb7185",
    "#60a5fa",
    "#f97316",
    "#2dd4bf",
    "#c084fc",
    "#facc15",
    "#94a3b8",
)
_PALETTES = {
    "light": {
        "background": "#ffffff",
        "panel": "#f5f7fb",
        "text": "#172033",
        "muted": "#667085",
        "grid": "#d8dee9",
        "edge": "#34445f",
    },
    "dark": {
        "background": "#08111f",
        "panel": "#111c2e",
        "text": "#e7edf8",
        "muted": "#9aa8c1",
        "grid": "#34445f",
        "edge": "#9aa8c1",
    },
}


class PackingSceneRenderer:
    renderer_version = "packing-scene-1"

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        scene = _scene(context)
        if (
            context.artifact_type == "scene_views"
            and context.format is ArtifactFormat.PNG
        ):
            return RenderedArtifact("image/png", _render_png(context, scene))
        if (
            context.artifact_type == "scene_model"
            and context.format is ArtifactFormat.OBJ_MTL_ZIP
        ):
            return RenderedArtifact(
                "application/zip",
                _render_obj_mtl_zip(context, scene),
            )
        raise ValueError("packing scene renderer received an unsupported output")


def _scene(context: ArtifactRenderContext) -> dict[str, object]:
    result = context.envelope.result
    requested = result.get("requested")
    requested = requested if isinstance(requested, dict) else {}
    placements = _objects(requested.get("placements"))
    if not placements:
        raise ValueError("packing scene requires at least one placement")
    if len(placements) > _MAX_PLACEMENTS:
        raise ValueError(f"packing scene supports at most {_MAX_PLACEMENTS} placements")
    container = context.problem.get("container")
    container = container if isinstance(container, dict) else {}
    dimensions = container.get("dimensions")
    dimensions = dimensions if isinstance(dimensions, dict) else {}
    normalized_dimensions = {
        axis: _positive_number(dimensions.get(axis), f"container {axis}")
        for axis in ("length", "width", "height")
    }
    normalized_placements = tuple(
        _normalize_placement(placement) for placement in placements
    )
    return {
        "container_id": str(container.get("id") or "container"),
        "container_name": str(container.get("name") or "Container"),
        "dimensions": normalized_dimensions,
        "placements": normalized_placements,
        "excluded_instance_ids": list(
            requested.get("excluded_instance_ids")
            if isinstance(requested.get("excluded_instance_ids"), list)
            else []
        ),
    }


def _normalize_placement(placement: dict) -> dict[str, object]:
    position = placement.get("position")
    position = position if isinstance(position, dict) else {}
    dimensions = placement.get("dimensions")
    dimensions = dimensions if isinstance(dimensions, dict) else {}
    return {
        "instance_id": str(placement.get("instance_id") or "item"),
        "item_id": str(placement.get("item_id") or "item"),
        "item_name": str(
            placement.get("item_name") or placement.get("item_id") or "Item"
        ),
        "unit_index": placement.get("unit_index"),
        "orientation_code": str(placement.get("orientation_code") or ""),
        "x": _number(position.get("x"), "placement x"),
        "y": _number(position.get("y"), "placement y"),
        "z": _number(position.get("z"), "placement z"),
        "length": _positive_number(dimensions.get("length"), "placement length"),
        "width": _positive_number(dimensions.get("width"), "placement width"),
        "height": _positive_number(dimensions.get("height"), "placement height"),
        "value": _number(placement.get("value"), "placement value"),
    }


def _render_png(context: ArtifactRenderContext, scene: dict[str, object]) -> bytes:
    view = str(_extra(context, "view", "isometric"))
    views = tuple(_CAMERAS) if view == "all" else (view,)
    if any(name not in _CAMERAS for name in views):
        raise ValueError("unsupported packing camera view")
    palette = _PALETTES[context.options.theme]
    figure = Figure(
        figsize=(context.options.width / 100, context.options.height / 100),
        dpi=100,
        facecolor=palette["background"],
    )
    FigureCanvasAgg(figure)
    for index, name in enumerate(views, start=1):
        axes = figure.add_subplot(
            2 if len(views) > 1 else 1,
            2 if len(views) > 1 else 1,
            index,
            projection="3d",
        )
        _draw_scene(axes, context, scene, name, palette)
    figure.text(
        0.99,
        0.01,
        "Optees",
        ha="right",
        va="bottom",
        color=palette["muted"],
        fontsize=8,
    )
    figure.tight_layout(rect=(0, 0.025, 1, 1))
    stream = BytesIO()
    figure.savefig(
        stream,
        format="png",
        facecolor=palette["background"],
        dpi=100,
        metadata={"Software": "Optees"},
    )
    return stream.getvalue()


def _draw_scene(axes, context, scene, view: str, palette) -> None:
    dimensions = scene["dimensions"]
    assert isinstance(dimensions, dict)
    placements = scene["placements"]
    assert isinstance(placements, tuple)
    labels = str(_extra(context, "labels", "items"))
    max_labels = int(_extra(context, "max_labels", 30))
    for index, placement in enumerate(placements):
        assert isinstance(placement, dict)
        color = _stable_color(str(placement["item_id"]))
        vertices = _cuboid_vertices(placement)
        axes.add_collection3d(
            Poly3DCollection(
                _cuboid_faces(vertices),
                facecolors=color,
                edgecolors=palette["edge"],
                linewidths=0.7,
                alpha=0.82,
            )
        )
        if labels == "items" and index < max_labels:
            axes.text(
                float(placement["x"]) + float(placement["length"]) / 2,
                float(placement["y"]) + float(placement["width"]) / 2,
                float(placement["z"]) + float(placement["height"]) / 2,
                str(placement["item_name"]),
                ha="center",
                va="center",
                fontsize=7,
                color=palette["text"],
            )
    _draw_container(
        axes,
        float(dimensions["length"]),
        float(dimensions["width"]),
        float(dimensions["height"]),
        palette["muted"],
    )
    axes.set_xlim(0, float(dimensions["length"]))
    axes.set_ylim(0, float(dimensions["width"]))
    axes.set_zlim(0, float(dimensions["height"]))
    axes.set_box_aspect(
        (
            float(dimensions["length"]),
            float(dimensions["width"]),
            float(dimensions["height"]),
        )
    )
    elev, azim = _CAMERAS[view]
    axes.view_init(elev=elev, azim=azim)
    axes.set_facecolor(palette["panel"])
    axes.tick_params(colors=palette["muted"], labelsize=7)
    axes.set_xlabel(
        "Lunghezza" if context.options.locale == "it" else "Length",
        color=palette["text"],
    )
    axes.set_ylabel(
        "Larghezza" if context.options.locale == "it" else "Width",
        color=palette["text"],
    )
    axes.set_zlabel(
        "Altezza" if context.options.locale == "it" else "Height",
        color=palette["text"],
    )
    if view == "front":
        axes.set_ylabel("")
        axes.set_yticks([])
    elif view == "side":
        axes.set_xlabel("")
        axes.set_xticks([])
    elif view == "top":
        axes.set_zlabel("")
        axes.set_zticks([])
    title = {
        "isometric": ("Vista isometrica", "Isometric view"),
        "front": ("Vista frontale", "Front view"),
        "side": ("Vista laterale", "Side view"),
        "top": ("Vista dall'alto", "Top view"),
    }[view][0 if context.options.locale == "it" else 1]
    axes.set_title(title, color=palette["text"], fontsize=10)


def _render_obj_mtl_zip(
    context: ArtifactRenderContext,
    scene: dict[str, object],
) -> bytes:
    placements = scene["placements"]
    assert isinstance(placements, tuple)
    obj_lines = [
        "# Optees orthogonal packing scene",
        "mtllib packing_scene.mtl",
        "",
    ]
    materials: dict[str, tuple[float, float, float]] = {}
    vertex_offset = 1
    for placement in placements:
        assert isinstance(placement, dict)
        item_id = str(placement["item_id"])
        material = (
            f"material_{hashlib.sha256(item_id.encode('utf-8')).hexdigest()[:12]}"
        )
        materials.setdefault(material, _hex_rgb(_stable_color(item_id)))
        name = _obj_name(str(placement["instance_id"]))
        vertices = _cuboid_vertices(placement)
        obj_lines.extend((f"o {name}", f"usemtl {material}"))
        obj_lines.extend(f"v {_fmt(x)} {_fmt(y)} {_fmt(z)}" for x, y, z in vertices)
        for face in _face_indices(vertex_offset):
            obj_lines.append("f " + " ".join(str(index) for index in face))
        obj_lines.append("")
        vertex_offset += 8

    dimensions = scene["dimensions"]
    assert isinstance(dimensions, dict)
    container_vertices = _container_vertices(
        float(dimensions["length"]),
        float(dimensions["width"]),
        float(dimensions["height"]),
    )
    obj_lines.extend(("o container_bounds", "usemtl container_wire"))
    obj_lines.extend(
        f"v {_fmt(x)} {_fmt(y)} {_fmt(z)}" for x, y, z in container_vertices
    )
    for start, end in _edge_indices(vertex_offset):
        obj_lines.append(f"l {start} {end}")
    obj_lines.append("")

    mtl_lines = ["# Optees packing materials", ""]
    for material, color in sorted(materials.items()):
        mtl_lines.extend(
            (
                f"newmtl {material}",
                f"Ka {_fmt(color[0] * 0.2)} {_fmt(color[1] * 0.2)} {_fmt(color[2] * 0.2)}",
                f"Kd {_fmt(color[0])} {_fmt(color[1])} {_fmt(color[2])}",
                "Ks 0.120000 0.120000 0.120000",
                "d 0.820000",
                "illum 2",
                "",
            )
        )
    mtl_lines.extend(
        (
            "newmtl container_wire",
            "Ka 0.100000 0.120000 0.160000",
            "Kd 0.400000 0.480000 0.620000",
            "Ks 0.000000 0.000000 0.000000",
            "d 1.000000",
            "illum 1",
            "",
        )
    )
    manifest = {
        "contract_version": "1",
        "generator": "Optees",
        "capability_id": context.capability_id,
        "artifact_type": context.artifact_type,
        "coordinate_system": {
            "handedness": "right",
            "x_axis": "length",
            "y_axis": "width",
            "z_axis": "height",
            "units": "problem_units",
        },
        "container": {
            "id": scene["container_id"],
            "name": scene["container_name"],
            "dimensions": dimensions,
        },
        "placement_count": len(placements),
        "excluded_instance_ids": scene["excluded_instance_ids"],
        "files": {
            "geometry": "packing_scene.obj",
            "materials": "packing_scene.mtl",
        },
    }
    stream = BytesIO()
    with ZipFile(
        stream, mode="w", compression=ZIP_DEFLATED, compresslevel=9
    ) as archive:
        _write_zip(archive, "packing_scene.obj", "\n".join(obj_lines).encode("utf-8"))
        _write_zip(archive, "packing_scene.mtl", "\n".join(mtl_lines).encode("utf-8"))
        _write_zip(
            archive,
            "manifest.json",
            json.dumps(
                manifest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8"),
        )
    return stream.getvalue()


def _write_zip(archive: ZipFile, name: str, content: bytes) -> None:
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    archive.writestr(info, content, compress_type=ZIP_DEFLATED, compresslevel=9)


def _cuboid_vertices(
    placement: dict[str, object]
) -> tuple[tuple[float, float, float], ...]:
    x = float(placement["x"])
    y = float(placement["y"])
    z = float(placement["z"])
    x2 = x + float(placement["length"])
    y2 = y + float(placement["width"])
    z2 = z + float(placement["height"])
    return (
        (x, y, z),
        (x2, y, z),
        (x2, y2, z),
        (x, y2, z),
        (x, y, z2),
        (x2, y, z2),
        (x2, y2, z2),
        (x, y2, z2),
    )


def _container_vertices(
    length: float,
    width: float,
    height: float,
) -> tuple[tuple[float, float, float], ...]:
    return _cuboid_vertices(
        {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "length": length,
            "width": width,
            "height": height,
        }
    )


def _cuboid_faces(vertices) -> tuple[tuple[tuple[float, float, float], ...], ...]:
    return tuple(tuple(vertices[index] for index in face) for face in _LOCAL_FACES)


_LOCAL_FACES = (
    (0, 1, 2, 3),
    (4, 5, 6, 7),
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
)
_LOCAL_EDGES = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 0),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 4),
    (0, 4),
    (1, 5),
    (2, 6),
    (3, 7),
)


def _face_indices(offset: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(offset + index for index in face) for face in _LOCAL_FACES)


def _edge_indices(offset: int) -> tuple[tuple[int, int], ...]:
    return tuple((offset + start, offset + end) for start, end in _LOCAL_EDGES)


def _draw_container(
    axes, length: float, width: float, height: float, color: str
) -> None:
    vertices = _container_vertices(length, width, height)
    for start, end in _LOCAL_EDGES:
        a = vertices[start]
        b = vertices[end]
        axes.plot(
            (a[0], b[0]),
            (a[1], b[1]),
            (a[2], b[2]),
            color=color,
            linewidth=1.2,
        )


def _stable_color(item_id: str) -> str:
    digest = hashlib.sha256(item_id.encode("utf-8")).digest()
    return _COLORS[int.from_bytes(digest[:2], "big") % len(_COLORS)]


def _hex_rgb(value: str) -> tuple[float, float, float]:
    return tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))


def _obj_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.")
    return normalized[:80] or "item"


def _objects(value: object) -> list[dict]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if normalized != normalized or normalized in {float("inf"), float("-inf")}:
        raise ValueError(f"{label} must be a finite number")
    return normalized


def _positive_number(value: object, label: str) -> float:
    normalized = _number(value, label)
    if normalized <= 0:
        raise ValueError(f"{label} must be positive")
    return normalized


def _extra(context: ArtifactRenderContext, key: str, default: object) -> object:
    return (context.options.extra or {}).get(key, default)


def _fmt(value: float) -> str:
    return f"{float(value):.6f}"
