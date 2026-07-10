from __future__ import annotations

from pathlib import Path
import tomllib

from optees import __version__
from optees.core.build_metadata import macos_info_plist


def test_macos_bundle_metadata_uses_the_application_version():
    metadata = macos_info_plist()

    assert metadata["CFBundleVersion"] == __version__
    assert metadata["CFBundleShortVersionString"] == __version__
    assert metadata["CFBundleName"] == "Optees"
    assert metadata["LSMinimumSystemVersion"] == "13.0"


def test_pyinstaller_spec_uses_shared_macos_metadata():
    spec = Path("optees.spec").read_text(encoding="utf-8")

    assert "_project_root = Path(SPECPATH).resolve()" in spec
    assert "from optees.core.build_metadata import macos_info_plist" in spec
    assert "info_plist=macos_info_plist()" in spec


def test_project_declares_the_milp_runtime_backend():
    with Path("pyproject.toml").open("rb") as manifest:
        project = tomllib.load(manifest)["project"]

    assert "ortools" in project["dependencies"]
