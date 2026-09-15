from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_linux_ci_groups_install_the_qt_runtime_before_pytest_collection():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert workflow.count("sudo apt-get install -y libgl1-mesa-glx libegl1") == 3


def test_python_distribution_ci_covers_supported_platforms_and_profiles():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "python-distribution:" in workflow
    assert "ubuntu-22.04" in workflow
    assert "windows-latest" in workflow
    assert "macos-14" in workflow
    assert "packaging/validate_python_distribution.py" in workflow
    assert "--rebuild-sdist" in workflow
    assert "smoke_python_distribution.py core" in workflow
    assert "for profile in local-service mcp desktop all" in workflow
    assert 'smoke_python_distribution.py "${profile}"' in workflow
