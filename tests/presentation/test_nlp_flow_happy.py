from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton

from _utils.fakes import FakeSolver
from optees.application.usecases.solve_nlp_usecase import SolveNLPUseCase
from optees.core.string_manager import strings as S
from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.models.nlp.nlp_model import NLPModel, NLPOptions
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.domain.value_objects.nlp.solve_status import NLPSolveStatus


def test_home_card_opens_nlp_page(window, qtbot) -> None:
    assert window.home_page.card_nlp.parentWidget() is window.home_page.cat_nlp
    assert window.home_page.cat_nlp.parentWidget() is not None

    qtbot.mouseClick(window.home_page.card_nlp, Qt.LeftButton)

    assert window.stack.currentWidget() is window.nlp_page


def test_nlp_form_solves_and_navigates_to_local_solution(window, qtbot) -> None:
    fake = FakeSolver(
        {
            "status": "Converged",
            "objective": 0.0,
            "x": {"x1": 2.0, "x2": -1.0},
            "extras": {
                "method": "BFGS",
                "iterations": 4,
                "evaluations": 7,
                "message": "gradient tolerance reached",
                "convergence_history": [5.0, 1.2, 0.0],
            },
        }
    )
    window.nlp_page.set_solve_usecase(SolveNLPUseCase(fake))
    window.goto("nlp")

    rows = window.nlp_page.variables_section.rows()
    rows[0].edit_initial.setText("0")
    rows[1].edit_initial.setText("0")
    window.nlp_page.edit_expression.setText("(x1 - 2)**2 + (x2 + 1)**2")

    with qtbot.waitSignal(window.nlp_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.nlp_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]
    assert solution.status is NLPSolveStatus.CONVERGED
    assert fake.last_problem == {
        "sense": "min",
        "expression": "(x1 - 2)**2 + (x2 + 1)**2",
        "variables": ["x1", "x2"],
        "initial_point": [0.0, 0.0],
        "bounds": [(None, None), (None, None)],
        "method": "BFGS",
        "max_iterations": 1000,
        "tolerance": pytest.approx(1e-8),
    }
    assert window.stack.currentWidget() is window.nlp_solution_page
    assert window.nlp_solution_page.candidate_table.rowCount() == 2
    assert window.nlp_solution_page.trace_table.rowCount() == 3
    assert window.nlp_solution_page.status.text()
    assert (
        window.nlp_solution_page.detail_labels["feasibility"].text()
        == S.t("nlp.solution.feasibility.within_bounds")
    )


def test_bounds_select_lbfgsb_before_the_model_is_built(window, qtbot) -> None:
    window.goto("nlp")
    row = window.nlp_page.variables_section.rows()[0]
    row.edit_lower.setText("0")
    combo = window.nlp_page.findChild(QComboBox, "nlpSolverMethod")

    assert combo is not None
    assert combo.currentData() == "L-BFGS-B"
    assert "L-BFGS-B" in window.nlp_page.method_hint.text()


def test_nlp_json_import_populates_the_form(window, qtbot, monkeypatch, tmp_path) -> None:
    data = {
        "version": "1",
        "problem_type": "nonlinear_programming",
        "variables": [
            {"name": "x1", "label": "coordinate", "lb": 0, "ub": 2, "initial": 0.5}
        ],
        "objective": {"sense": "min", "expression": "(x1 - 2)**2"},
        "solver_options": {"method": "L-BFGS-B", "max_iterations": 50, "tolerance": 1e-7},
    }
    path = tmp_path / "nlp.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.nlp_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    window.goto("nlp")

    qtbot.mouseClick(window.nlp_page.btn_import_json, Qt.LeftButton)

    rows = window.nlp_page.variables_section.rows()
    assert len(rows) == 1
    assert rows[0].edit_name.text() == "x1"
    assert rows[0].edit_lower.text() == "0"
    assert rows[0].edit_upper.text() == "2"
    assert rows[0].edit_initial.text() == "0.5"
    assert window.nlp_page.edit_expression.text() == "(x1 - 2)**2"
    method = window.nlp_page.findChild(QComboBox, "nlpSolverMethod")
    assert method is not None and method.currentData() == "L-BFGS-B"
    assert window.nlp_page.findChild(QLineEdit, "nlpMaxIterations").text() == "50"


def test_nlp_view_uses_localized_controls(window) -> None:
    window.goto("nlp")

    assert window.nlp_page.findChild(QPushButton, "nlpImportJsonButton").text()
    assert window.nlp_page.findChild(QPushButton, "nlpOptimizeButton").text()
    assert window.nlp_page.findChild(QLineEdit, "nlpObjectiveExpression").placeholderText()


@pytest.mark.parametrize("language", ["en", "it"])
def test_nlp_view_retranslates_in_each_supported_language(window, language: str) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        assert window.nlp_page.btn_optimize.text() == S.t("nlp.actions.optimize")
        assert window.nlp_page.btn_import_json.text() == S.t("nlp.import.button")
        assert "nlp." not in window.nlp_page.title.text()
    finally:
        S.set_language(previous)


@pytest.mark.parametrize(
    ("status", "history", "expected_status_key"),
    [
        ("IterationLimit", (), "nlp.solution.status.iteration_limit"),
        ("Failed", (), "nlp.solution.status.failed"),
    ],
)
def test_nlp_solution_explains_non_converged_runs(
    window,
    status: str,
    history: tuple[float, ...],
    expected_status_key: str,
) -> None:
    model = NLPModel.from_parts(
        variables=[NLPVariable("x1", lower_bound=0.0, upper_bound=1.0, initial_value=0.5)],
        objective=NLPObjective("(x1 - 1)**2"),
        options=NLPOptions(method=NLPSolverMethod.L_BFGS_B),
    )
    solution = NLPSolution.from_solver_result(
        status=status,
        objective=0.25 if status == "IterationLimit" else None,
        values={"x1": 0.5} if status == "IterationLimit" else {},
        extras={"method": "L-BFGS-B", "message": "stopped", "convergence_history": history},
    )

    window.nlp_solution_page.set_problem(model)
    window.nlp_solution_page.set_solution(solution)

    assert S.t(expected_status_key) in window.nlp_solution_page.status.text()
    assert window.nlp_solution_page.trace_table.rowCount() == 0
    assert window.nlp_solution_page.trace_hint.text() == S.t("nlp.solution.trace.empty")
