from __future__ import annotations

from pathlib import Path
import tomllib

from optees import __version__
from optees.core.build_metadata import macos_info_plist, windows_version_info_text
from optees.core.release_version import display_release_version, numeric_release_version


def test_macos_bundle_metadata_uses_the_application_version():
    metadata = macos_info_plist()

    assert metadata["CFBundleVersion"] == numeric_release_version(__version__)
    assert metadata["CFBundleShortVersionString"] == numeric_release_version(__version__)
    assert display_release_version(__version__) in metadata["CFBundleGetInfoString"]
    assert metadata["CFBundleName"] == "Optees"
    assert metadata["LSMinimumSystemVersion"] == "13.0"


def test_pyinstaller_spec_uses_shared_macos_metadata():
    spec = Path("optees.spec").read_text(encoding="utf-8")

    assert "_project_root = Path(SPECPATH).resolve()" in spec
    assert "from optees.core.build_metadata import macos_info_plist" in spec
    assert "info_plist=macos_info_plist()" in spec


def test_windows_executable_metadata_uses_the_application_version():
    metadata = windows_version_info_text()

    display_version = display_release_version(__version__)
    assert f"StringStruct('FileVersion', '{display_version}')" in metadata
    assert f"StringStruct('ProductVersion', '{display_version}')" in metadata
    assert "StringStruct('OriginalFilename', 'optees.exe')" in metadata


def test_pyinstaller_spec_generates_windows_version_metadata():
    spec = Path("optees.spec").read_text(encoding="utf-8")

    assert "windows_version_info_text" in spec
    assert 'version=str(_version_file) if _version_file is not None else None' in spec


def test_project_declares_the_milp_runtime_backend():
    with Path("pyproject.toml").open("rb") as manifest:
        project = tomllib.load(manifest)["project"]

    assert "ortools" in project["dependencies"]
