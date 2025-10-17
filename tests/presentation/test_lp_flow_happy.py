# tests/presentation/test_lp_flow_happy.py
import pytest
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from _utils.fakes import FakeSolver
from PySide6.QtCore import Qt

def test_happy_flow_optimize_navigates_and_populates(window, qtbot):
    # Arrange: Fake solver with an optimal solution
    fake = FakeSolver({
        "status": "Optimal",
        "objective": 8.0,
        "x": {"X1": 2.0, "X2": 1.0},
        "extras": {"method": "highs", "nit": 7, "message": "OK"},
    })
    uc = SolveLPUseCase(fake)
    window.lp_page.set_solve_usecase(uc)

    # We build a model with 2 variables and 3 constraints
    ctrl = window.lp_controller
    ctrl.add_variable(); ctrl.add_variable()
    ctrl.set_objective_sense("max")
    ctrl.set_objective_coef(0, 3.0)   # 3 * x1
    ctrl.set_objective_coef(1, 2.0)   # + 2 * x2
    # 2x1 + 1x2 <= 6
    ctrl.add_constraint()
    ctrl.set_constraint_coef(0, 0, 2.0)
    ctrl.set_constraint_coef(0, 1, 1.0)
    ctrl.set_constraint_rel(0, "<=")
    ctrl.set_constraint_rhs(0, 6.0)
    # x1 - x2 <= 1
    ctrl.add_constraint()
    ctrl.set_constraint_coef(1, 0, 1.0)
    ctrl.set_constraint_coef(1, 1, -1.0)
    ctrl.set_constraint_rel(1, "<=")
    ctrl.set_constraint_rhs(1, 1.0)
    # x1 + x2 <= 3
    ctrl.add_constraint()
    ctrl.set_constraint_coef(2, 0, 1.0)
    ctrl.set_constraint_coef(2, 1, 1.0)
    ctrl.set_constraint_rel(2, "<=")
    ctrl.set_constraint_rhs(2, 3.0)

    # Act: click "Optimize" and wait the signal
    with qtbot.waitSignal(window.lp_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.lp_page.btn_optimize, Qt.LeftButton)

    result = blocker.args[0]
    # Assert 1: result from signal
    assert result.status == "Optimal"
    assert result.objective == 8.0
    assert result.values == {"X1": 2.0, "X2": 1.0}

    # Assert 2: MainController go to solution view
    assert window.stack.currentWidget() is window.lp_solution_page

    # Assert 3: la solution view show two rows 
    table = window.lp_solution_page.solution_table
    model = table.model()
    assert model.rowCount() == 2
    # optional: check first row content
    idx0 = model.index(0, 0)
    idx1 = model.index(0, 1)
    assert model.data(idx0) == "X1"
    assert pytest.approx(float(model.data(idx1))) == 2.0
