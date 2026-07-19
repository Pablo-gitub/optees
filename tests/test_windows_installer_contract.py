from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_inno_setup_is_per_user_and_has_stable_identity():
    script = (ROOT / "packaging/windows/optees.iss").read_text(encoding="utf-8")

    assert "AppId={{7B07EED7-C851-4B42-B0DC-184BF7793D6A}" in script
    assert "DefaultDirName={localappdata}\\Programs\\Optees" in script
    assert "PrivilegesRequired=lowest" in script
    assert "UninstallDisplayIcon={app}\\{#AppExecutable}" in script
    assert "VersionInfoVersion={#AppNumericVersion}" in script
    assert 'Name: "{group}\\Optees"' in script
    assert 'Name: "desktopicon"' in script
    assert "Flags: unchecked" in script


def test_release_builds_native_and_explicit_portable_windows_artifacts():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "choco install innosetup --version=6.7.1" in workflow
    assert "Validate release tag against application version" in workflow
    assert '"/DAppVersion=$version"' in workflow
    assert '"/DAppNumericVersion=$numericVersion"' in workflow
    assert "packaging\\windows\\optees.iss" in workflow
    assert "optees-windows-x64-setup.exe" in workflow
    assert "optees-windows-x64-portable.zip" in workflow
