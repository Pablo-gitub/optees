# tests/conftest.py
import os
import pytest

# headless Qt + Matplotlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("OPTEES_DISABLE_UPDATE_CHECK", "1")

from optees.application.usecases.solve_lp_usecase import SolveLPUseCase


_MEASURED_BENCHMARK_FILES = {
    "tests/utility/test_io_knapsack_param.py",
    "tests/utility/test_miplib_milp_e2e.py",
}


def pytest_collection_modifyitems(config, items) -> None:
    """Classify tests by stable ownership boundaries, not naming guesses."""

    root = config.rootpath
    for item in items:
        relative = item.path.relative_to(root).as_posix()
        if relative.startswith("tests/presentation/"):
            item.add_marker(pytest.mark.gui)
        if relative in _MEASURED_BENCHMARK_FILES:
            item.add_marker(pytest.mark.benchmark)
        if relative.endswith("_tcp_e2e.py"):
            item.add_marker(pytest.mark.tcp)


@pytest.fixture
def window(qtbot):
    pytest.importorskip("PySide6")
    from optees.presentation.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    return w

@pytest.fixture
def controller(window):
    # return the LPController associated with the main window
    return window.lp_controller
