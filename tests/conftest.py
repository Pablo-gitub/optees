# tests/conftest.py
import os
import pytest

# headless Qt + Matplotlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

from optees.presentation.main_window import MainWindow
from optees.presentation.controllers.lp_controller import LPController
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase

@pytest.fixture
def window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    return w

@pytest.fixture
def controller(window) -> LPController:
    # return the LPController associated with the main window
    return window.lp_controller
