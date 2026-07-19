from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_build_installs_and_smoke_tests_local_service_extra():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'pip install ".[plot,local-service]"' in workflow
    assert workflow.count("Smoke test packaged local service") == 3
    assert "/api/v1/capabilities" in workflow


def test_pyinstaller_dispatches_the_headless_server_entrypoint():
    spec = (ROOT / "optees.spec").read_text(encoding="utf-8")
    main = (ROOT / "src/optees/main.py").read_text(encoding="utf-8")

    assert '"optees.local_server"' in spec
    assert 'arguments[0] == "--local-server"' in main


def test_windows_bundle_has_a_diagnostic_headless_companion():
    spec = (ROOT / "optees.spec").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'name="optees-server"' in spec
    assert "console=True" in spec
    assert "dist\\optees\\optees-server.exe" in workflow
    assert "RedirectStandardError" in workflow
    assert "if ($server.HasExited)" in workflow
