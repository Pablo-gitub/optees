# tests/conftest.py
import os
import pytest

# headless Qt + Matplotlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("OPTEES_DISABLE_UPDATE_CHECK", "1")

from optees.application.usecases.solve_lp_usecase import SolveLPUseCase

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
