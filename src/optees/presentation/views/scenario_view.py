"""Formulation view for the linear scenario min-max / max-min capabilities.

The view collects ordered decision variables, shared terms, scenarios and
solver options, then hands a form snapshot to :class:`ScenarioViewModel`. It
performs input-shape validation only: every mathematical decision, including
the reduction, the guarantee and the binding set, stays behind the registered
application capability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from optees.application.contracts.capability_ids import (
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
)
from optees.application.codecs.scenario_problem_codec import scenario_model_from_public_dict
from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.error_feedback import localized_error_detail
from optees.presentation.viewmodels.scenario_view_model import (
    ScenarioConstraintInput,
    ScenarioFormInput,
    ScenarioInput,
    ScenarioOptionsInput,
    ScenarioVariableInput,
    ScenarioViewModel,
    build_problem_payload,
    MIN_MAX_LOSS_ORIENTATION,
)
from optees.presentation.views.lp_view.section import Section

_INTEGRALITY_TOKENS = ("C", "I", "B")
_RELATION_SYMBOLS = ("<=", "=", ">=")
_NUMERIC_WIDTH = 130
_MAX_GRID_ROWS = 8


def _parse_number(text: str, *, required: bool, label: str) -> Optional[float]:
    """Parse one user-entered number, accepting comma decimals and fractions."""
    normalized = text.strip().replace(",", ".")
    if not normalized:
        if required:
            raise ValueError(f"{label} is required")
        return None
    try:
        if "/" in normalized:
            numerator, denominator = normalized.split("/", 1)
            return float(numerator) / float(denominator)
        return float(normalized)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc


def _format_optional(value: Optional[float]) -> str:
    return "" if value is None else f"{float(value):.10g}"


def _format_number(value: float) -> str:
    return f"{float(value):.10g}"


def _make_info_button(object_name: str) -> QPushButton:
    button = QPushButton("i")
    button.setObjectName(object_name)
    button.setProperty("variant", "info")
    button.setFixedSize(24, 24)
    button.setCursor(Qt.PointingHandCursor)
    return button


def _fit_table_height(table: QTableWidget, *, max_rows: int = _MAX_GRID_ROWS) -> None:
    visible = min(max(table.rowCount(), 1), max_rows)
    rows = sum(table.rowHeight(row) for row in range(min(table.rowCount(), visible)))
    if table.rowCount() == 0:
        rows = table.verticalHeader().defaultSectionSize()
    header = table.horizontalHeader().height()
    table.setFixedHeight(header + rows + 2 * table.frameWidth() + 2)


def _make_grid(object_name: str) -> QTableWidget:
    table = QTableWidget(0, 0)
    table.setObjectName(object_name)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(False)
    return table


def _cell(text: str, *, centered: bool = True) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if centered:
        item.setTextAlignment(Qt.AlignCenter)
    return item


def _cell_text(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column)
    return item.text() if item is not None else ""


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 420)
        self.setWindowTitle(title)
        root = QVBoxLayout(self)
        intro_label = QLabel(intro)
        intro_label.setWordWrap(True)
        root.addWidget(intro_label)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setHtml(html)
        root.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(S.t("nlp.info.close"))
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class ScenarioView(QWidget):
    """Scenario formulation page shared by both frozen orientations."""

    solve_completed = Signal(object)
    solve_rejected = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(
        self,
        view_model: Optional[ScenarioViewModel] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model or ScenarioViewModel(parent=self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        root.addWidget(self.title)

        self.dependency_notice = QLabel()
        self.dependency_notice.setObjectName("scenarioDependencyNotice")
        self.dependency_notice.setWordWrap(True)
        self.dependency_notice.setVisible(False)
        root.addWidget(self.dependency_notice)

        root.addWidget(self._build_intro_section())
        root.addWidget(self._build_orientation_section())
        root.addWidget(self._build_variables_section())
        root.addWidget(self._build_shared_objective_section())
        root.addWidget(self._build_constraints_section())
        root.addWidget(self._build_scenarios_section())
        root.addWidget(self._build_options_section())

        actions = QHBoxLayout()
        self.solve_notice = QLabel()
        self.solve_notice.setObjectName("scenarioSolveNotice")
        self.solve_notice.setWordWrap(True)
        actions.addWidget(self.solve_notice, 1)
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("scenarioCancelButton")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        actions.addWidget(self.btn_cancel)
        self.btn_solve = QPushButton()
        self.btn_solve.setObjectName("scenarioSolveButton")
        self.btn_solve.setDefault(True)
        self.btn_solve.clicked.connect(self._on_solve)
        actions.addWidget(self.btn_solve)
        root.addLayout(actions)
        root.addStretch(1)

        self._connect_view_model()
        self._load_default_problem()
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    # -- construction helpers -------------------------------------------
    def _build_intro_section(self) -> Section:
        section = Section()
        header = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        header.addWidget(self.intro_text, 1)
        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("scenarioImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_export_json = QPushButton()
        self.btn_export_json.setObjectName("scenarioExportJsonButton")
        self.btn_export_json.clicked.connect(self._on_export_json)
        self.btn_json_info = _make_info_button("scenarioJsonInfoButton")
        self.btn_json_info.clicked.connect(lambda: self._show_info("import"))
        header.addWidget(self.btn_import_json)
        header.addWidget(self.btn_export_json)
        header.addWidget(self.btn_json_info)
        section.body.addLayout(header)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("scenarioExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("scenarioProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        actions.addWidget(self.btn_example)
        actions.addWidget(self.btn_problem)
        section.body.addLayout(actions)
        self.intro_section = section
        return section

    def _build_orientation_section(self) -> Section:
        section = Section()
        header = QHBoxLayout()
        self.orientation_hint = QLabel()
        self.orientation_hint.setWordWrap(True)
        header.addWidget(self.orientation_hint, 1)
        self.btn_orientation_info = _make_info_button("scenarioOrientationInfoButton")
        self.btn_orientation_info.clicked.connect(lambda: self._show_info("orientation"))
        header.addWidget(self.btn_orientation_info)
        section.body.addLayout(header)

        self.radio_min_max = QRadioButton()
        self.radio_min_max.setObjectName("scenarioOrientationMinMaxLoss")
        self.radio_min_max.setChecked(True)
        self.radio_min_max.toggled.connect(self._on_orientation_toggled)
        self.min_max_description = QLabel()
        self.min_max_description.setWordWrap(True)
        self.min_max_description.setIndent(24)

        self.radio_max_min = QRadioButton()
        self.radio_max_min.setObjectName("scenarioOrientationMaxMinReward")
        self.radio_max_min.toggled.connect(self._on_orientation_toggled)
        self.max_min_description = QLabel()
        self.max_min_description.setWordWrap(True)
        self.max_min_description.setIndent(24)

        for widget in (
            self.radio_min_max,
            self.min_max_description,
            self.radio_max_min,
            self.max_min_description,
        ):
            section.body.addWidget(widget)

        self.capability_label = QLabel()
        self.capability_label.setObjectName("scenarioCapabilityLabel")
        self.capability_label.setWordWrap(True)
        section.body.addWidget(self.capability_label)
        self.orientation_section = section
        return section

    def _build_variables_section(self) -> Section:
        section = Section()
        self.variables_hint = QLabel()
        self.variables_hint.setWordWrap(True)
        section.body.addWidget(self.variables_hint)
        self.variables_table = _make_grid("scenarioVariablesTable")
        self.variables_table.setColumnCount(5)
        self.variables_table.itemChanged.connect(self._on_variable_names_changed)
        section.body.addWidget(self.variables_table)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_remove_variable = QPushButton()
        self.btn_remove_variable.setObjectName("scenarioRemoveVariableButton")
        self.btn_remove_variable.clicked.connect(self._on_remove_variable)
        self.btn_add_variable = QPushButton()
        self.btn_add_variable.setObjectName("scenarioAddVariableButton")
        self.btn_add_variable.clicked.connect(self._on_add_variable)
        footer.addWidget(self.btn_remove_variable)
        footer.addWidget(self.btn_add_variable)
        section.body.addLayout(footer)
        self.variables_section = section
        return section

    def _build_shared_objective_section(self) -> Section:
        section = Section()
        self.shared_hint = QLabel()
        self.shared_hint.setWordWrap(True)
        section.body.addWidget(self.shared_hint)
        self.chk_shared_objective = QCheckBox()
        self.chk_shared_objective.setObjectName("scenarioSharedObjectiveToggle")
        self.chk_shared_objective.toggled.connect(self._on_shared_objective_toggled)
        section.body.addWidget(self.chk_shared_objective)
        self.shared_table = _make_grid("scenarioSharedObjectiveTable")
        self.shared_table.setVisible(False)
        section.body.addWidget(self.shared_table)
        offset_row = QHBoxLayout()
        self.lbl_shared_offset = QLabel()
        self.edit_shared_offset = QLineEdit("0")
        self.edit_shared_offset.setObjectName("scenarioSharedObjectiveOffset")
        self.edit_shared_offset.setFixedWidth(_NUMERIC_WIDTH)
        offset_row.addWidget(self.lbl_shared_offset)
        offset_row.addWidget(self.edit_shared_offset)
        offset_row.addStretch(1)
        self.shared_offset_row = offset_row
        self.lbl_shared_offset.setVisible(False)
        self.edit_shared_offset.setVisible(False)
        section.body.addLayout(offset_row)
        self.shared_section = section
        return section

    def _build_constraints_section(self) -> Section:
        section = Section()
        self.constraints_hint = QLabel()
        self.constraints_hint.setWordWrap(True)
        section.body.addWidget(self.constraints_hint)
        self.constraints_table = _make_grid("scenarioConstraintsTable")
        section.body.addWidget(self.constraints_table)
        self.constraints_empty = QLabel()
        self.constraints_empty.setObjectName("scenarioConstraintsEmpty")
        self.constraints_empty.setWordWrap(True)
        section.body.addWidget(self.constraints_empty)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_remove_constraint = QPushButton()
        self.btn_remove_constraint.setObjectName("scenarioRemoveConstraintButton")
        self.btn_remove_constraint.clicked.connect(self._on_remove_constraint)
        self.btn_add_constraint = QPushButton()
        self.btn_add_constraint.setObjectName("scenarioAddConstraintButton")
        self.btn_add_constraint.clicked.connect(self._on_add_constraint)
        footer.addWidget(self.btn_remove_constraint)
        footer.addWidget(self.btn_add_constraint)
        section.body.addLayout(footer)
        self.constraints_section = section
        return section

    def _build_scenarios_section(self) -> Section:
        section = Section()
        header = QHBoxLayout()
        self.scenarios_hint = QLabel()
        self.scenarios_hint.setWordWrap(True)
        header.addWidget(self.scenarios_hint, 1)
        self.btn_scenarios_info = _make_info_button("scenarioScenariosInfoButton")
        self.btn_scenarios_info.clicked.connect(lambda: self._show_info("scenarios"))
        header.addWidget(self.btn_scenarios_info)
        section.body.addLayout(header)
        self.scenarios_table = _make_grid("scenarioScenariosTable")
        section.body.addWidget(self.scenarios_table)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_remove_scenario = QPushButton()
        self.btn_remove_scenario.setObjectName("scenarioRemoveScenarioButton")
        self.btn_remove_scenario.clicked.connect(self._on_remove_scenario)
        self.btn_add_scenario = QPushButton()
        self.btn_add_scenario.setObjectName("scenarioAddScenarioButton")
        self.btn_add_scenario.clicked.connect(self._on_add_scenario)
        footer.addWidget(self.btn_remove_scenario)
        footer.addWidget(self.btn_add_scenario)
        section.body.addLayout(footer)
        self.scenarios_section = section
        return section

    def _build_options_section(self) -> Section:
        section = Section()
        header = QHBoxLayout()
        self.options_hint = QLabel()
        self.options_hint.setWordWrap(True)
        header.addWidget(self.options_hint, 1)
        self.btn_options_info = _make_info_button("scenarioOptionsInfoButton")
        self.btn_options_info.clicked.connect(lambda: self._show_info("options"))
        header.addWidget(self.btn_options_info)
        section.body.addLayout(header)
        row = QHBoxLayout()
        self.lbl_tolerance = QLabel()
        self.edit_tolerance = QLineEdit("1e-7")
        self.edit_tolerance.setObjectName("scenarioTolerance")
        self.edit_tolerance.setFixedWidth(_NUMERIC_WIDTH)
        self.lbl_binding_tolerance = QLabel()
        self.edit_binding_tolerance = QLineEdit("1e-6")
        self.edit_binding_tolerance.setObjectName("scenarioBindingTolerance")
        self.edit_binding_tolerance.setFixedWidth(_NUMERIC_WIDTH)
        self.lbl_time_limit = QLabel()
        self.edit_time_limit = QLineEdit("")
        self.edit_time_limit.setObjectName("scenarioTimeLimit")
        self.edit_time_limit.setFixedWidth(_NUMERIC_WIDTH)
        for label, editor in (
            (self.lbl_tolerance, self.edit_tolerance),
            (self.lbl_binding_tolerance, self.edit_binding_tolerance),
            (self.lbl_time_limit, self.edit_time_limit),
        ):
            row.addWidget(label)
            row.addWidget(editor)
            row.addSpacing(16)
        row.addStretch(1)
        section.body.addLayout(row)
        self.options_section = section
        return section

    # -- view-model wiring ----------------------------------------------
    def _connect_view_model(self) -> None:
        self._view_model.succeeded.connect(self._on_succeeded)
        self._view_model.rejected.connect(self._on_rejected)
        self._view_model.failed.connect(self._on_failed)
        self._view_model.busy_changed.connect(self._on_busy_changed)

    @property
    def view_model(self) -> ScenarioViewModel:
        return self._view_model

    def set_optimization_service(self, service: object) -> None:
        self._view_model.set_service(service)  # type: ignore[arg-type]
        self._refresh_availability()

    def set_capability_id(self, capability_id: str) -> None:
        """Preselect one orientation without aliasing it to the other."""
        self._view_model.set_capability_id(capability_id)
        if capability_id == SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID:
            self.radio_min_max.setChecked(True)
        else:
            self.radio_max_min.setChecked(True)
        self._refresh_availability()
        self.refresh_strings()

    def _on_orientation_toggled(self, _checked: bool) -> None:
        capability_id = (
            SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID
            if self.radio_min_max.isChecked()
            else SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID
        )
        self._view_model.set_capability_id(capability_id)
        self._refresh_availability()
        self.refresh_strings()

    def _refresh_availability(self) -> None:
        available = self._view_model.is_available()
        descriptor = self._view_model.capability_descriptor()
        known = descriptor is not None
        self.dependency_notice.setVisible(known and not available)
        if known and not available:
            reason = self._view_model.unavailable_reason() or ""
            self.dependency_notice.setText(S.t("scenario.dependency.unavailable", reason=reason))
        self.btn_solve.setEnabled(not known or available)

    # -- default problem -------------------------------------------------
    def _load_default_problem(self) -> None:
        """Seed the frozen contract's first analytic reference problem."""
        self._set_variables(
            [
                ScenarioVariableInput("x1", "Allocation 1", 0.0, None, "C"),
                ScenarioVariableInput("x2", "Allocation 2", 0.0, None, "C"),
            ]
        )
        self._set_constraints([ScenarioConstraintInput("total_budget", (1.0, 1.0), "=", 10.0)])
        self._set_scenarios(
            [
                ScenarioInput("s1", "Regime 1", (2.0, -1.0), 5.0),
                ScenarioInput("s2", "Regime 2", (-1.0, 3.0), 2.0),
                ScenarioInput("s3", "Regime 3", (1.0, 1.0), -4.0),
            ]
        )

    # -- variables grid --------------------------------------------------
    def _set_variables(self, variables) -> None:
        table = self.variables_table
        table.blockSignals(True)
        try:
            table.setRowCount(0)
            for variable in variables:
                self._append_variable_row(variable)
        finally:
            table.blockSignals(False)
        self._refresh_variable_headers()
        self._rebind_variable_columns()

    def _append_variable_row(self, variable: ScenarioVariableInput) -> None:
        table = self.variables_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, _cell(variable.name, centered=False))
        table.setItem(row, 1, _cell(variable.label, centered=False))
        table.setItem(row, 2, _cell(_format_optional(variable.lower_bound)))
        table.setItem(row, 3, _cell(_format_optional(variable.upper_bound)))
        combo = QComboBox()
        combo.setObjectName("scenarioVariableIntegrality")
        for token in _INTEGRALITY_TOKENS:
            combo.addItem(S.t(f"scenario.variables.integrality.{token}"), token)
        combo.setCurrentIndex(max(0, combo.findData(variable.integrality)))
        combo.setAccessibleName(S.t("scenario.variables.columns.integrality"))
        table.setCellWidget(row, 4, combo)

    def _variable_names(self) -> list[str]:
        names: list[str] = []
        for row in range(self.variables_table.rowCount()):
            text = _cell_text(self.variables_table, row, 0).strip()
            names.append(text or f"x{row + 1}")
        return names

    def _on_variable_names_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            self._refresh_variable_headers()

    def _on_add_variable(self) -> None:
        existing = set(self._variable_names())
        index = self.variables_table.rowCount() + 1
        name = f"x{index}"
        while name in existing:
            index += 1
            name = f"x{index}"
        table = self.variables_table
        table.blockSignals(True)
        try:
            self._append_variable_row(ScenarioVariableInput(name, "", 0.0, None, "C"))
        finally:
            table.blockSignals(False)
        self._refresh_variable_headers()
        self._rebind_variable_columns()

    def _on_remove_variable(self) -> None:
        table = self.variables_table
        if table.rowCount() <= 1:
            return
        row = table.currentRow()
        if row < 0:
            row = table.rowCount() - 1
        # Remove the same variable from every grid before rebuilding headers.
        # Truncating the grids would silently reassign later coefficients.
        self.shared_table.removeColumn(row)
        self.constraints_table.removeColumn(row + 1)
        self.scenarios_table.removeColumn(row + 2)
        table.blockSignals(True)
        try:
            table.removeRow(row)
        finally:
            table.blockSignals(False)
        self._refresh_variable_headers()
        self._rebind_variable_columns()

    def _refresh_variable_headers(self) -> None:
        self.variables_table.setHorizontalHeaderLabels(
            [
                S.t("scenario.variables.columns.name"),
                S.t("scenario.variables.columns.label"),
                S.t("scenario.variables.columns.lower"),
                S.t("scenario.variables.columns.upper"),
                S.t("scenario.variables.columns.integrality"),
            ]
        )
        header = self.variables_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (2, 3, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        _fit_table_height(self.variables_table)

    # -- variable-bound grids -------------------------------------------
    def _rebind_variable_columns(self) -> None:
        """Keep every coefficient grid bound to the declared variable order."""
        names = self._variable_names()
        self._rebind_shared_objective(names)
        self._rebind_constraints(names)
        self._rebind_scenarios(names)

    def _rebind_shared_objective(self, names: list[str]) -> None:
        table = self.shared_table
        previous = [_cell_text(table, 0, column) for column in range(table.columnCount())]
        table.setColumnCount(len(names))
        table.setHorizontalHeaderLabels(names)
        table.setRowCount(1)
        for column in range(len(names)):
            text = previous[column] if column < len(previous) else "0"
            table.setItem(0, column, _cell(text or "0"))
        header = table.horizontalHeader()
        for column in range(len(names)):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        _fit_table_height(table)

    def _constraint_headers(self, names: list[str]) -> list[str]:
        return (
            [S.t("scenario.constraints.columns.name")]
            + names
            + [
                S.t("scenario.constraints.columns.relation"),
                S.t("scenario.constraints.columns.rhs"),
            ]
        )

    def _rebind_constraints(self, names: list[str]) -> None:
        table = self.constraints_table
        old_count = max(0, table.columnCount() - 3)
        rows = []
        for row in range(table.rowCount()):
            combo = table.cellWidget(row, old_count + 1)
            rows.append(
                (
                    _cell_text(table, row, 0),
                    [_cell_text(table, row, c + 1) for c in range(old_count)],
                    combo.currentData() if isinstance(combo, QComboBox) else "<=",
                    _cell_text(table, row, old_count + 2),
                )
            )
        table.setColumnCount(len(names) + 3)
        table.setHorizontalHeaderLabels(self._constraint_headers(names))
        for row, (name, coefficients, relation, rhs) in enumerate(rows):
            table.setItem(row, 0, _cell(name, centered=False))
            for column in range(len(names)):
                text = coefficients[column] if column < len(coefficients) else "0"
                table.setItem(row, column + 1, _cell(text or "0"))
            table.setCellWidget(row, len(names) + 1, self._relation_combo(relation))
            table.setItem(row, len(names) + 2, _cell(rhs or "0"))
        self._refresh_constraints_state()

    def _relation_combo(self, symbol: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("scenarioConstraintRelation")
        for relation in _RELATION_SYMBOLS:
            combo.addItem(relation, relation)
        combo.setCurrentIndex(max(0, combo.findData(symbol)))
        combo.setAccessibleName(S.t("scenario.constraints.columns.relation"))
        return combo

    def _set_constraints(self, constraints) -> None:
        names = self._variable_names()
        table = self.constraints_table
        table.setColumnCount(len(names) + 3)
        table.setHorizontalHeaderLabels(self._constraint_headers(names))
        table.setRowCount(0)
        for constraint in constraints:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, _cell(constraint.name, centered=False))
            for column in range(len(names)):
                value = (
                    constraint.coefficients[column]
                    if column < len(constraint.coefficients)
                    else 0.0
                )
                table.setItem(row, column + 1, _cell(_format_number(value)))
            table.setCellWidget(row, len(names) + 1, self._relation_combo(constraint.relation))
            table.setItem(row, len(names) + 2, _cell(_format_number(constraint.rhs)))
        self._refresh_constraints_state()

    def _on_add_constraint(self) -> None:
        names = self._variable_names()
        table = self.constraints_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, _cell(f"c{row + 1}", centered=False))
        for column in range(len(names)):
            table.setItem(row, column + 1, _cell("0"))
        table.setCellWidget(row, len(names) + 1, self._relation_combo("<="))
        table.setItem(row, len(names) + 2, _cell("0"))
        self._refresh_constraints_state()

    def _on_remove_constraint(self) -> None:
        table = self.constraints_table
        if table.rowCount() == 0:
            return
        row = table.currentRow()
        if row < 0:
            row = table.rowCount() - 1
        table.removeRow(row)
        self._refresh_constraints_state()

    def _refresh_constraints_state(self) -> None:
        count = self.constraints_table.rowCount()
        self.constraints_table.setVisible(count > 0)
        self.constraints_empty.setVisible(count == 0)
        self.btn_remove_constraint.setEnabled(count > 0)
        header = self.constraints_table.horizontalHeader()
        for column in range(self.constraints_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        if self.constraints_table.columnCount():
            header.setSectionResizeMode(0, QHeaderView.Stretch)
        _fit_table_height(self.constraints_table)

    def _scenario_headers(self, names: list[str]) -> list[str]:
        return (
            [
                S.t("scenario.scenarios.columns.id"),
                S.t("scenario.scenarios.columns.label"),
            ]
            + names
            + [S.t("scenario.scenarios.columns.offset")]
        )

    def _rebind_scenarios(self, names: list[str]) -> None:
        table = self.scenarios_table
        old_count = max(0, table.columnCount() - 3)
        rows = []
        for row in range(table.rowCount()):
            rows.append(
                (
                    _cell_text(table, row, 0),
                    _cell_text(table, row, 1),
                    [_cell_text(table, row, c + 2) for c in range(old_count)],
                    _cell_text(table, row, old_count + 2),
                )
            )
        table.setColumnCount(len(names) + 3)
        table.setHorizontalHeaderLabels(self._scenario_headers(names))
        for row, (identifier, label, coefficients, offset) in enumerate(rows):
            table.setItem(row, 0, _cell(identifier, centered=False))
            table.setItem(row, 1, _cell(label, centered=False))
            for column in range(len(names)):
                text = coefficients[column] if column < len(coefficients) else "0"
                table.setItem(row, column + 2, _cell(text or "0"))
            table.setItem(row, len(names) + 2, _cell(offset or "0"))
        self._refresh_scenarios_state()

    def _set_scenarios(self, scenarios) -> None:
        names = self._variable_names()
        table = self.scenarios_table
        table.setColumnCount(len(names) + 3)
        table.setHorizontalHeaderLabels(self._scenario_headers(names))
        table.setRowCount(0)
        for scenario in scenarios:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, _cell(scenario.scenario_id, centered=False))
            table.setItem(row, 1, _cell(scenario.label, centered=False))
            for column in range(len(names)):
                value = (
                    scenario.coefficients[column] if column < len(scenario.coefficients) else 0.0
                )
                table.setItem(row, column + 2, _cell(_format_number(value)))
            table.setItem(row, len(names) + 2, _cell(_format_number(scenario.offset)))
        self._refresh_scenarios_state()

    def _on_add_scenario(self) -> None:
        names = self._variable_names()
        table = self.scenarios_table
        existing = {_cell_text(table, row, 0).strip() for row in range(table.rowCount())}
        index = table.rowCount() + 1
        identifier = f"s{index}"
        while identifier in existing:
            index += 1
            identifier = f"s{index}"
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, _cell(identifier, centered=False))
        table.setItem(row, 1, _cell("", centered=False))
        for column in range(len(names)):
            table.setItem(row, column + 2, _cell("0"))
        table.setItem(row, len(names) + 2, _cell("0"))
        self._refresh_scenarios_state()

    def _on_remove_scenario(self) -> None:
        table = self.scenarios_table
        if table.rowCount() <= 1:
            return
        row = table.currentRow()
        if row < 0:
            row = table.rowCount() - 1
        table.removeRow(row)
        self._refresh_scenarios_state()

    def _refresh_scenarios_state(self) -> None:
        self.btn_remove_scenario.setEnabled(self.scenarios_table.rowCount() > 1)
        header = self.scenarios_table.horizontalHeader()
        for column in range(self.scenarios_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        if self.scenarios_table.columnCount() > 1:
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        _fit_table_height(self.scenarios_table)

    def _on_shared_objective_toggled(self, checked: bool) -> None:
        self.shared_table.setVisible(checked)
        self.lbl_shared_offset.setVisible(checked)
        self.edit_shared_offset.setVisible(checked)
        if checked:
            self._rebind_shared_objective(self._variable_names())

    # -- form snapshot ---------------------------------------------------
    def current_form(self) -> ScenarioFormInput:
        """Read the form, rejecting incomplete or malformed rows."""
        variables: list[ScenarioVariableInput] = []
        for row in range(self.variables_table.rowCount()):
            name = _cell_text(self.variables_table, row, 0).strip()
            if not name:
                raise ValueError(f"variable name is required on row {row + 1}")
            combo = self.variables_table.cellWidget(row, 4)
            integrality = combo.currentData() if isinstance(combo, QComboBox) else "C"
            variables.append(
                ScenarioVariableInput(
                    name=name,
                    label=_cell_text(self.variables_table, row, 1).strip(),
                    lower_bound=_parse_number(
                        _cell_text(self.variables_table, row, 2),
                        required=False,
                        label=f"{name} lower bound",
                    ),
                    upper_bound=_parse_number(
                        _cell_text(self.variables_table, row, 3),
                        required=False,
                        label=f"{name} upper bound",
                    ),
                    integrality=str(integrality),
                )
            )
        if not variables:
            raise ValueError("at least one decision variable is required")

        count = len(variables)
        constraints: list[ScenarioConstraintInput] = []
        for row in range(self.constraints_table.rowCount()):
            coefficients = tuple(
                float(
                    _parse_number(
                        _cell_text(self.constraints_table, row, column + 1),
                        required=True,
                        label=f"constraint row {row + 1} coefficient {column + 1}",
                    )
                )
                for column in range(count)
            )
            combo = self.constraints_table.cellWidget(row, count + 1)
            relation = combo.currentData() if isinstance(combo, QComboBox) else "<="
            rhs = _parse_number(
                _cell_text(self.constraints_table, row, count + 2),
                required=True,
                label=f"constraint row {row + 1} right-hand side",
            )
            constraints.append(
                ScenarioConstraintInput(
                    name=_cell_text(self.constraints_table, row, 0).strip(),
                    coefficients=coefficients,
                    relation=str(relation),
                    rhs=float(rhs),
                )
            )

        scenarios: list[ScenarioInput] = []
        for row in range(self.scenarios_table.rowCount()):
            identifier = _cell_text(self.scenarios_table, row, 0).strip()
            if not identifier:
                raise ValueError(f"scenario id is required on row {row + 1}")
            coefficients = tuple(
                float(
                    _parse_number(
                        _cell_text(self.scenarios_table, row, column + 2),
                        required=True,
                        label=f"scenario {identifier} coefficient {column + 1}",
                    )
                )
                for column in range(count)
            )
            offset = _parse_number(
                _cell_text(self.scenarios_table, row, count + 2),
                required=True,
                label=f"scenario {identifier} offset",
            )
            scenarios.append(
                ScenarioInput(
                    scenario_id=identifier,
                    label=_cell_text(self.scenarios_table, row, 1).strip(),
                    coefficients=coefficients,
                    offset=float(offset),
                )
            )
        if not scenarios:
            raise ValueError("at least one scenario is required")

        shared_coefficients = None
        shared_offset = None
        if self.chk_shared_objective.isChecked():
            shared_coefficients = tuple(
                float(
                    _parse_number(
                        _cell_text(self.shared_table, 0, column),
                        required=True,
                        label=f"shared objective coefficient {column + 1}",
                    )
                )
                for column in range(count)
            )
            shared_offset = float(
                _parse_number(
                    self.edit_shared_offset.text(),
                    required=True,
                    label="shared objective offset",
                )
            )

        options = ScenarioOptionsInput(
            tolerance=_parse_number(self.edit_tolerance.text(), required=False, label="tolerance"),
            binding_tolerance=_parse_number(
                self.edit_binding_tolerance.text(),
                required=False,
                label="binding tolerance",
            ),
            time_limit_seconds=_parse_number(
                self.edit_time_limit.text(), required=False, label="time limit"
            ),
        )

        return ScenarioFormInput(
            variables=tuple(variables),
            scenarios=tuple(scenarios),
            constraints=tuple(constraints),
            shared_objective_coefficients=shared_coefficients,
            shared_objective_offset=shared_offset,
            options=options,
        )

    def set_form(self, form: ScenarioFormInput) -> None:
        """Replace the editable form with an already validated public problem."""
        self._set_variables(form.variables)
        self._set_constraints(form.constraints)
        self._set_scenarios(form.scenarios)
        has_shared = form.shared_objective_coefficients is not None
        self.chk_shared_objective.setChecked(has_shared)
        if has_shared:
            coefficients = form.shared_objective_coefficients or ()
            for column, value in enumerate(coefficients):
                self.shared_table.setItem(0, column, _cell(_format_number(value)))
            self.edit_shared_offset.setText(_format_number(form.shared_objective_offset or 0.0))
        self.edit_tolerance.setText(_format_optional(form.options.tolerance))
        self.edit_binding_tolerance.setText(_format_optional(form.options.binding_tolerance))
        self.edit_time_limit.setText(_format_optional(form.options.time_limit_seconds))

    @staticmethod
    def _form_from_model(model) -> ScenarioFormInput:
        shared = model.shared_objective
        return ScenarioFormInput(
            variables=tuple(
                ScenarioVariableInput(
                    variable.name,
                    variable.label,
                    variable.bounds.lb,
                    variable.bounds.ub,
                    variable.integrality.value,
                )
                for variable in model.variables
            ),
            scenarios=tuple(
                ScenarioInput(item.id, item.label, item.coefficients, item.offset)
                for item in model.scenarios
            ),
            constraints=tuple(
                ScenarioConstraintInput(
                    item.name, item.coefficients, item.relation.symbol(), item.rhs
                )
                for item in model.shared_constraints
            ),
            shared_objective_coefficients=(shared.coefficients if shared is not None else None),
            shared_objective_offset=(shared.offset if shared is not None else None),
            options=ScenarioOptionsInput(
                tolerance=model.options.tolerance,
                binding_tolerance=model.options.binding_tolerance,
                time_limit_seconds=model.options.time_limit_seconds,
            ),
        )

    # -- actions ---------------------------------------------------------
    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, S.t("scenario.import.dialog_title"), "", "JSON (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("problem document must be a JSON object")
            orientation = payload.get("orientation")
            model = scenario_model_from_public_dict(
                payload,
                expected_orientation=str(orientation),
            )
            capability_id = (
                SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID
                if orientation == MIN_MAX_LOSS_ORIENTATION
                else SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID
            )
            self.set_capability_id(capability_id)
            self.set_form(self._form_from_model(model))
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(
                self,
                S.t("scenario.import.error_title"),
                S.t(
                    "scenario.import.error_body",
                    detail=localized_error_detail("scenario_import", exc),
                ),
            )

    def _on_export_json(self) -> None:
        try:
            payload = build_problem_payload(
                self.current_form(), orientation=self._view_model.orientation
            )
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("scenario.validation.title"),
                S.t(
                    "scenario.validation.body",
                    detail=localized_error_detail("scenario_validation", exc),
                ),
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            S.t("scenario.export.dialog_title"),
            S.t("scenario.export.default_name"),
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                S.t("scenario.export.error_title"),
                S.t(
                    "scenario.export.error_body",
                    detail=localized_error_detail("scenario_export", exc),
                ),
            )

    def _on_solve(self) -> None:
        try:
            form = self.current_form()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("scenario.validation.title"),
                S.t(
                    "scenario.validation.body",
                    detail=localized_error_detail("scenario_validation", exc),
                ),
            )
            return
        self._view_model.submit(form)

    def _on_cancel(self) -> None:
        self._view_model.cancel()
        self.solve_notice.setText(S.t("scenario.solve.cancelled"))

    def _on_busy_changed(self, busy: bool) -> None:
        self.btn_solve.setEnabled(not busy and self._view_model.is_available())
        self.btn_cancel.setVisible(busy)
        self.btn_cancel.setEnabled(busy)
        for widget in (
            self.radio_min_max,
            self.radio_max_min,
            self.btn_add_variable,
            self.btn_remove_variable,
            self.btn_add_constraint,
            self.btn_remove_constraint,
            self.btn_add_scenario,
            self.btn_remove_scenario,
        ):
            widget.setEnabled(not busy)
        if busy:
            self.solve_notice.setText(S.t("scenario.solve.running"))
        elif self.solve_notice.text() == S.t("scenario.solve.running"):
            self.solve_notice.clear()
        self._refresh_scenarios_state()
        self._refresh_constraints_state()

    def _on_succeeded(self, envelope: object) -> None:
        self.solve_notice.clear()
        self.solve_completed.emit(envelope)

    def _on_rejected(self, error: object) -> None:
        self.solve_notice.clear()
        self.solve_rejected.emit(error)

    def _on_failed(self, detail: str) -> None:
        self.solve_notice.clear()
        QMessageBox.warning(
            self,
            S.t("scenario.validation.title"),
            S.t(
                "scenario.validation.body",
                detail=localized_error_detail("scenario_validation", detail),
            ),
        )

    def _show_info(self, topic: str) -> None:
        dialog = _InfoDialog(
            S.t(f"scenario.{topic}.info_title"),
            S.t(f"scenario.{topic}.info_body"),
            S.t(f"scenario.{topic}.info_html"),
            self,
        )
        dialog.exec()

    # -- localization and theme ------------------------------------------
    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:26px; font-weight:700'>{S.t('scenario.header.title')}</span>"
        )
        self.intro_section.set_title(S.t("scenario.header.section"))
        self.intro_text.setText(S.t("scenario.header.description"))
        self.btn_import_json.setText(S.t("scenario.import.button"))
        self.btn_export_json.setText(S.t("scenario.export.button"))
        self.btn_json_info.setToolTip(S.t("scenario.import.info_tooltip"))
        self.btn_example.setText(S.t("scenario.header.buttons.example"))
        self.btn_problem.setText(S.t("scenario.header.buttons.problem"))

        self.orientation_section.set_title(S.t("scenario.orientation.section"))
        self.orientation_hint.setText(S.t("scenario.orientation.hint"))
        self.btn_orientation_info.setToolTip(S.t("scenario.orientation.info_tooltip"))
        self.radio_min_max.setText(S.t("scenario.orientation.min_max_loss"))
        self.radio_min_max.setAccessibleName(S.t("scenario.orientation.min_max_loss"))
        self.min_max_description.setText(S.t("scenario.orientation.min_max_loss_description"))
        self.radio_max_min.setText(S.t("scenario.orientation.max_min_reward"))
        self.radio_max_min.setAccessibleName(S.t("scenario.orientation.max_min_reward"))
        self.max_min_description.setText(S.t("scenario.orientation.max_min_reward_description"))
        self.capability_label.setText(
            S.t("scenario.orientation.capability", capability=self._view_model.capability_id)
        )

        self.variables_section.set_title(S.t("scenario.variables.section"))
        self.variables_hint.setText(S.t("scenario.variables.hint"))
        self.btn_add_variable.setText(S.t("scenario.variables.add"))
        self.btn_remove_variable.setText(S.t("scenario.variables.remove"))
        self._refresh_variable_headers()

        self.shared_section.set_title(S.t("scenario.shared_objective.section"))
        self.shared_hint.setText(S.t("scenario.shared_objective.hint"))
        self.chk_shared_objective.setText(S.t("scenario.shared_objective.enable"))
        self.lbl_shared_offset.setText(S.t("scenario.shared_objective.offset"))
        self.edit_shared_offset.setAccessibleName(S.t("scenario.shared_objective.offset"))

        self.constraints_section.set_title(S.t("scenario.constraints.section"))
        self.constraints_hint.setText(S.t("scenario.constraints.hint"))
        self.constraints_empty.setText(S.t("scenario.constraints.empty"))
        self.btn_add_constraint.setText(S.t("scenario.constraints.add"))
        self.btn_remove_constraint.setText(S.t("scenario.constraints.remove"))
        if self.constraints_table.columnCount():
            self.constraints_table.setHorizontalHeaderLabels(
                self._constraint_headers(self._variable_names())
            )

        self.scenarios_section.set_title(S.t("scenario.scenarios.section"))
        self.scenarios_hint.setText(S.t("scenario.scenarios.hint"))
        self.btn_scenarios_info.setToolTip(S.t("scenario.scenarios.info_tooltip"))
        self.btn_add_scenario.setText(S.t("scenario.scenarios.add"))
        self.btn_remove_scenario.setText(S.t("scenario.scenarios.remove"))
        if self.scenarios_table.columnCount():
            self.scenarios_table.setHorizontalHeaderLabels(
                self._scenario_headers(self._variable_names())
            )

        self.options_section.set_title(S.t("scenario.options.section"))
        self.options_hint.setText(S.t("scenario.options.hint"))
        self.btn_options_info.setToolTip(S.t("scenario.options.info_tooltip"))
        self.lbl_tolerance.setText(S.t("scenario.options.tolerance"))
        self.edit_tolerance.setAccessibleName(S.t("scenario.options.tolerance"))
        self.lbl_binding_tolerance.setText(S.t("scenario.options.binding_tolerance"))
        self.edit_binding_tolerance.setAccessibleName(S.t("scenario.options.binding_tolerance"))
        self.lbl_time_limit.setText(S.t("scenario.options.time_limit"))
        self.edit_time_limit.setPlaceholderText(S.t("scenario.options.time_limit_placeholder"))
        self.edit_time_limit.setAccessibleName(S.t("scenario.options.time_limit"))

        self.btn_solve.setText(S.t("scenario.solve.button"))
        self.btn_cancel.setText(S.t("scenario.solve.cancel"))
        self._refresh_availability()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.dependency_notice.setStyleSheet(f"color: {t.warning}; font-weight: 600;")
        self.capability_label.setStyleSheet(f"color: {t.text_faint};")
        self.solve_notice.setStyleSheet(f"color: {t.text_muted};")
        for label in (
            self.intro_text,
            self.orientation_hint,
            self.min_max_description,
            self.max_min_description,
            self.variables_hint,
            self.shared_hint,
            self.constraints_hint,
            self.constraints_empty,
            self.scenarios_hint,
            self.options_hint,
        ):
            label.setStyleSheet(f"color: {t.text_muted};")
