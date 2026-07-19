from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_linux_ci_groups_install_the_qt_runtime_before_pytest_collection():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert workflow.count("sudo apt-get install -y libgl1-mesa-glx libegl1") == 3
