from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton

from _utils.fakes import FakeSolver
from optees.application.usecases.solve_qp_usecase import SolveQPUseCase
from optees.application.validation.qp_solution_validator import QPIndependentSolutionValidator
from optees.core.string_manager import strings as S
from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.solution import QPSolution
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.models.qp.qp_model import QPModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus


def _boundary_model() -> QPModel:
    """The contract's boundary-optimum reference case: x* = (1, 1), f = 1."""
    return QPModel.from_parts(
        variables=[
            QPVariable("x1", label="X1", bounds=Bounds(0.0, None)),
            QPVariable("x2", label="X2", bounds=Bounds(0.0, None)),
        ],
        objective=QPObjective(
            sense=ObjectiveSense.MIN,
            linear_coefs=(0.0, 0.0),
            quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
            offset=0.0,
        ),
        constraints=[QPConstraint("sum_bound", (1.0, 1.0), Relation.GE, 2.0)],
    )


def _optimal_solution() -> QPSolution:
    return QPSolution.from_solver_result(
        status="Optimal",
        objective=1.0,
        values={"x1": 1.0, "x2": 1.0},
        extras={
            "backend": "osqp",
            "backend_version": "0.6.7.post3",
            "status": "solved",
            "iterations": 25,
            "solve_time_seconds": 0.001,
            "success": True,
        },
    )


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


def test_home_card_opens_qp_page(window, qtbot) -> None:
    assert window.home_page.card_qp.parentWidget() is window.home_page.cat_nlp

    qtbot.mouseClick(window.home_page.card_qp, Qt.LeftButton)

    assert window.stack.currentWidget() is window.qp_page


def test_toolbar_groups_nonlinear_actions(window) -> None:
    assert window.drop_nonlinear.menu() is not None
    assert window.drop_nonlinear.menu().actions() == [window.act_nlp, window.act_qp]

    window.act_qp.trigger()

    assert window.stack.currentWidget() is window.qp_page


# ---------------------------------------------------------------------------
# Formulation and solve
# ---------------------------------------------------------------------------


def test_default_form_solves_and_navigates_to_the_result(window, qtbot) -> None:
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 1.0,
            "x": {"x1": 1.0, "x2": 1.0},
            "dual_values": {
                "constraints": [1.0],
                "lower_bounds": [0.0, 0.0],
                "upper_bounds": [0.0, 0.0],
            },
            "kkt_residuals": {"primal_residual": 1e-10, "dual_residual": 2e-10},
            "extras": {"backend": "osqp", "backend_version": "0.6.7.post3", "status": "solved"},
        }
    )
    window.qp_page.set_solve_usecase(SolveQPUseCase(fake))
    window.goto("qp")

    with qtbot.waitSignal(window.qp_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.qp_page.btn_solve, Qt.LeftButton)

    solution = blocker.args[0]
    assert solution.status is QPSolveStatus.OPTIMAL
    assert fake.last_problem["sense"] == "min"
    assert fake.last_problem["variables"] == ["x1", "x2"]
    assert fake.last_problem["Q"] == [[1.0, 0.0], [0.0, 1.0]]
    assert fake.last_problem["c"] == [0.0, 0.0]
    assert fake.last_problem["bounds"] == [(0.0, None), (0.0, None)]
    assert fake.last_problem["constraints"] == [
        {"name": "sum_bound", "coefs": [1.0, 1.0], "relation": ">=", "rhs": 2.0}
    ]
    assert fake.last_problem["options"]["method"] == "osqp"

    assert window.stack.currentWidget() is window.qp_solution_page
    assert window.qp_solution_page.variables_table.rowCount() == 2
    assert window.qp_solution_page.variables_table.item(0, 0).text() == "x1"
    assert window.qp_solution_page.constraints_table.rowCount() == 1
    assert window.qp_solution_page.duals_table.rowCount() == 5
    assert S.t("qp.solution.status.optimal") in window.qp_solution_page.status.text()


def test_matrix_editor_keeps_the_hessian_symmetric(window) -> None:
    window.goto("qp")
    table = window.qp_page.matrix_table

    table.item(0, 1).setText("0.5")

    assert table.item(1, 0).text() == "0.5"
    model = window.qp_page.current_model()
    assert model.objective.quadratic_matrix == ((1.0, 0.5), (0.5, 1.0))


def test_adding_a_variable_rebinds_matrix_and_constraint_columns(window, qtbot) -> None:
    window.goto("qp")

    qtbot.mouseClick(window.qp_page.findChild(QPushButton, "qpAddVariableButton"), Qt.LeftButton)

    assert len(window.qp_page.variables_section.rows()) == 3
    assert window.qp_page.matrix_table.rowCount() == 3
    assert window.qp_page.matrix_table.columnCount() == 3
    assert window.qp_page.linear_table.columnCount() == 3
    # name + one column per variable + relation + right-hand side
    assert window.qp_page.constraints_table.columnCount() == 6
    model = window.qp_page.current_model()
    assert len(model.objective.linear_coefs) == 3
    assert len(model.constraints[0].coefs) == 3


def test_adding_and_removing_constraints(window, qtbot) -> None:
    window.goto("qp")
    add = window.qp_page.findChild(QPushButton, "qpAddConstraintButton")

    qtbot.mouseClick(add, Qt.LeftButton)

    assert window.qp_page.constraints_table.rowCount() == 2
    assert len(window.qp_page.current_model().constraints) == 2

    qtbot.mouseClick(window.qp_page.findChild(QPushButton, "qpRemoveConstraintButton"), Qt.LeftButton)

    assert window.qp_page.constraints_table.rowCount() == 1


def test_non_convex_matrix_is_refused_with_a_localized_message(window, monkeypatch) -> None:
    window.goto("qp")
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "optees.presentation.views.qp_view.QMessageBox.warning",
        lambda _parent, title, body: captured.update(title=title, body=body),
    )
    # Eigenvalues 3 and -1: an indefinite saddle, rejected before solving.
    window.qp_page.matrix_table.item(0, 1).setText("2")
    window.qp_page.matrix_table.item(0, 0).setText("1")
    window.qp_page.matrix_table.item(1, 1).setText("1")

    window.qp_page._on_solve()

    assert captured["title"] == S.t("qp.validation.title")
    assert S.t("error_feedback.qp.curvature") in captured["body"]


# ---------------------------------------------------------------------------
# Import and export
# ---------------------------------------------------------------------------


def test_json_import_populates_the_form(window, qtbot, monkeypatch, tmp_path) -> None:
    data = {
        "capability_id": "qp.continuous",
        "problem_type": "quadratic_programming",
        "variables": [
            {"name": "a", "label": "Asset A", "lower_bound": 0.0, "upper_bound": 1.0},
            {"name": "b", "label": "Asset B", "lower_bound": 0.0, "upper_bound": None},
        ],
        "objective": {
            "sense": "min",
            "linear_coefs": [-4.0, -6.0],
            "quadratic_matrix": [[2.0, 1.0], [1.0, 2.0]],
            "offset": 1.5,
        },
        "constraints": [
            {"name": "budget", "coefs": [1.0, 1.0], "relation": "<=", "rhs": 1.0}
        ],
        "options": {"method": "osqp", "tolerance": 1e-6, "max_iterations": 500},
    }
    path = tmp_path / "qp.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.qp_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    window.goto("qp")

    qtbot.mouseClick(window.qp_page.btn_import_json, Qt.LeftButton)

    rows = window.qp_page.variables_section.rows()
    assert [row.edit_name.text() for row in rows] == ["a", "b"]
    assert rows[0].edit_upper.text() == "1"
    assert rows[1].edit_upper.text() == ""
    assert window.qp_page.matrix_table.item(0, 1).text() == "1"
    assert window.qp_page.linear_table.item(0, 0).text() == "-4"
    assert window.qp_page.edit_offset.text() == "1.5"
    assert window.qp_page.constraints_table.rowCount() == 1
    assert window.qp_page.findChild(QLineEdit, "qpMaxIterations").text() == "500"


def test_import_then_solve_matches_a_manually_entered_model(window, qtbot, monkeypatch, tmp_path):
    """The imported and hand-entered forms must reach the use case identically."""
    window.goto("qp")
    manual = FakeSolver({"status": "Optimal", "objective": 1.0, "x": {"x1": 1.0, "x2": 1.0}})
    window.qp_page.set_solve_usecase(SolveQPUseCase(manual))
    qtbot.mouseClick(window.qp_page.btn_solve, Qt.LeftButton)
    manual_problem = manual.last_problem

    path = tmp_path / "roundtrip.json"
    from optees.utility.qp_json_io import qp_model_to_json

    path.write_text(qp_model_to_json(window.qp_page.current_model()), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.qp_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    qtbot.mouseClick(window.qp_page.btn_import_json, Qt.LeftButton)

    imported = FakeSolver({"status": "Optimal", "objective": 1.0, "x": {"x1": 1.0, "x2": 1.0}})
    window.qp_page.set_solve_usecase(SolveQPUseCase(imported))
    qtbot.mouseClick(window.qp_page.btn_solve, Qt.LeftButton)

    assert imported.last_problem == manual_problem


def test_export_writes_an_importable_document(window, qtbot, monkeypatch, tmp_path) -> None:
    window.goto("qp")
    path = tmp_path / "exported.json"
    monkeypatch.setattr(
        "optees.presentation.views.qp_view.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(path), ""),
    )

    qtbot.mouseClick(window.qp_page.btn_export_json, Qt.LeftButton)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["capability_id"] == "qp.continuous"
    assert payload["objective"]["quadratic_matrix"] == [[1.0, 0.0], [0.0, 1.0]]

    from optees.utility.qp_json_io import qp_model_from_dict

    assert qp_model_from_dict(payload).variable_names() == ("x1", "x2")


def test_invalid_import_reports_a_localized_error(window, qtbot, monkeypatch, tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('{"variables": []}', encoding="utf-8")
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "optees.presentation.views.qp_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    monkeypatch.setattr(
        "optees.presentation.views.qp_view.QMessageBox.warning",
        lambda _parent, title, body: captured.update(title=title, body=body),
    )
    window.goto("qp")

    qtbot.mouseClick(window.qp_page.btn_import_json, Qt.LeftButton)

    assert captured["title"] == S.t("qp.import.error_title")
    assert S.t("error_feedback.import.schema") in captured["body"]


# ---------------------------------------------------------------------------
# Result presentation
# ---------------------------------------------------------------------------


def test_result_view_separates_status_objective_and_validation(window) -> None:
    model = _boundary_model()
    solution = QPSolution.from_solver_result(
        status="Optimal",
        objective=1.0,
        values={"x1": 1.0, "x2": 1.0},
        extras={
            "backend": "osqp",
            "backend_version": "0.6.7.post3",
            "status": "solved",
            "iterations": 25,
        },
    )
    view = window.qp_solution_page
    view.set_problem(model)
    view.set_solution(solution)
    view.set_validation(None)

    assert S.t("qp.solution.status.optimal") in view.status.text()
    assert view.explanation.text() == S.t("qp.solution.explanation.optimal")
    assert S.t("qp.solution.objective.sense_min") in view.objective_value.text()
    assert view.diagnostic_labels["backend_status"].text() == "solved"
    assert view.diagnostic_labels["backend_version"].text() == "0.6.7.post3"
    assert view.validation_status.text() == S.t("qp.solution.validation_report.empty")
    # Bound positions and constraint activity are derived for display only.
    assert view.variables_table.item(0, 5).text() == S.t("qp.solution.variables.interior")
    assert view.constraints_table.item(0, 5).text() == S.t("qp.solution.constraints.binding")


def test_result_view_renders_the_independent_validation_report(window) -> None:
    model = _boundary_model()
    solution = QPSolution.from_solver_result(
        status="Optimal",
        objective=1.0,
        values={"x1": 1.0, "x2": 1.0},
        dual_values=None,
        extras={"backend": "osqp", "status": "solved"},
    )
    from optees.application.codecs.qp_result_codec import QPResultCodec

    report = QPIndependentSolutionValidator()(model, QPResultCodec().serialize(solution))
    view = window.qp_solution_page
    view.set_problem(model)
    view.set_solution(solution)
    view.set_validation(report)

    assert view.validation_table.rowCount() == len(report.checks)
    assert view.validation_table.item(0, 0).text() == S.t(
        "qp.solution.validation_report.checks.variable_vector.name"
    )
    assert S.t("qp.solution.validation_report.status_partial") in view.validation_status.text()
    assert S.t("qp.solution.validation_report.limitations") in view.validation_limitations.text()
    # Public detail codes contain dots; a naive lookup would leak the raw key.
    for row in range(view.validation_table.rowCount()):
        for column in range(view.validation_table.columnCount()):
            assert not view.validation_table.item(row, column).text().startswith("qp.")


def test_validation_limitations_have_a_translation_for_every_reported_caveat(window) -> None:
    """A caveat the validator reports must never surface as a raw i18n key."""
    view = window.qp_solution_page
    for index in range(len(QPIndependentSolutionValidator.DEFAULT_LIMITATIONS)):
        key = f"qp.solution.validation_report.limitation.{index + 1}"
        assert S.t(key) != key
    assert view is not None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Infeasible", "qp.solution.explanation.infeasible"),
        ("Unbounded", "qp.solution.explanation.unbounded"),
        ("NotSolved", "qp.solution.explanation.not_solved"),
        ("Feasible", "qp.solution.explanation.feasible"),
    ],
)
def test_result_view_explains_every_non_optimal_outcome(window, status, expected) -> None:
    model = _boundary_model()
    has_candidate = status == "Feasible"
    solution = QPSolution.from_solver_result(
        status=status,
        objective=1.4 if has_candidate else None,
        values={"x1": 0.7, "x2": 1.3} if has_candidate else {},
        extras={"backend": "osqp", "status": "maximum iterations reached"},
    )
    view = window.qp_solution_page
    view.set_problem(model)
    view.set_solution(solution)
    view.set_validation(None)
    window.goto("qp_solution")

    assert view.explanation.text() == S.t(expected)
    if not has_candidate:
        assert view.variables_table.rowCount() == 0
        assert view.variables_empty.isVisible()
        assert view.objective_value.text() == S.t("qp.solution.objective.unavailable")


def test_missing_duals_are_reported_as_unavailable(window) -> None:
    view = window.qp_solution_page
    view.set_problem(_boundary_model())
    view.set_solution(_optimal_solution())
    window.goto("qp_solution")

    assert view.duals_table.rowCount() == 0
    assert view.duals_unavailable.isVisible()
    assert view.residual_labels["primal"].text() == S.t("qp.solution.residuals.unavailable")


def test_dependency_failure_is_named_as_a_missing_backend(window) -> None:
    solution = QPSolution.from_solver_result(
        status="NotSolved",
        objective=None,
        values={},
        extras={
            "backend": "osqp",
            "backend_version": None,
            "message": "OSQP is not installed",
            "success": False,
        },
    )
    view = window.qp_solution_page
    view.set_problem(_boundary_model())
    view.set_solution(solution)
    window.goto("qp_solution")

    assert view.dependency_notice.isVisible()
    assert view.dependency_notice.text() == S.t("qp.solution.dependency_failure")


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------


def test_two_variable_problem_draws_contours_and_the_candidate(window) -> None:
    view = window.qp_solution_page
    view.set_problem(_boundary_model())
    view.set_solution(_optimal_solution())

    plot = view.contour_plot
    assert plot.visualization_state == "ready"
    assert plot._figure is not None and plot._figure.axes


def test_higher_dimensions_offer_an_honest_alternative(window) -> None:
    model = QPModel.from_parts(
        variables=[QPVariable(f"x{index}", bounds=Bounds(0.0, 5.0)) for index in range(1, 4)],
        objective=QPObjective(
            sense=ObjectiveSense.MIN,
            linear_coefs=(0.0, 0.0, 0.0),
            quadratic_matrix=tuple(
                tuple(1.0 if row == column else 0.0 for column in range(3)) for row in range(3)
            ),
        ),
    )
    solution = QPSolution.from_solver_result(
        status="Optimal",
        objective=0.0,
        values={"x1": 0.0, "x2": 0.0, "x3": 0.0},
        extras={"backend": "osqp", "status": "solved"},
    )
    view = window.qp_solution_page
    view.set_problem(model)
    view.set_solution(solution)

    assert view.contour_plot.visualization_state == "unsupported_dimension"
    assert view.contour_plot.status_label.text() == S.t(
        "qp.solution.visualization.unsupported_dimension", count=3
    )
    # The exact tables remain the complete answer in every dimension.
    assert view.variables_table.rowCount() == 3


def test_unbounded_window_without_anchors_is_reported(window) -> None:
    model = QPModel.from_parts(
        variables=[QPVariable("x1"), QPVariable("x2")],
        objective=QPObjective(
            sense=ObjectiveSense.MIN,
            linear_coefs=(0.0, 0.0),
            quadratic_matrix=((1.0, 0.0), (0.0, 1.0)),
        ),
    )
    view = window.qp_solution_page
    view.set_problem(model)
    view.set_solution(None)

    assert view.contour_plot.visualization_state == "no_window"


# ---------------------------------------------------------------------------
# Localization and accessibility
# ---------------------------------------------------------------------------


def test_qp_view_uses_localized_controls(window) -> None:
    window.goto("qp")

    assert window.qp_page.findChild(QPushButton, "qpImportJsonButton").text()
    assert window.qp_page.findChild(QPushButton, "qpExportJsonButton").text()
    assert window.qp_page.findChild(QPushButton, "qpSolveButton").text()
    assert window.qp_page.findChild(QComboBox, "qpObjectiveSense").count() == 2
    assert window.qp_page.btn_json_info.property("variant") == "info"


def test_interactive_controls_expose_accessible_names(window) -> None:
    window.goto("qp")
    row = window.qp_page.variables_section.rows()[0]

    assert row.edit_name.accessibleName() == S.t("qp.variables.columns.name")
    assert row.edit_lower.accessibleName() == S.t("qp.variables.columns.lower")
    assert window.qp_page.edit_tolerance.accessibleName() == S.t("qp.solver.tolerance")
    assert window.qp_page.matrix_table.accessibleName() == S.t("qp.objective.matrix_label")


@pytest.mark.parametrize("language", ["en", "it"])
def test_qp_pages_retranslate_in_each_supported_language(window, language: str) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        window.qp_solution_page.set_problem(_boundary_model())
        window.qp_solution_page.set_solution(_optimal_solution())

        assert window.qp_page.btn_solve.text() == S.t("qp.actions.solve")
        assert window.qp_page.btn_export_json.text() == S.t("qp.export.button")
        assert "qp." not in window.qp_page.title.text()
        assert "qp." not in window.qp_page.formula_label.text()
        assert "qp." not in window.qp_solution_page.status.text()
        assert "qp." not in window.qp_solution_page.explanation.text()
        assert window.act_qp.text() == S.t("alg.qp")
    finally:
        S.set_language(previous)


def test_backend_availability_disables_solving_without_hiding_the_form(window) -> None:
    window.goto("qp")

    window.qp_page.set_backend_available(False)
    assert window.qp_page.dependency_notice.isVisible()
    assert not window.qp_page.btn_solve.isEnabled()
    assert window.qp_page.matrix_table.isVisible()

    window.qp_page.set_backend_available(True)
    assert not window.qp_page.dependency_notice.isVisible()
    assert window.qp_page.btn_solve.isEnabled()


def test_large_models_hide_the_dense_editor_but_stay_solvable(window, qtbot) -> None:
    size = 15
    model = QPModel.from_parts(
        variables=[QPVariable(f"x{index}") for index in range(size)],
        objective=QPObjective(
            sense=ObjectiveSense.MIN,
            linear_coefs=tuple(0.0 for _ in range(size)),
            quadratic_matrix=tuple(
                tuple(1.0 if row == column else 0.0 for column in range(size))
                for row in range(size)
            ),
        ),
    )
    window.goto("qp")
    window.qp_page.set_model(model)

    assert not window.qp_page.matrix_table.isVisible()
    assert window.qp_page.large_matrix_notice.isVisible()
    assert str(size) in window.qp_page.large_matrix_notice.text()

    fake = FakeSolver({"status": "Optimal", "objective": 0.0, "x": {}})
    window.qp_page.set_solve_usecase(SolveQPUseCase(fake))
    qtbot.mouseClick(window.qp_page.btn_solve, Qt.LeftButton)

    assert len(fake.last_problem["variables"]) == size
