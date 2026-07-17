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
