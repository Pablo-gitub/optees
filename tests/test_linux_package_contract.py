from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
BUILDER = ROOT / "packaging" / "linux" / "build_deb.sh"


def test_debian_builder_registers_desktop_and_all_entry_points():
    script = BUILDER.read_text(encoding="utf-8")

    assert "/opt/optees" in script
    assert "/usr/share/applications/optees.desktop" in script
    assert "/usr/share/icons/hicolor/256x256/apps/optees.png" in script
    assert "Terminal=false" in script
    assert "ln -s /opt/optees/optees " in script
    assert "ln -s /opt/optees/optees-server " in script
    assert "ln -s /opt/optees/optees-mcp " in script
    assert "dpkg-deb --root-owner-group --build" in script
    assert "libxcb-cursor0" in script
    assert "libxcb-xinerama0" in script


def test_release_builds_smoke_tests_and_publishes_debian_package():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Build Debian package (Linux)" in workflow
    assert "Smoke test Debian package payload (Linux)" in workflow
    assert "optees-linux-x86_64.deb" in workflow
    assert "Upload Debian package" in workflow


def test_windows_release_still_builds_and_prefers_native_setup():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Build Windows installer" in workflow
    assert "optees-windows-x64-setup.exe" in workflow
    assert 'name: optees-windows-x64-portable.zip' in workflow
