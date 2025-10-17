# tests/presentation/test_lp_flow_notsolved.py
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from _utils.fakes import FakeSolver
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt


def test_notsolved_shows_message_placeholder(window, qtbot):
    fake = FakeSolver({
        "status": "NotSolved",
        "objective": None,
        "x": {},
        "extras": {"method": "highs", "message": "SciPy missing"},
    })
    window.lp_page.set_solve_usecase(SolveLPUseCase(fake))
    ctrl = window.lp_controller
    ctrl.add_variable()

    with qtbot.waitSignal(window.lp_page.solve_completed, timeout=1000):
        qtbot.mouseClick(window.lp_page.btn_optimize, Qt.LeftButton)

    # verify message in status card
    lbl = (window.lp_solution_page.findChild(QLabel, "solverMsg")
           or getattr(getattr(window.lp_solution_page, "status", None), "msg", None))
    assert lbl is not None
    # if shoews a placeholder for plot
    ph = window.lp_solution_page.findChild(QWidget, "plotPlaceholder")
    assert ph is not None
