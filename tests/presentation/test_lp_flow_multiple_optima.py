# tests/presentation/test_lp_flow_multiple_optima.py
import pytest
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from _utils.fakes import FakeSolver
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from PySide6.QtWidgets import QLabel
from optees.presentation.views.lp_solution_view.status_card import StatusCard
from optees.core.string_manager import strings as S

def test_multiple_optima_note_is_shown(window, qtbot):
    # Fake solver: ottimo con alt_opt che segnala molteplici soluzioni
    fake = FakeSolver({
        "status": "Optimal",
        "objective": 3.0,
        "x": {"X1": 0.0, "X2": 3.0},
        "extras": {
            "method": "highs",
            "nit": 5,
            "message": "OK",
            # <<< chiave: simuliamo ciò che _postprocess_result produrrebbe
            "alt_opt": {
                "has_alternate_optimum": True,
                "varying_variables": ["X1", "X2"],
                "ranges": {
                    "X1": {"min": 0.0, "max": 3.0, "width": 3.0, "is_fixed": False},
                    "X2": {"min": 0.0, "max": 3.0, "width": 3.0, "is_fixed": False},
                },
                "extreme_points": {
                    "A": {"X1": 0.0, "X2": 3.0},
                    "B": {"X1": 3.0, "X2": 0.0},
                },
            },
            "var_names": ["X1", "X2"],
        },
    })
    uc = SolveLPUseCase(fake)
    window.lp_page.set_solve_usecase(uc)

    # Modello semplice che ammette molteplici ottimi:
    # max x1 + x2  s.t.  x1 + x2 <= 3, x >= 0
    ctrl = window.lp_controller
    ctrl.set_objective_sense("max")
    ctrl.set_objective_coef(0, 1.0)
    ctrl.set_objective_coef(1, 1.0)

    ctrl.add_constraint()
    ctrl.set_constraint_coef(0, 0, 1.0)
    ctrl.set_constraint_coef(0, 1, 1.0)
    ctrl.set_constraint_rel(0, "<=")
    ctrl.set_constraint_rhs(0, 3.0)

    # Act
    with qtbot.waitSignal(window.lp_page.solve_completed, timeout=1000):
        qtbot.mouseClick(window.lp_page.btn_optimize, Qt.LeftButton)

    # Assert: siamo sulla solution page
    assert window.stack.currentWidget() is window.lp_solution_page

    card = window.lp_solution_page.findChild(StatusCard)
    assert card is not None, "StatusCard not found in solution page"

    note_label = card.findChild(QLabel, "optNote")
    assert note_label is not None, "Label 'optNote' not found in StatusCard"

    # Read the note from the found QLabel instead of accessing private attributes
    note = note_label.text().lower().strip()

    # normalize to be language-independent
    # we check for keywords that appear in either translation
    keywords = [
        "infiniti ottimi",      # Italian
        "infinite optimal",     # English
        "optimal variable ranges",  # English range form
        "intervalli ottimi"     # Italian range form
    ]

    assert any(k in note for k in keywords), \
        f"Expected note to mention multiple optima, got: {note!r}"


    # Additional structural checks (unchanged)
    assert "[" in note and "]" in note        # compact range representation
    assert "x1" in note and "x2" in note
    assert "0" in note and "3" in note        # expected ranges [0, 3]

    # Read the meta line via its objectName 'solverMsg'
    meta_label = card.findChild(QLabel, "solverMsg")
    assert meta_label is not None, "Label 'solverMsg' not found in StatusCard"
    meta = meta_label.text()
    assert "X1" in meta and "X2" in meta
