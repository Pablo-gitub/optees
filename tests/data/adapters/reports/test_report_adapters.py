from __future__ import annotations

import io
from pathlib import Path
from threading import Event
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from optees.application.contracts.artifact import (
    ArtifactFormat,
    ArtifactManifestEntry,
    ArtifactProvenance,
    ArtifactStatus,
)
from optees.application.contracts.report_backend import (
    ReportBackendAsset,
    ReportBackendRequest,
)
from optees.application.contracts.report_composition import ResolvedReportArtifact
from optees.data.adapters.reports.pandoc_typst_report_backend import (
    PandocTypstReportBackend,
)
from optees.data.adapters.reports.validated_report_asset_converter import (
    ValidatedReportAssetConverter,
)


def _resolved(
    format_: ArtifactFormat,
    media_type: str,
    content: bytes,
) -> ResolvedReportArtifact:
    manifest = ArtifactManifestEntry(
        artifact_id="artifact-test",
        artifact_type="test_asset",
        format=format_,
        media_type=media_type,
        status=ArtifactStatus.AVAILABLE,
        provenance=ArtifactProvenance(
            capability_id="test.capability",
            job_id="job-test",
            problem_schema_version="1",
            result_schema_version="1",
            renderer_version="test-1",
            locale="en",
        ),
        created_at="2026-01-01T00:00:00Z",
        expires_at="2026-01-01T01:00:00Z",
        size_bytes=len(content),
        sha256="0" * 64,
    )
    return ResolvedReportArtifact(
        artifact_id=manifest.artifact_id,
        manifest=manifest,
        content=content,
    )


def _xlsx(rows: list[list[str]]) -> bytes:
    cells = []
    for row_number, row in enumerate(rows, 1):
        values = "".join(
            (
                f'<c r="{chr(65 + column)}{row_number}" t="inlineStr">'
                f"<is><t>{value}</t></is></c>"
            )
            for column, value in enumerate(row)
        )
        cells.append(f'<row r="{row_number}">{values}</row>')
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            (
                '<workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships"><sheets>'
                '<sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
                "</sheets></workbook>"
            ),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
                '2006/relationships"><Relationship Id="rId1" '
                'Target="worksheets/sheet1.xml"/></Relationships>'
            ),
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            (
                '<worksheet xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main"><sheetData>'
                + "".join(cells)
                + "</sheetData></worksheet>"
            ),
        )
    return stream.getvalue()


def _obj_bundle() -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "packing_scene.obj",
            "\n".join(
                (
                    "mtllib packing_scene.mtl",
                    "o box",
                    "usemtl blue",
                    "v 0 0 0",
                    "v 1 0 0",
                    "v 1 1 0",
                    "v 0 1 0",
                    "v 0 0 1",
                    "v 1 0 1",
                    "v 1 1 1",
                    "v 0 1 1",
                    "f 1 2 3 4",
                    "f 5 8 7 6",
                    "f 1 5 6 2",
                    "f 2 6 7 3",
                    "f 3 7 8 4",
                    "f 5 1 4 8",
                )
            ),
        )
        archive.writestr("packing_scene.mtl", "newmtl blue\nKd 0.2 0.5 0.9\n")
    return stream.getvalue()


def _obj_bundle_with(*, vertex: str = "v 0 0 0", color: str = "Kd 0.2 0.5 0.9") -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "packing_scene.obj",
            "\n".join(
                (
                    "o box",
                    "usemtl blue",
                    vertex,
                    "v 1 0 0",
                    "v 0 1 0",
                    "f 1 2 3",
                )
            ),
        )
        archive.writestr("packing_scene.mtl", f"newmtl blue\n{color}\n")
    return stream.getvalue()


def test_xlsx_conversion_is_bounded_and_preserves_table_values():
    converter = ValidatedReportAssetConverter()
    converted = converter.convert(
        _resolved(
            ArtifactFormat.XLSX,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            _xlsx([["Product", "Value"], ["A", "30"], ["B", "40"]]),
        ),
        views=(),
        locale="en",
    )

    assert converted.unavailable_reason is None
    assert "| Product | Value |" in converted.markdown
    assert "| B | 40 |" in converted.markdown


def test_xlsx_conversion_rejects_tables_over_the_row_limit():
    converter = ValidatedReportAssetConverter()
    converted = converter.convert(
        _resolved(
            ArtifactFormat.XLSX,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            _xlsx([["row"], *[[str(index)] for index in range(501)]]),
        ),
        views=(),
        locale="en",
    )

    assert converted.markdown is None
    assert "failed bounded report conversion" in converted.unavailable_reason


def test_obj_bundle_conversion_produces_selected_nonblank_png_views():
    converter = ValidatedReportAssetConverter()
    converted = converter.convert(
        _resolved(
            ArtifactFormat.OBJ_MTL_ZIP,
            "application/zip",
            _obj_bundle(),
        ),
        views=("front", "top"),
        locale="en",
    )

    assert [asset.asset_id for asset in converted.assets] == [
        "artifact-test-front",
        "artifact-test-top",
    ]
    assert all(asset.content.startswith(b"\x89PNG\r\n\x1a\n") for asset in converted.assets)
    assert all(len(asset.content) > 1_000 for asset in converted.assets)


def test_obj_bundle_conversion_rejects_non_finite_geometry_and_materials():
    converter = ValidatedReportAssetConverter()

    vertex = converter.convert(
        _resolved(
            ArtifactFormat.OBJ_MTL_ZIP,
            "application/zip",
            _obj_bundle_with(vertex="v nan 0 0"),
        ),
        views=("front",),
        locale="en",
    )
    material = converter.convert(
        _resolved(
            ArtifactFormat.OBJ_MTL_ZIP,
            "application/zip",
            _obj_bundle_with(color="Kd nan 0.5 0.9"),
        ),
        views=("front",),
        locale="en",
    )

    assert vertex.assets == ()
    assert material.assets == ()
    assert "failed bounded report conversion" in vertex.unavailable_reason
    assert "failed bounded report conversion" in material.unavailable_reason


def test_report_conversion_rejects_duplicate_archive_entries():
    stream = io.BytesIO()
    with pytest.warns(UserWarning, match="Duplicate name"):
        with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
            archive.writestr("packing_scene.obj", "o first\n")
            archive.writestr("packing_scene.obj", "o second\n")
            archive.writestr("packing_scene.mtl", "newmtl blue\n")
    converter = ValidatedReportAssetConverter()

    converted = converter.convert(
        _resolved(ArtifactFormat.OBJ_MTL_ZIP, "application/zip", stream.getvalue()),
        views=("front",),
        locale="en",
    )

    assert converted.assets == ()
    assert "failed bounded report conversion" in converted.unavailable_reason


def test_pandoc_backend_reports_missing_runtime_without_executing(tmp_path):
    backend = PandocTypstReportBackend(
        pandoc_executable=str(tmp_path / "missing-pandoc"),
        typst_executable=str(tmp_path / "missing-typst"),
        template_path=tmp_path / "template.typst",
    )

    diagnostic = backend.diagnostic()

    assert diagnostic.available is False
    assert diagnostic.reason == "Pandoc was not found on PATH."


def test_report_backend_assets_require_matching_media_signatures():
    with pytest.raises(ValueError, match="PNG asset is inconsistent"):
        ReportBackendAsset(
            "artifact-invalid",
            "image/png",
            ".png",
            b"not-a-png",
        )


def test_pandoc_backend_uses_fixed_template_and_returns_verified_pdf(tmp_path):
    pandoc = tmp_path / "pandoc"
    typst = tmp_path / "typst"
    template = tmp_path / "optees.typst"
    pandoc.write_text(
        """#!/usr/bin/env python3
import pathlib
import sys
if "--version" in sys.argv:
    print("pandoc-test 1")
else:
    output = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
    output.write_bytes(b"%PDF-1.7\\n% fake renderer\\n")
""",
        encoding="utf-8",
    )
    typst.write_text(
        "#!/bin/sh\nprintf 'typst-test 1\\n'\n",
        encoding="utf-8",
    )
    template.write_text("$body$\n", encoding="utf-8")
    pandoc.chmod(0o700)
    typst.chmod(0o700)
    backend = PandocTypstReportBackend(
        pandoc_executable=str(pandoc),
        typst_executable=str(typst),
        template_path=template,
    )
    progress = []

    rendered = backend.render(
        ReportBackendRequest(b"# Report\n", "Report", "en"),
        cancellation=Event(),
        progress=lambda percent, stage: progress.append((percent, stage)),
    )

    assert backend.diagnostic().available is True
    assert rendered.content.startswith(b"%PDF-")
    assert rendered.backend_id == "pandoc.typst.v1"
    assert progress[-1] == (90, "verifying_pdf")


def test_bundled_typst_template_defines_bounded_page_and_footer():
    template = (
        Path(__file__).parents[4]
        / "src"
        / "optees"
        / "assets"
        / "reports"
        / "optees.typst"
    ).read_text(encoding="utf-8")

    assert 'paper: "a4"' in template
    assert "margin:" in template
    assert "breakable: true" in template
    assert "#let horizontalrule" in template
    assert '#set image(width: 100%, height: 80mm, fit: "contain")' in template
    assert '#link("https://optees.it")' in template
    assert "#counter(page).display" in template
