from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_build_installs_and_smoke_tests_local_service_extra():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'pip install ".[plot,local-service,mcp]"' in workflow
    assert workflow.count("Smoke test packaged local service") == 3
    assert "/api/v1/capabilities" in workflow


def test_pyinstaller_dispatches_the_headless_server_entrypoint():
    spec = (ROOT / "optees.spec").read_text(encoding="utf-8")
    main = (ROOT / "src/optees/main.py").read_text(encoding="utf-8")

    assert '"optees.local_server"' in spec
    assert 'arguments[0] == "--local-server"' in main
    assert 'arguments[0] == "--mcp-server"' in main


def test_windows_bundle_has_a_diagnostic_headless_companion():
    spec = (ROOT / "optees.spec").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'name="optees-server"' in spec
    assert "console=True" in spec
    assert "dist\\optees\\optees-server.exe" in workflow
    assert "RedirectStandardError" in workflow
    assert "if ($server.HasExited)" in workflow


def test_windows_entrypoints_are_selected_by_path_not_toc_position():
    spec = (ROOT / "optees.spec").read_text(encoding="utf-8")

    assert "_main_entry" in spec
    assert "_server_entry" in spec
    assert "_server_scripts" in spec
    assert "[a.scripts[" not in spec


def test_native_bundles_include_and_smoke_test_mcp_companion():
    spec = (ROOT / "optees.spec").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert '"src/optees/mcp_server.py"' in spec
    assert 'name="optees-mcp"' in spec
    assert "_mcp_entry" in spec
    assert "_mcp_scripts" in spec
    assert workflow.count("Smoke test packaged MCP companion") == 3
    assert "packaging/smoke_mcp.py" in workflow
    assert "dist\\optees\\optees-mcp.exe" in workflow
    assert "dist/optees.app/Contents/MacOS/optees-mcp" in workflow
    smoke = (ROOT / "packaging/smoke_mcp.py").read_text(encoding="utf-8")
    assert '"optees_create_job"' in smoke
    assert '"lp.continuous"' in smoke
    assert '"mathematical_status") != "optimal"' in smoke


def test_final_appimage_dispatches_and_smoke_tests_mcp():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'if [[ "${1:-}" == "--mcp-server" ]]' in workflow
    assert 'exec "${HERE}/optees-mcp" "$@"' in workflow
    assert "Smoke test final AppImage MCP entry point" in workflow
    assert "./optees-linux-x86_64.AppImage --mcp-server" in workflow


def test_native_bundles_smoke_test_artifact_and_report_workflow():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    smoke_path = ROOT / "packaging" / "smoke_packaged_reporting.py"
    smoke = smoke_path.read_text(encoding="utf-8")

    assert workflow.count("Smoke test packaged artifact reporting") == 3
    assert workflow.count("packaging/smoke_packaged_reporting.py") == 3
    assert workflow.count("Verify packaged report template") == 3
    assert "solution_table" in smoke
    assert "feasible_region" in smoke
    assert "/api/v1/reports/backends" in smoke
    assert "Optees · optees.it" in smoke
    assert 'pdf.startswith(b"%PDF-")' in smoke
    assert "x-content-sha256" in smoke
