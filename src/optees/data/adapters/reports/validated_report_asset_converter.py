from __future__ import annotations

import io
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.report_backend import ReportBackendAsset
from optees.application.contracts.report_composition import ResolvedReportArtifact
from optees.application.contracts.report_conversion import ConvertedReportArtifact


_MAX_ARCHIVE_ENTRIES = 128
_MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
_MAX_XML_BYTES = 8 * 1024 * 1024
_MAX_TABLE_ROWS = 500
_MAX_TABLE_COLUMNS = 50
_MAX_TABLE_CELLS = 10_000
_MAX_OBJ_VERTICES = 5_000
_MAX_OBJ_FACES = 5_000
_MAX_OBJ_OBJECTS = 500
_CAMERAS = {
    "isometric": (24, -56),
    "front": (0, -90),
    "side": (0, 0),
    "top": (90, -90),
}


@dataclass(frozen=True)
class _ObjObject:
    name: str
    material: str | None
    faces: tuple[tuple[int, ...], ...]


class ValidatedReportAssetConverter:
    """Bounded converters for stored XLSX tables and Optees OBJ/MTL bundles."""

    converter_version = "report-assets-1"

    def convert(
        self,
        artifact: ResolvedReportArtifact,
        *,
        views: tuple[str, ...],
        locale: str,
    ) -> ConvertedReportArtifact:
        if artifact.manifest is None or artifact.content is None:
            return ConvertedReportArtifact(
                unavailable_reason=artifact.unavailable_reason
                or "The artifact is unavailable."
            )
        try:
            if artifact.manifest.format is ArtifactFormat.XLSX:
                return ConvertedReportArtifact(
                    markdown=_xlsx_to_markdown(artifact.content)
                )
            if artifact.manifest.format is ArtifactFormat.OBJ_MTL_ZIP:
                selected = views or ("isometric",)
                return ConvertedReportArtifact(
                    assets=_obj_bundle_views(
                        artifact.artifact_id,
                        artifact.content,
                        selected,
                        locale,
                    )
                )
        except (
            ValueError,
            KeyError,
            UnicodeDecodeError,
            BadZipFile,
            ElementTree.ParseError,
        ):
            return ConvertedReportArtifact(
                unavailable_reason=(
                    "The stored artifact failed bounded report conversion."
                )
            )
        return ConvertedReportArtifact(
            unavailable_reason=(
                f"Format '{artifact.manifest.format.value}' has no report conversion."
            )
        )


def _xlsx_to_markdown(content: bytes) -> str:
    with ZipFile(io.BytesIO(content)) as archive:
        _validate_archive(archive)
        shared = _shared_strings(archive)
        worksheet_name = _first_worksheet(archive)
        worksheet = _xml(archive, worksheet_name)
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows: list[list[str]] = []
    cell_count = 0
    for row in worksheet.iter(f"{namespace}row"):
        values: list[str] = []
        for cell in row.findall(f"{namespace}c"):
            cell_count += 1
            if cell_count > _MAX_TABLE_CELLS:
                raise ValueError("spreadsheet cell limit exceeded")
            column = _cell_column(cell.get("r", ""))
            if column >= _MAX_TABLE_COLUMNS:
                raise ValueError("spreadsheet column limit exceeded")
            while len(values) <= column:
                values.append("")
            values[column] = _cell_value(cell, shared, namespace)
        rows.append(values)
        if len(rows) > _MAX_TABLE_ROWS:
            raise ValueError("spreadsheet row limit exceeded")
    if not rows:
        raise ValueError("spreadsheet has no rows")
    width = max(len(row) for row in rows)
    if width < 1:
        raise ValueError("spreadsheet has no cells")
    normalized = [row + [""] * (width - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(_escape(value) for value in normalized[0]) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    lines.extend(
        "| " + " | ".join(_escape(value) for value in row) + " |"
        for row in normalized[1:]
    )
    return "\n".join(lines)


def _shared_strings(archive: ZipFile) -> tuple[str, ...]:
    try:
        root = _xml(archive, "xl/sharedStrings.xml")
    except KeyError:
        return ()
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    return tuple(
        "".join(node.text or "" for node in item.iter(f"{namespace}t"))
        for item in root.findall(f"{namespace}si")
    )


def _first_worksheet(archive: ZipFile) -> str:
    workbook = _xml(archive, "xl/workbook.xml")
    relations = _xml(archive, "xl/_rels/workbook.xml.rels")
    main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    package = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    sheet = workbook.find(f"{main}sheets/{main}sheet")
    if sheet is None:
        raise ValueError("spreadsheet has no worksheets")
    relationship_id = sheet.get(f"{rel}id")
    for relation in relations.findall(f"{package}Relationship"):
        if relation.get("Id") == relationship_id:
            target = relation.get("Target", "").lstrip("/")
            candidate = (
                PurePosixPath(target)
                if target.startswith("xl/")
                else PurePosixPath("xl") / PurePosixPath(target)
            )
            normalized = str(candidate)
            if ".." in candidate.parts or not normalized.startswith("xl/"):
                raise ValueError("unsafe worksheet relationship")
            return normalized
    raise ValueError("worksheet relationship is missing")


def _xml(archive: ZipFile, name: str) -> ElementTree.Element:
    info = archive.getinfo(name)
    if info.file_size > _MAX_XML_BYTES:
        raise ValueError("spreadsheet XML exceeds the configured limit")
    return ElementTree.fromstring(archive.read(name))


def _cell_value(
    cell: ElementTree.Element,
    shared: tuple[str, ...],
    namespace: str,
) -> str:
    type_ = cell.get("t")
    if type_ == "inlineStr":
        inline = cell.find(f"{namespace}is")
        return "" if inline is None else "".join(
            node.text or "" for node in inline.iter(f"{namespace}t")
        )
    value = cell.findtext(f"{namespace}v", default="")
    if type_ == "s":
        index = int(value)
        if index < 0 or index >= len(shared):
            raise ValueError("invalid shared string index")
        return shared[index]
    if type_ == "b":
        return "true" if value == "1" else "false"
    return value


def _cell_column(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference.upper())
    if match is None:
        return 0
    result = 0
    for character in match.group(1):
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def _obj_bundle_views(
    artifact_id: str,
    content: bytes,
    views: tuple[str, ...],
    locale: str,
) -> tuple[ReportBackendAsset, ...]:
    if any(view not in _CAMERAS for view in views):
        raise ValueError("unsupported OBJ camera")
    with ZipFile(io.BytesIO(content)) as archive:
        _validate_archive(archive)
        obj = archive.read("packing_scene.obj").decode("utf-8")
        mtl = archive.read("packing_scene.mtl").decode("utf-8")
    vertices, objects = _parse_obj(obj)
    colors = _parse_mtl(mtl)
    return tuple(
        ReportBackendAsset(
            asset_id=f"{artifact_id}-{view}",
            media_type="image/png",
            suffix=".png",
            content=_render_obj_view(vertices, objects, colors, view, locale),
        )
        for view in views
    )


def _parse_obj(
    content: str,
) -> tuple[tuple[tuple[float, float, float], ...], tuple[_ObjObject, ...]]:
    vertices: list[tuple[float, float, float]] = []
    objects: list[_ObjObject] = []
    name = "scene"
    material: str | None = None
    faces: list[tuple[int, ...]] = []

    def finish() -> None:
        nonlocal faces
        if faces:
            objects.append(_ObjObject(name, material, tuple(faces)))
            faces = []

    for line in content.splitlines():
        values = line.strip().split()
        if not values or values[0].startswith("#"):
            continue
        if values[0] == "v" and len(values) == 4:
            vertex = tuple(float(value) for value in values[1:4])
            if not all(math.isfinite(value) for value in vertex):
                raise ValueError("OBJ vertex contains a non-finite coordinate")
            vertices.append(vertex)
            if len(vertices) > _MAX_OBJ_VERTICES:
                raise ValueError("OBJ vertex limit exceeded")
        elif values[0] == "o":
            finish()
            name = " ".join(values[1:])[:80] or "object"
            material = None
            if len(objects) >= _MAX_OBJ_OBJECTS:
                raise ValueError("OBJ object limit exceeded")
        elif values[0] == "usemtl":
            material = values[1][:100] if len(values) > 1 else None
        elif values[0] == "f":
            indices = tuple(int(value.split("/", 1)[0]) - 1 for value in values[1:])
            if len(indices) < 3 or any(
                index < 0 or index >= len(vertices) for index in indices
            ):
                raise ValueError("OBJ face contains an invalid vertex")
            faces.append(indices)
            if sum(len(item.faces) for item in objects) + len(faces) > _MAX_OBJ_FACES:
                raise ValueError("OBJ face limit exceeded")
    finish()
    if not vertices or not objects:
        raise ValueError("OBJ contains no renderable geometry")
    return tuple(vertices), tuple(objects)


def _parse_mtl(content: str) -> dict[str, tuple[float, float, float]]:
    colors: dict[str, tuple[float, float, float]] = {}
    current: str | None = None
    for line in content.splitlines():
        values = line.strip().split()
        if not values:
            continue
        if values[0] == "newmtl" and len(values) > 1:
            current = values[1][:100]
        elif values[0] == "Kd" and len(values) == 4 and current is not None:
            color = tuple(float(value) for value in values[1:])
            if any(
                not math.isfinite(value) or value < 0 or value > 1
                for value in color
            ):
                raise ValueError("MTL color is outside the supported range")
            colors[current] = color
    return colors


def _render_obj_view(vertices, objects, colors, view: str, locale: str) -> bytes:
    figure = Figure(figsize=(9.6, 6.4), dpi=100, facecolor="#ffffff")
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111, projection="3d")
    all_points: list[tuple[float, float, float]] = []
    for object_ in objects:
        polygons = [
            [vertices[index] for index in face]
            for face in object_.faces
        ]
        all_points.extend(point for polygon in polygons for point in polygon)
        axes.add_collection3d(
            Poly3DCollection(
                polygons,
                facecolors=colors.get(object_.material or "", (0.31, 0.49, 1.0)),
                edgecolors="#34445f",
                linewidths=0.6,
                alpha=0.82,
            )
        )
    xs, ys, zs = zip(*all_points)
    axes.set_xlim(*_axis_limits(min(xs), max(xs)))
    axes.set_ylim(*_axis_limits(min(ys), max(ys)))
    axes.set_zlim(*_axis_limits(min(zs), max(zs)))
    axes.set_box_aspect(
        (
            max(max(xs) - min(xs), 1),
            max(max(ys) - min(ys), 1),
            max(max(zs) - min(zs), 1),
        )
    )
    axes.view_init(*_CAMERAS[view])
    axes.set_xlabel("Lunghezza" if locale == "it" else "Length")
    axes.set_ylabel("Larghezza" if locale == "it" else "Width")
    axes.set_zlabel("Altezza" if locale == "it" else "Height")
    axes.set_title(
        {
            "isometric": ("Vista isometrica", "Isometric view"),
            "front": ("Vista frontale", "Front view"),
            "side": ("Vista laterale", "Side view"),
            "top": ("Vista dall'alto", "Top view"),
        }[view][0 if locale == "it" else 1]
    )
    figure.tight_layout()
    stream = io.BytesIO()
    figure.savefig(stream, format="png", metadata={"Software": "Optees"})
    return stream.getvalue()


def _validate_archive(archive: ZipFile) -> None:
    infos = archive.infolist()
    if len(infos) > _MAX_ARCHIVE_ENTRIES:
        raise ValueError("archive entry limit exceeded")
    total = 0
    names: set[str] = set()
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
            raise ValueError("archive contains an unsafe path")
        if info.filename in names:
            raise ValueError("archive contains duplicate entry names")
        names.add(info.filename)
        total += info.file_size
        if total > _MAX_ARCHIVE_BYTES:
            raise ValueError("archive size limit exceeded")
        if info.compress_size > 0 and info.file_size > info.compress_size * 200:
            raise ValueError("archive compression ratio is unsafe")


def _axis_limits(minimum: float, maximum: float) -> tuple[float, float]:
    if minimum != maximum:
        return minimum, maximum
    padding = max(abs(minimum) * 0.05, 0.5)
    return minimum - padding, maximum + padding


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")
