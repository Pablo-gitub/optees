# tests/presentation/test_lp_flow_infeasible.py
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from _utils.fakes import FakeSolver
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt

def test_infeasible_shows_badge_and_empty_table(window, qtbot):
    fake = FakeSolver({
        "status": "Infeasible",
        "objective": None,
        "x": {},
        "extras": {"method": "highs", "message": "infeasible"},
    })
    window.lp_page.set_solve_usecase(SolveLPUseCase(fake))

    # enoudh to have some variables for clicking optimize
    ctrl = window.lp_controller
    ctrl.add_variable(); ctrl.add_variable()

    with qtbot.waitSignal(window.lp_page.solve_completed, timeout=1000):
        qtbot.mouseClick(window.lp_page.btn_optimize, Qt.LeftButton)

    # stays on solution page
    assert window.stack.currentWidget() is window.lp_solution_page

    # badge/label state (assume objectName "statusBadge")
    badge = (window.lp_solution_page.findChild(QLabel, "statusBadge")
          or getattr(getattr(window.lp_solution_page, "status", None), "badge", None))
    assert badge is not None
    # alternatively, read one text label with localized status
    # table empty
    table = window.lp_solution_page.solution_table
    assert table.model().rowCount() == 0
