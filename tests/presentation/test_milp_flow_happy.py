import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox

from _utils.fakes import FakeSolver
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus


def test_milp_flow_solves_and_navigates_to_solution(window, qtbot):
    fake = FakeSolver({
        "status": "Feasible",
        "objective": 10.0,
        "x": {"X1": 1.0, "X2": 0.0},
        "extras": {
            "backend": "stub",
            "best_bound": 9.0,
            "relative_gap": 0.1,
            "message": "incumbent found",
        },
    })
    window.milp_page.set_solve_usecase(SolveMILPUseCase(fake))

    ctrl = window.milp_controller
    ctrl.set_integrality(0, "B")
    ctrl.set_integrality(1, "I")
    ctrl.set_objective_sense("max")
    ctrl.set_objective_coef(0, 10.0)
    ctrl.set_objective_coef(1, 1.0)
    ctrl.set_constraint_coef(0, 0, 1.0)
    ctrl.set_constraint_coef(0, 1, 1.0)
    ctrl.set_constraint_rel(0, "<=")
    ctrl.set_constraint_rhs(0, 1.0)

    window.milp_page.solver_sec.edit_time.setText("3.5")
    window.milp_page.solver_sec.edit_gap.setText("0.05")

    with qtbot.waitSignal(window.milp_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.milp_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.status is MILPSolveStatus.FEASIBLE
    assert solution.objective == pytest.approx(10.0)
    assert solution.values == {"X1": 1.0, "X2": 0.0}

    assert fake.last_problem["sense"] == "max"
    assert fake.last_problem["integrality"] == ["B", "I"]
    assert fake.last_problem["bounds"][0] == (0.0, 1.0)
    assert fake.last_problem["time_limit"] == pytest.approx(3.5)
    assert fake.last_problem["mip_gap"] == pytest.approx(0.05)

    assert window.stack.currentWidget() is window.milp_solution_page
    assert window.milp_solution_page.solution_table.model().rowCount() == 3


def test_milp_variable_type_combo_exposes_boolean_choice(window):
    combos = window.milp_page.vars_sec.findChildren(QComboBox, "milpIntegralityCombo")

    assert combos
    items = [
        (combos[0].itemText(i), combos[0].itemData(i))
        for i in range(combos[0].count())
    ]
    boolean_items = [text for text, data in items if data == "B"]

    assert boolean_items
    assert "0/1" in boolean_items[0]
