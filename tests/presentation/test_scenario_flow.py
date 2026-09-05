"""Desktop workflow coverage for the linear scenario capabilities.

These tests drive the production views and their view-model. Mathematical
expectations come from the frozen contract's reference examples and are produced
by the registered capability, never recomputed here.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QPushButton

from optees.application.contracts.capability_ids import (
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
)
from optees.application.contracts.errors import ErrorCode, ErrorDetail, StructuredError
from optees.core.string_manager import strings as S
from optees.presentation.viewmodels.scenario_view_model import (
    MAX_MIN_REWARD_ORIENTATION,
    MIN_MAX_LOSS_ORIENTATION,
)
from optees.presentation.views.scenario_comparison_widget import BINDING_MARKER

SOLVE_TIMEOUT_MS = 20_000


@pytest.mark.parametrize("removed", [0, 1, 2])
def test_remove_variable_preserves_coefficient_identity(qtbot, removed):
    from PySide6.QtWidgets import QTableWidgetItem
    from optees.presentation.views.scenario_view import ScenarioView

    view = ScenarioView()
    qtbot.addWidget(view)
    view._on_add_variable()
    view._on_add_constraint()
    grids = [(view.shared_table, 0), (view.constraints_table, 1), (view.scenarios_table, 2)]
    for table, offset in grids:
        for column, value in enumerate([11, 22, 33]):
            table.setItem(0, column + offset, QTableWidgetItem(str(value)))
    view.variables_table.setCurrentCell(removed, 0)
    view._on_remove_variable()
    expected = [str(v) for i, v in enumerate([11, 22, 33]) if i != removed]
    for table, offset in grids:
        assert [table.item(0, c + offset).text() for c in range(2)] == expected
    view._on_add_variable()
    for table, offset in grids:
        assert table.item(0, 2 + offset).text() == "0"


# ---------------------------------------------------------------------------
# Composition and navigation
# ---------------------------------------------------------------------------


def test_desktop_resolves_both_registered_scenario_capabilities(window) -> None:
    """One composition smoke test through the ordinary application boundary."""
    service = window.optimization_service
    registered = {descriptor["id"] for descriptor in service.list_capabilities()}

    assert SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID in registered
    assert SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID in registered

    view_model = window.scenario_page.view_model
    for capability_id in (
        SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
        SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    ):
        descriptor = view_model.capability_descriptor(capability_id)
        assert descriptor is not None
        assert descriptor["problem_type"] == "linear_scenario"
        assert descriptor["problem_schema_version"] == "1"
        assert descriptor["result_schema_version"] == "1"


def test_home_card_opens_the_scenario_page(window, qtbot) -> None:
    assert window.home_page.card_scenario.parentWidget() is window.home_page.cat_lin

    qtbot.mouseClick(window.home_page.card_scenario, Qt.LeftButton)

    assert window.stack.currentWidget() is window.scenario_page


def test_toolbar_names_each_orientation_separately(window) -> None:
    menu_actions = window.drop.menu().actions()
    assert window.act_scenario_min_max in menu_actions
    assert window.act_scenario_max_min in menu_actions
    assert window.act_scenario_min_max.text() != window.act_scenario_max_min.text()

    window.act_scenario_max_min.trigger()
    assert window.stack.currentWidget() is window.scenario_page
    assert window.scenario_page.view_model.capability_id == SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID
    assert window.scenario_page.radio_max_min.isChecked()

    window.act_scenario_min_max.trigger()
    assert window.scenario_page.view_model.capability_id == SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID
    assert window.scenario_page.radio_min_max.isChecked()


def test_solution_page_returns_to_the_formulation(window, qtbot) -> None:
    window.goto("scenario_solution")

    qtbot.mouseClick(window.scenario_solution_page.btn_back, Qt.LeftButton)

    assert window.stack.currentWidget() is window.scenario_page


# ---------------------------------------------------------------------------
# Orientation semantics
# ---------------------------------------------------------------------------


def test_the_two_orientations_are_labelled_as_distinct_semantics(window) -> None:
    page = window.scenario_page

    assert page.radio_min_max.text() == S.t("scenario.orientation.min_max_loss")
    assert page.radio_max_min.text() == S.t("scenario.orientation.max_min_reward")
    assert page.radio_min_max.text() != page.radio_max_min.text()
    assert page.min_max_description.text() != page.max_min_description.text()
    assert page.min_max_description.text()
    assert page.max_min_description.text()


def test_selecting_an_orientation_updates_the_named_capability(window) -> None:
    page = window.scenario_page

    page.radio_max_min.setChecked(True)
    assert page.view_model.orientation == MAX_MIN_REWARD_ORIENTATION
    assert SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID in page.capability_label.text()

    page.radio_min_max.setChecked(True)
    assert page.view_model.orientation == MIN_MAX_LOSS_ORIENTATION
    assert SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID in page.capability_label.text()


# ---------------------------------------------------------------------------
# Structured editing
# ---------------------------------------------------------------------------


def test_the_default_problem_is_the_contract_reference(window) -> None:
    form = window.scenario_page.current_form()

    assert [variable.name for variable in form.variables] == ["x1", "x2"]
    assert [scenario.scenario_id for scenario in form.scenarios] == ["s1", "s2", "s3"]
    assert form.scenarios[0].coefficients == (2.0, -1.0)
    assert form.constraints[0].relation == "="


def test_adding_a_variable_rebinds_every_coefficient_grid(window, qtbot) -> None:
    page = window.scenario_page

    qtbot.mouseClick(page.findChild(QPushButton, "scenarioAddVariableButton"), Qt.LeftButton)

    assert page.variables_table.rowCount() == 3
    # name + one column per variable + relation + right-hand side
    assert page.constraints_table.columnCount() == 6
    # id + label + one column per variable + constant
    assert page.scenarios_table.columnCount() == 6
    form = page.current_form()
    assert len(form.variables) == 3
    assert all(len(scenario.coefficients) == 3 for scenario in form.scenarios)
    assert all(len(constraint.coefficients) == 3 for constraint in form.constraints)


def test_removing_a_variable_rebinds_every_coefficient_grid(window, qtbot) -> None:
    page = window.scenario_page
    page.variables_table.setCurrentCell(1, 0)

    qtbot.mouseClick(page.findChild(QPushButton, "scenarioRemoveVariableButton"), Qt.LeftButton)

    assert page.variables_table.rowCount() == 1
    form = page.current_form()
    assert len(form.variables) == 1
    assert all(len(scenario.coefficients) == 1 for scenario in form.scenarios)


def test_scenarios_can_be_added_and_removed(window, qtbot) -> None:
    page = window.scenario_page

    qtbot.mouseClick(page.findChild(QPushButton, "scenarioAddScenarioButton"), Qt.LeftButton)
    assert page.scenarios_table.rowCount() == 4
    assert len(page.current_form().scenarios) == 4

    qtbot.mouseClick(page.findChild(QPushButton, "scenarioRemoveScenarioButton"), Qt.LeftButton)
    assert page.scenarios_table.rowCount() == 3


def test_the_last_scenario_cannot_be_removed(window, qtbot) -> None:
    page = window.scenario_page
    remove = page.findChild(QPushButton, "scenarioRemoveScenarioButton")
    for _ in range(2):
        qtbot.mouseClick(remove, Qt.LeftButton)

    assert page.scenarios_table.rowCount() == 1
    assert not remove.isEnabled()
    qtbot.mouseClick(remove, Qt.LeftButton)
    assert page.scenarios_table.rowCount() == 1


def test_constraints_can_be_emptied_and_the_empty_state_is_shown(window, qtbot) -> None:
    window.goto("scenario")
    page = window.scenario_page
    remove = page.findChild(QPushButton, "scenarioRemoveConstraintButton")

    qtbot.mouseClick(remove, Qt.LeftButton)

    assert page.constraints_table.rowCount() == 0
    assert not remove.isEnabled()
    assert page.constraints_empty.isVisible()
    assert page.current_form().constraints == ()


def test_the_shared_term_is_optional_and_toggled(window) -> None:
    window.goto("scenario")
    page = window.scenario_page
    assert page.current_form().shared_objective_coefficients is None

    page.chk_shared_objective.setChecked(True)
    assert page.shared_table.isVisible()
    form = page.current_form()
    assert form.shared_objective_coefficients == (0.0, 0.0)
    assert form.shared_objective_offset == 0.0


def test_an_incomplete_row_is_rejected_with_a_localized_message(window, monkeypatch) -> None:
    page = window.scenario_page
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "optees.presentation.views.scenario_view.QMessageBox.warning",
        lambda _parent, title, body: captured.update(title=title, body=body),
    )
    page.scenarios_table.item(0, 2).setText("")

    page._on_solve()

    assert captured["title"] == S.t("scenario.validation.title")
    assert S.t("error_feedback.scenario.scenarios") in captured["body"]


def test_a_missing_scenario_identifier_is_rejected(window, monkeypatch) -> None:
    page = window.scenario_page
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "optees.presentation.views.scenario_view.QMessageBox.warning",
        lambda _parent, title, body: captured.update(title=title, body=body),
    )
    page.scenarios_table.item(1, 0).setText("   ")

    page._on_solve()

    assert captured["title"] == S.t("scenario.validation.title")


# ---------------------------------------------------------------------------
# Accessibility and localization
# ---------------------------------------------------------------------------


def test_interactive_controls_expose_accessible_names(window) -> None:
    page = window.scenario_page

    assert page.radio_min_max.accessibleName() == S.t("scenario.orientation.min_max_loss")
    assert page.radio_max_min.accessibleName() == S.t("scenario.orientation.max_min_reward")
    assert page.edit_tolerance.accessibleName() == S.t("scenario.options.tolerance")
    assert page.edit_binding_tolerance.accessibleName() == S.t("scenario.options.binding_tolerance")
    assert page.edit_time_limit.accessibleName() == S.t("scenario.options.time_limit")
    integrality = page.variables_table.cellWidget(0, 4)
    assert isinstance(integrality, QComboBox)
    assert integrality.accessibleName() == S.t("scenario.variables.columns.integrality")
    relation = page.constraints_table.cellWidget(0, 3)
    assert isinstance(relation, QComboBox)
    assert relation.accessibleName() == S.t("scenario.constraints.columns.relation")


def test_orientation_radios_are_keyboard_reachable(window, qtbot) -> None:
    page = window.scenario_page

    page.radio_min_max.setFocus()
    assert page.radio_min_max.hasFocus()
    assert page.radio_min_max.focusPolicy() != Qt.NoFocus
    assert page.radio_max_min.focusPolicy() != Qt.NoFocus

    # Space activates the focused radio without a pointer.
    page.radio_max_min.setFocus()
    qtbot.keyClick(page.radio_max_min, Qt.Key_Space)
    assert page.radio_max_min.isChecked()
    assert page.view_model.capability_id == SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID


def test_grids_are_keyboard_navigable(window) -> None:
    page = window.scenario_page

    for table in (page.variables_table, page.constraints_table, page.scenarios_table):
        assert table.focusPolicy() != Qt.NoFocus


@pytest.mark.parametrize("language", ["en", "it"])
def test_scenario_pages_retranslate_in_each_supported_language(window, language: str) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        page = window.scenario_page

        assert page.btn_solve.text() == S.t("scenario.solve.button")
        assert page.radio_min_max.text() == S.t("scenario.orientation.min_max_loss")
        assert "scenario." not in page.title.text()
        assert "scenario." not in page.intro_text.text()
        assert "scenario." not in page.min_max_description.text()
        assert window.act_scenario_min_max.text() == S.t("alg.scenario_min_max")
        assert "scenario." not in window.scenario_solution_page.title.text()
    finally:
        S.set_language(previous)


# ---------------------------------------------------------------------------
# End-to-end result presentation
# ---------------------------------------------------------------------------


def _solve_default(window, qtbot):
    page = window.scenario_page
    with qtbot.waitSignal(page.solve_completed, timeout=SOLVE_TIMEOUT_MS) as blocker:
        qtbot.mouseClick(page.btn_solve, Qt.LeftButton)
    return blocker.args[0]


def test_solving_navigates_and_separates_every_reported_status(window, qtbot) -> None:
    envelope = _solve_default(window, qtbot)

    assert window.stack.currentWidget() is window.scenario_solution_page
    view = window.scenario_solution_page
    assert view.envelope is envelope
    assert view.status_labels["job"].text() == S.t("scenario.solution.job_status.completed")
    assert view.status_labels["mathematical"].text() == S.t(
        "scenario.solution.mathematical_status.optimal"
    )
    assert view.status_labels["termination"].text() == S.t(
        "scenario.solution.termination_reason.completed"
    )
    assert view.status_labels["validation"].text() == S.t(
        "scenario.solution.validation_status.verified"
    )
    # The four facts are rendered by four distinct widgets.
    assert (
        len(
            {
                id(view.status_labels[key])
                for key in ("job", "mathematical", "termination", "validation")
            }
        )
        == 4
    )


def test_the_result_view_shows_the_returned_values_verbatim(window, qtbot) -> None:
    _solve_default(window, qtbot)
    view = window.scenario_solution_page

    assert view.scenarios_table.rowCount() == 3
    assert [view.scenarios_table.item(row, 1).text() for row in range(3)] == ["s1", "s2", "s3"]
    assert BINDING_MARKER in view.scenarios_table.item(0, 3).text()
    assert BINDING_MARKER in view.scenarios_table.item(1, 3).text()
    assert BINDING_MARKER not in view.scenarios_table.item(2, 3).text()
    assert view.binding_summary.text() == S.t(
        "scenario.solution.scenarios.binding_summary", ids="s1, s2"
    )
    assert view.variables_table.rowCount() == 2
    assert view.comparison.plotted_scenario_ids == ("s1", "s2", "s3")
    assert view.diagnostics_table.rowCount() > 0
    assert view.validation_table.rowCount() > 0


def test_validation_rows_never_leak_a_raw_resource_key(window, qtbot) -> None:
    _solve_default(window, qtbot)
    table = window.scenario_solution_page.validation_table

    for row in range(table.rowCount()):
        for column in range(table.columnCount()):
            assert not table.item(row, column).text().startswith("scenario.")


def test_a_structured_rejection_is_shown_instead_of_an_empty_result(window) -> None:
    view = window.scenario_solution_page
    error = StructuredError(
        code=ErrorCode.DEPENDENCY_UNAVAILABLE,
        message="The capability is unavailable in this installation.",
        details=(ErrorDetail(path="$", message="missing backend", code="dependency"),),
    )

    view.set_error(error)

    assert not view.error_section.isHidden()
    assert S.t("scenario.solution.error.codes.dependency_unavailable") in view.error_code.text()
    assert "missing backend" in view.error_details.text()
    assert view.envelope is None


def test_structured_rejection_details_are_html_escaped(window) -> None:
    view = window.scenario_solution_page
    error = StructuredError(
        code=ErrorCode.VALIDATION_FAILED,
        message="Invalid input",
        details=(
            ErrorDetail(
                path="<b>field</b>",
                message="<img src=x>",
                code="invalid<input>",
            ),
        ),
    )

    view.set_error(error)

    rendered = view.error_details.text()
    assert "&lt;b&gt;field&lt;/b&gt;" in rendered
    assert "&lt;img src=x&gt;" in rendered
    assert "invalid&lt;input&gt;" in rendered


def test_actions_are_disabled_while_a_submission_is_in_flight(window) -> None:
    window.goto("scenario")
    page = window.scenario_page

    page._on_busy_changed(True)
    assert not page.btn_solve.isEnabled()
    assert page.btn_cancel.isVisible()
    assert not page.radio_max_min.isEnabled()
    assert not page.btn_add_scenario.isEnabled()
    assert page.solve_notice.text() == S.t("scenario.solve.running")

    page._on_busy_changed(False)
    assert page.btn_solve.isEnabled()
    assert not page.btn_cancel.isVisible()
    assert page.radio_max_min.isEnabled()
