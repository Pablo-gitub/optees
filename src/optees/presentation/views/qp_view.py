"""Formulation view for the continuous convex quadratic-programming capability.

The view owns presentation only. It builds a :class:`QPModel` from the form,
hands it to the Stage A application use case, and forwards the returned
solution. Curvature, symmetry, feasibility, and status semantics all remain
with the domain, the use case, and the registered validator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.qp.constraint import QPConstraint
from optees.domain.entities.qp.objective import QPObjective
from optees.domain.entities.qp.variable import QPVariable
from optees.domain.models.qp.qp_model import QPModel, QPOptions
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.presentation.error_feedback import localized_error_detail
from optees.presentation.views.lp_view.section import Section
from optees.utility.qp_json_io import qp_model_from_json, qp_model_to_json

# Public schema version 1 limits, mirrored here only to keep the form from
# offering an input the contract would reject.
MAX_VARIABLES = 500
MAX_CONSTRAINTS = 1000

# Above this many variables the dense n x n editor stops being usable on a
# desktop page, so the view keeps the imported model and hides the grids.
MATRIX_EDITOR_LIMIT = 12

_NAME_WIDTH = 120
_NUMERIC_WIDTH = 120
_REMOVE_WIDTH = 28
_MATRIX_COLUMN_WIDTH = 92


def _parse_number(text: str, *, required: bool, label: str) -> Optional[float]:
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
    if value is None:
        return ""
    return f"{float(value):.10g}"


def _format_number(value: float) -> str:
    return f"{float(value):.10g}"


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _make_info_button(object_name: str, parent: Optional[QWidget] = None) -> QPushButton:
    button = QPushButton("i", parent)
    button.setObjectName(object_name)
    button.setProperty("variant", "info")
    button.setFixedSize(24, 24)
    button.setCursor(Qt.PointingHandCursor)
    return button


def _fit_table_height(table: QTableWidget, *, max_rows: int = 8) -> None:
    """Size a grid to its rows, scrolling only once it grows past `max_rows`."""
    visible_rows = min(table.rowCount(), max_rows)
    rows = sum(table.rowHeight(row) for row in range(visible_rows))
    header = table.horizontalHeader().height()
    table.setFixedHeight(header + rows + 2 * table.frameWidth() + 2)


def _make_remove_button(tooltip_key: str) -> QToolButton:
    button = QToolButton()
    button.setObjectName("rowRemoveButton")
    icon = QIcon.fromTheme("edit-delete")
    if icon.isNull():
        button.setText("x")
    else:
        button.setIcon(icon)
    button.setAutoRaise(True)
    button.setFixedSize(_REMOVE_WIDTH, 28)
    button.setToolTip(S.t(tooltip_key))
    return button


class _InfoDialog(QDialog):
    """Educational dialog reused by every info button on this page."""

    def __init__(self, title: str, intro: str, html: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setMinimumSize(560, 400)
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


class _VariableRow(QWidget):
    remove_requested = Signal(int)
    name_changed = Signal()

    def __init__(self, index: int, variable: QPVariable, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.lbl_index = QLabel(str(index))
        self.lbl_index.setFixedWidth(24)
        self.lbl_index.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.edit_name = QLineEdit(variable.name)
        self.edit_name.setObjectName("qpVariableName")
        self.edit_name.setFixedWidth(_NAME_WIDTH)
        self.edit_name.editingFinished.connect(self.name_changed.emit)

        self.edit_label = QLineEdit(variable.label)
        self.edit_label.setObjectName("qpVariableLabel")
        self.edit_label.setMinimumWidth(150)

        self.edit_lower = QLineEdit(_format_optional(variable.bounds.lb))
        self.edit_lower.setObjectName("qpVariableLowerBound")
        self.edit_lower.setFixedWidth(_NUMERIC_WIDTH)

        self.edit_upper = QLineEdit(_format_optional(variable.bounds.ub))
        self.edit_upper.setObjectName("qpVariableUpperBound")
        self.edit_upper.setFixedWidth(_NUMERIC_WIDTH)

        self.btn_remove = _make_remove_button("qp.variables.remove")
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self._index))

        layout.addWidget(self.lbl_index)
        layout.addWidget(self.edit_name)
        layout.addWidget(self.edit_label, 1)
        layout.addWidget(self.edit_lower)
        layout.addWidget(self.edit_upper)
        layout.addWidget(self.btn_remove)
        self.refresh_strings()

    def set_index(self, index: int) -> None:
        self._index = index
        self.lbl_index.setText(str(index))

    def variable(self) -> QPVariable:
        name = self.edit_name.text().strip()
        if not name:
            raise ValueError(f"variable {self._index} name is required")
        lower = _parse_number(self.edit_lower.text(), required=False, label=f"{name} lower bound")
        upper = _parse_number(self.edit_upper.text(), required=False, label=f"{name} upper bound")
        return QPVariable(name=name, label=self.edit_label.text(), bounds=Bounds(lower, upper))

    def refresh_strings(self) -> None:
        self.edit_name.setPlaceholderText(S.t("qp.variables.name_placeholder"))
        self.edit_name.setAccessibleName(S.t("qp.variables.columns.name"))
        self.edit_label.setPlaceholderText(S.t("qp.variables.label_placeholder"))
        self.edit_label.setAccessibleName(S.t("qp.variables.columns.label"))
        self.edit_lower.setPlaceholderText(S.t("qp.variables.bound_placeholder"))
        self.edit_lower.setAccessibleName(S.t("qp.variables.columns.lower"))
        self.edit_upper.setPlaceholderText(S.t("qp.variables.bound_placeholder"))
        self.edit_upper.setAccessibleName(S.t("qp.variables.columns.upper"))
        self.btn_remove.setToolTip(S.t("qp.variables.remove"))


class _VariablesSection(Section):
    add_requested = Signal()
    structure_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)
        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self.body.addWidget(self._hint)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.col_index = QLabel()
        self.col_name = QLabel()
        self.col_label = QLabel()
        self.col_lower = QLabel()
        self.col_upper = QLabel()
        self.col_index.setFixedWidth(24)
        self.col_name.setFixedWidth(_NAME_WIDTH)
        self.col_lower.setFixedWidth(_NUMERIC_WIDTH)
        self.col_upper.setFixedWidth(_NUMERIC_WIDTH)
        header.addWidget(self.col_index)
        header.addWidget(self.col_name)
        header.addWidget(self.col_label, 1)
        header.addWidget(self.col_lower)
        header.addWidget(self.col_upper)
        header.addSpacing(_REMOVE_WIDTH)
        self.body.addLayout(header)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)
        self.body.addLayout(self._rows_layout)

        footer = QHBoxLayout()
        self.limit_notice = QLabel()
        self.limit_notice.setWordWrap(True)
        self.limit_notice.setVisible(False)
        footer.addWidget(self.limit_notice)
        footer.addStretch(1)
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("qpAddVariableButton")
        self.btn_add.clicked.connect(self.add_requested.emit)
        footer.addWidget(self.btn_add)
        self.body.addLayout(footer)
        self.refresh_strings()

    def set_variables(self, variables) -> None:
        _clear_layout(self._rows_layout)
        for index, variable in enumerate(variables):
            row = _VariableRow(index, variable)
            row.remove_requested.connect(self.remove_row)
            row.name_changed.connect(self.structure_changed.emit)
            self._rows_layout.addWidget(row)
        self._update_limit_notice()

    def rows(self) -> list[_VariableRow]:
        result: list[_VariableRow] = []
        for index in range(self._rows_layout.count()):
            widget = self._rows_layout.itemAt(index).widget()
            if isinstance(widget, _VariableRow):
                result.append(widget)
        return result

    def remove_row(self, index: int) -> None:
        rows = self.rows()
        if len(rows) <= 1 or not 0 <= index < len(rows):
            return
        row = rows[index]
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        for new_index, remaining in enumerate(self.rows()):
            remaining.set_index(new_index)
        self._update_limit_notice()
        self.structure_changed.emit()

    def _update_limit_notice(self) -> None:
        reached = len(self.rows()) >= MAX_VARIABLES
        self.btn_add.setEnabled(not reached)
        self.limit_notice.setVisible(reached)

    def refresh_strings(self) -> None:
        self.set_title(S.t("qp.variables.section"))
        self._hint.setText(S.t("qp.variables.hint"))
        self.col_index.setText(S.t("qp.variables.columns.index"))
        self.col_name.setText(S.t("qp.variables.columns.name"))
        self.col_label.setText(S.t("qp.variables.columns.label"))
        self.col_lower.setText(S.t("qp.variables.columns.lower"))
        self.col_upper.setText(S.t("qp.variables.columns.upper"))
        self.btn_add.setText(S.t("qp.variables.add"))
        self.limit_notice.setText(S.t("qp.variables.limit_reached", limit=MAX_VARIABLES))
        for row in self.rows():
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        t = tokens(theme.is_dark())
        self._hint.setStyleSheet(f"color: {t.text_muted};")
        self.limit_notice.setStyleSheet(f"color: {t.warning};")


class _SymmetricMatrixTable(QTableWidget):
    """Editor for the Hessian ``Q`` that keeps the entered matrix symmetric.

    Mirroring is a data-entry convenience, not a mathematical correction: the
    domain still validates symmetry and curvature on the submitted matrix.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._mirroring = False
        self.setObjectName("qpQuadraticMatrixTable")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(False)
        self.itemChanged.connect(self._on_item_changed)

    def set_size(self, size: int, headers: list[str]) -> None:
        self._mirroring = True
        try:
            previous = self.values(fallback=0.0)
            self.setRowCount(size)
            self.setColumnCount(size)
            self.setHorizontalHeaderLabels(headers)
            self.setVerticalHeaderLabels(headers)
            for row in range(size):
                for column in range(size):
                    if row < len(previous) and column < len(previous[row]):
                        value = previous[row][column]
                    else:
                        value = 1.0 if row == column else 0.0
                    self._set_cell(row, column, _format_number(value))
                    self.setColumnWidth(column, _MATRIX_COLUMN_WIDTH)
        finally:
            self._mirroring = False

    def set_matrix(self, matrix, headers: list[str]) -> None:
        self._mirroring = True
        try:
            size = len(matrix)
            self.setRowCount(size)
            self.setColumnCount(size)
            self.setHorizontalHeaderLabels(headers)
            self.setVerticalHeaderLabels(headers)
            for row in range(size):
                for column in range(size):
                    self._set_cell(row, column, _format_number(matrix[row][column]))
                    self.setColumnWidth(column, _MATRIX_COLUMN_WIDTH)
        finally:
            self._mirroring = False

    def values(self, *, fallback: Optional[float] = None) -> list[list[float]]:
        matrix: list[list[float]] = []
        for row in range(self.rowCount()):
            values: list[float] = []
            for column in range(self.columnCount()):
                item = self.item(row, column)
                text = item.text() if item is not None else ""
                if fallback is None:
                    parsed = _parse_number(
                        text,
                        required=True,
                        label=f"quadratic matrix entry [{row}][{column}]",
                    )
                    values.append(float(parsed))
                else:
                    try:
                        parsed = _parse_number(text, required=False, label="")
                    except ValueError:
                        parsed = None
                    values.append(float(parsed) if parsed is not None else fallback)
            matrix.append(values)
        return matrix

    def _set_cell(self, row: int, column: int, text: str) -> None:
        item = self.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, column, item)
        item.setText(text)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._mirroring:
            return
        row, column = item.row(), item.column()
        if row == column:
            return
        self._mirroring = True
        try:
            self._set_cell(column, row, item.text())
        finally:
            self._mirroring = False


class QPView(QWidget):
    """Formulation page for `qp.continuous`."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solve_usecase = None
        self._model: Optional[QPModel] = None
        self._compact = False

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
        self.dependency_notice.setObjectName("qpDependencyNotice")
        self.dependency_notice.setWordWrap(True)
        self.dependency_notice.setVisible(False)
        root.addWidget(self.dependency_notice)

        intro = Section()
        intro_header = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        intro_header.addWidget(self.intro_text, 1)
        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("qpImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_export_json = QPushButton()
        self.btn_export_json.setObjectName("qpExportJsonButton")
        self.btn_export_json.clicked.connect(self._on_export_json)
        self.btn_json_info = _make_info_button("qpJsonInfoButton")
        self.btn_json_info.clicked.connect(lambda: self._show_info("import"))
        intro_header.addWidget(self.btn_import_json)
        intro_header.addWidget(self.btn_export_json)
        intro_header.addWidget(self.btn_json_info)
        intro.body.addLayout(intro_header)
        intro_actions = QHBoxLayout()
        intro_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("qpExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("qpProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        intro_actions.addWidget(self.btn_example)
        intro_actions.addWidget(self.btn_problem)
        intro.body.addLayout(intro_actions)
        self.intro_section = intro
        root.addWidget(intro)

        self.variables_section = _VariablesSection()
        self.variables_section.add_requested.connect(self._add_variable)
        self.variables_section.structure_changed.connect(self._sync_structure)
        root.addWidget(self.variables_section)

        objective = Section()
        objective_header = QHBoxLayout()
        self.objective_hint = QLabel()
        self.objective_hint.setWordWrap(True)
        objective_header.addWidget(self.objective_hint, 1)
        self.btn_objective_info = _make_info_button("qpObjectiveInfoButton")
        self.btn_objective_info.clicked.connect(lambda: self._show_info("objective"))
        objective_header.addWidget(self.btn_objective_info)
        objective.body.addLayout(objective_header)

        sense_row = QHBoxLayout()
        self.lbl_sense = QLabel()
        self.combo_sense = QComboBox()
        self.combo_sense.setObjectName("qpObjectiveSense")
        self.combo_sense.addItem("", ObjectiveSense.MIN.value)
        self.combo_sense.addItem("", ObjectiveSense.MAX.value)
        self.combo_sense.currentIndexChanged.connect(self._update_formula)
        self.lbl_offset = QLabel()
        self.edit_offset = QLineEdit("0")
        self.edit_offset.setObjectName("qpObjectiveOffset")
        self.edit_offset.setFixedWidth(_NUMERIC_WIDTH)
        sense_row.addWidget(self.lbl_sense)
        sense_row.addWidget(self.combo_sense)
        sense_row.addSpacing(16)
        sense_row.addWidget(self.lbl_offset)
        sense_row.addWidget(self.edit_offset)
        sense_row.addStretch(1)
        objective.body.addLayout(sense_row)

        self.formula_label = QLabel()
        self.formula_label.setObjectName("qpObjectiveFormula")
        self.formula_label.setWordWrap(True)
        objective.body.addWidget(self.formula_label)

        self.matrix_label = QLabel()
        objective.body.addWidget(self.matrix_label)
        self.matrix_hint = QLabel()
        self.matrix_hint.setWordWrap(True)
        objective.body.addWidget(self.matrix_hint)
        self.matrix_table = _SymmetricMatrixTable()
        objective.body.addWidget(self.matrix_table)

        self.linear_label = QLabel()
        objective.body.addWidget(self.linear_label)
        self.linear_table = QTableWidget(1, 0)
        self.linear_table.setObjectName("qpLinearCoefficientsTable")
        self.linear_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.linear_table.verticalHeader().setVisible(False)
        objective.body.addWidget(self.linear_table)

        self.large_matrix_notice = QLabel()
        self.large_matrix_notice.setObjectName("qpLargeMatrixNotice")
        self.large_matrix_notice.setWordWrap(True)
        self.large_matrix_notice.setVisible(False)
        objective.body.addWidget(self.large_matrix_notice)
        self.objective_section = objective
        root.addWidget(objective)

        constraints = Section()
        constraints_header = QHBoxLayout()
        self.constraints_hint = QLabel()
        self.constraints_hint.setWordWrap(True)
        constraints_header.addWidget(self.constraints_hint, 1)
        constraints.body.addLayout(constraints_header)
        self.constraints_table = QTableWidget(0, 0)
        self.constraints_table.setObjectName("qpConstraintsTable")
        self.constraints_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.constraints_table.verticalHeader().setVisible(False)
        constraints.body.addWidget(self.constraints_table)
        self.constraints_empty = QLabel()
        self.constraints_empty.setObjectName("qpConstraintsEmpty")
        self.constraints_empty.setWordWrap(True)
        constraints.body.addWidget(self.constraints_empty)
        constraints_footer = QHBoxLayout()
        self.constraints_limit_notice = QLabel()
        self.constraints_limit_notice.setWordWrap(True)
        self.constraints_limit_notice.setVisible(False)
        constraints_footer.addWidget(self.constraints_limit_notice)
        constraints_footer.addStretch(1)
        self.btn_remove_constraint = QPushButton()
        self.btn_remove_constraint.setObjectName("qpRemoveConstraintButton")
        self.btn_remove_constraint.clicked.connect(self._remove_selected_constraint)
        self.btn_add_constraint = QPushButton()
        self.btn_add_constraint.setObjectName("qpAddConstraintButton")
        self.btn_add_constraint.clicked.connect(self._add_constraint)
        constraints_footer.addWidget(self.btn_remove_constraint)
        constraints_footer.addWidget(self.btn_add_constraint)
        constraints.body.addLayout(constraints_footer)
        self.constraints_section = constraints
        root.addWidget(constraints)

        solver = Section()
        solver_header = QHBoxLayout()
        self.solver_hint = QLabel()
        self.solver_hint.setWordWrap(True)
        solver_header.addWidget(self.solver_hint, 1)
        self.btn_solver_info = _make_info_button("qpSolverInfoButton")
        self.btn_solver_info.clicked.connect(lambda: self._show_info("solver"))
        solver_header.addWidget(self.btn_solver_info)
        solver.body.addLayout(solver_header)
        solver_row = QHBoxLayout()
        self.lbl_method = QLabel()
        self.combo_method = QComboBox()
        self.combo_method.setObjectName("qpSolverMethod")
        self.combo_method.addItem("osqp", "osqp")
        self.lbl_tolerance = QLabel()
        self.edit_tolerance = QLineEdit("1e-7")
        self.edit_tolerance.setObjectName("qpTolerance")
        self.edit_tolerance.setFixedWidth(_NUMERIC_WIDTH)
        self.lbl_iterations = QLabel()
        self.edit_iterations = QLineEdit("4000")
        self.edit_iterations.setObjectName("qpMaxIterations")
        self.edit_iterations.setFixedWidth(_NUMERIC_WIDTH)
        self.lbl_time_limit = QLabel()
        self.edit_time_limit = QLineEdit("60")
        self.edit_time_limit.setObjectName("qpTimeLimit")
        self.edit_time_limit.setFixedWidth(_NUMERIC_WIDTH)
        for label, editor in (
            (self.lbl_method, self.combo_method),
            (self.lbl_tolerance, self.edit_tolerance),
            (self.lbl_iterations, self.edit_iterations),
            (self.lbl_time_limit, self.edit_time_limit),
        ):
            solver_row.addWidget(label)
            solver_row.addWidget(editor)
            solver_row.addSpacing(16)
        solver_row.addStretch(1)
        solver.body.addLayout(solver_row)
        self.solver_section = solver
        root.addWidget(solver)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_solve = QPushButton()
        self.btn_solve.setObjectName("qpSolveButton")
        self.btn_solve.setDefault(True)
        self.btn_solve.clicked.connect(self._on_solve)
        actions.addWidget(self.btn_solve)
        root.addLayout(actions)
        root.addStretch(1)

        self.set_model(_default_model())
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    def set_solve_usecase(self, usecase) -> None:
        self._solve_usecase = usecase

    def set_backend_available(self, available: bool) -> None:
        """Report backend availability decided by the composition root."""
        self.dependency_notice.setVisible(not available)
        self.btn_solve.setEnabled(bool(available))

    # ------------------------------------------------------------------
    # Model <-> form
    # ------------------------------------------------------------------
    def set_model(self, model: QPModel) -> None:
        self._model = model
        self._compact = len(model.variables) > MATRIX_EDITOR_LIMIT
        self.variables_section.set_variables(model.variables)
        self.combo_sense.setCurrentIndex(
            max(0, self.combo_sense.findData(model.objective.sense.value))
        )
        self.edit_offset.setText(_format_number(model.objective.offset))
        headers = [variable.name for variable in model.variables]
        if not self._compact:
            self.matrix_table.set_matrix(model.objective.quadratic_matrix, headers)
            self._set_linear_coefficients(model.objective.linear_coefs, headers)
            self._set_constraints(model.constraints, headers)
        self.combo_method.setCurrentIndex(max(0, self.combo_method.findData(model.options.method)))
        self.edit_tolerance.setText(_format_number(model.options.tolerance))
        self.edit_iterations.setText(str(model.options.max_iterations))
        self.edit_time_limit.setText(_format_number(model.options.time_limit_seconds))
        self._apply_compact_state()
        self._fit_grids()
        self._update_formula()

    def _fit_grids(self) -> None:
        for table in (self.matrix_table, self.linear_table, self.constraints_table):
            _fit_table_height(table)

    def current_model(self) -> QPModel:
        variables = [row.variable() for row in self.variables_section.rows()]
        sense = ObjectiveSense.from_str(self.combo_sense.currentData())
        offset = _parse_number(self.edit_offset.text(), required=False, label="objective offset") or 0.0
        options = self._current_options()

        if self._compact:
            if self._model is None:
                raise ValueError("no quadratic model is loaded")
            return QPModel.from_parts(
                variables=self._model.variables,
                objective=self._model.objective,
                constraints=self._model.constraints,
                options=options,
            )

        objective = QPObjective(
            sense=sense,
            linear_coefs=tuple(self._linear_coefficients()),
            quadratic_matrix=tuple(tuple(row) for row in self.matrix_table.values()),
            offset=offset,
        )
        return QPModel.from_parts(
            variables=variables,
            objective=objective,
            constraints=self._constraints_from_table(),
            options=options,
        )

    def _current_options(self) -> QPOptions:
        tolerance = _parse_number(self.edit_tolerance.text(), required=True, label="tolerance")
        time_limit = _parse_number(self.edit_time_limit.text(), required=True, label="time limit")
        raw_iterations = self.edit_iterations.text().strip()
        try:
            max_iterations = int(raw_iterations)
        except ValueError as exc:
            raise ValueError("max iterations must be a positive integer") from exc
        return QPOptions(
            method=str(self.combo_method.currentData()),
            tolerance=float(tolerance),
            max_iterations=max_iterations,
            time_limit_seconds=float(time_limit),
        )

    # ------------------------------------------------------------------
    # Objective grids
    # ------------------------------------------------------------------
    def _set_linear_coefficients(self, coefficients, headers: list[str]) -> None:
        self.linear_table.setColumnCount(len(headers))
        self.linear_table.setHorizontalHeaderLabels(headers)
        self.linear_table.setRowCount(1)
        for index in range(len(headers)):
            value = coefficients[index] if index < len(coefficients) else 0.0
            item = QTableWidgetItem(_format_number(value))
            item.setTextAlignment(Qt.AlignCenter)
            self.linear_table.setItem(0, index, item)
            self.linear_table.setColumnWidth(index, _MATRIX_COLUMN_WIDTH)

    def _linear_coefficients(self) -> list[float]:
        values: list[float] = []
        for index in range(self.linear_table.columnCount()):
            item = self.linear_table.item(0, index)
            text = item.text() if item is not None else ""
            parsed = _parse_number(text, required=True, label=f"objective linear coefficient {index}")
            values.append(float(parsed))
        return values

    # ------------------------------------------------------------------
    # Constraints grid
    # ------------------------------------------------------------------
    def _constraint_headers(self, variable_names: list[str]) -> list[str]:
        return (
            [S.t("qp.constraints.columns.name")]
            + variable_names
            + [S.t("qp.constraints.columns.relation"), S.t("qp.constraints.columns.rhs")]
        )

    def _set_constraints(self, constraints, variable_names: list[str]) -> None:
        self.constraints_table.setColumnCount(len(variable_names) + 3)
        self.constraints_table.setHorizontalHeaderLabels(
            self._constraint_headers(variable_names) + [""]
        )
        self.constraints_table.setRowCount(0)
        for constraint in constraints:
            self._append_constraint_row(constraint, variable_names)
        self._update_constraints_state()

    def _append_constraint_row(self, constraint: QPConstraint, variable_names: list[str]) -> None:
        row = self.constraints_table.rowCount()
        self.constraints_table.insertRow(row)
        name_item = QTableWidgetItem(constraint.name)
        self.constraints_table.setItem(row, 0, name_item)
        for index in range(len(variable_names)):
            value = constraint.coefs[index] if index < len(constraint.coefs) else 0.0
            item = QTableWidgetItem(_format_number(value))
            item.setTextAlignment(Qt.AlignCenter)
            self.constraints_table.setItem(row, index + 1, item)
        relation_combo = QComboBox()
        relation_combo.setObjectName("qpConstraintRelation")
        for relation in Relation:
            relation_combo.addItem(relation.symbol(), relation.symbol())
        relation_combo.setCurrentIndex(max(0, relation_combo.findData(constraint.relation.symbol())))
        self.constraints_table.setCellWidget(row, len(variable_names) + 1, relation_combo)
        rhs_item = QTableWidgetItem(_format_number(constraint.rhs))
        rhs_item.setTextAlignment(Qt.AlignCenter)
        self.constraints_table.setItem(row, len(variable_names) + 2, rhs_item)

    def _constraints_from_table(self) -> list[QPConstraint]:
        variable_count = self.constraints_table.columnCount() - 3
        constraints: list[QPConstraint] = []
        for row in range(self.constraints_table.rowCount()):
            name_item = self.constraints_table.item(row, 0)
            name = name_item.text().strip() if name_item is not None else ""
            coefficients: list[float] = []
            for index in range(variable_count):
                item = self.constraints_table.item(row, index + 1)
                text = item.text() if item is not None else ""
                parsed = _parse_number(
                    text,
                    required=True,
                    label=f"constraint {row} coefficient {index}",
                )
                coefficients.append(float(parsed))
            combo = self.constraints_table.cellWidget(row, variable_count + 1)
            symbol = combo.currentData() if isinstance(combo, QComboBox) else "<="
            rhs_item = self.constraints_table.item(row, variable_count + 2)
            rhs_text = rhs_item.text() if rhs_item is not None else ""
            rhs = _parse_number(rhs_text, required=True, label=f"constraint {row} right-hand side")
            constraints.append(
                QPConstraint(
                    name=name,
                    coefs=tuple(coefficients),
                    relation=Relation.from_symbol(str(symbol)),
                    rhs=float(rhs),
                )
            )
        return constraints

    def _add_constraint(self) -> None:
        if self._compact or self.constraints_table.rowCount() >= MAX_CONSTRAINTS:
            return
        names = self._variable_names()
        index = self.constraints_table.rowCount() + 1
        self._append_constraint_row(
            QPConstraint(name=f"c{index}", coefs=tuple(0.0 for _ in names), relation=Relation.LE),
            names,
        )
        self._update_constraints_state()

    def _remove_selected_constraint(self) -> None:
        row = self.constraints_table.currentRow()
        if row < 0:
            row = self.constraints_table.rowCount() - 1
        if row < 0:
            return
        self.constraints_table.removeRow(row)
        self._update_constraints_state()

    def _update_constraints_state(self) -> None:
        count = self.constraints_table.rowCount()
        self.constraints_table.setVisible(count > 0 and not self._compact)
        self.constraints_empty.setVisible(count == 0 and not self._compact)
        self.btn_remove_constraint.setEnabled(count > 0 and not self._compact)
        reached = count >= MAX_CONSTRAINTS
        self.btn_add_constraint.setEnabled(not reached and not self._compact)
        self.constraints_limit_notice.setVisible(reached)
        _fit_table_height(self.constraints_table)

    # ------------------------------------------------------------------
    # Structure synchronization
    # ------------------------------------------------------------------
    def _variable_names(self) -> list[str]:
        names: list[str] = []
        for index, row in enumerate(self.variables_section.rows()):
            names.append(row.edit_name.text().strip() or f"x{index + 1}")
        return names

    def _sync_structure(self) -> None:
        """Keep Q, c, and the constraint columns bound to the declared variables."""
        if self._compact:
            return
        names = self._variable_names()
        size = len(names)
        self.matrix_table.set_size(size, names)
        previous = [
            [
                (self.constraints_table.item(row, column + 1).text()
                 if self.constraints_table.item(row, column + 1) is not None else "0")
                for column in range(max(0, self.constraints_table.columnCount() - 3))
            ]
            for row in range(self.constraints_table.rowCount())
        ]
        relations = [
            self.constraints_table.cellWidget(row, self.constraints_table.columnCount() - 2)
            for row in range(self.constraints_table.rowCount())
        ]
        rhs_values = [
            (self.constraints_table.item(row, self.constraints_table.columnCount() - 1).text()
             if self.constraints_table.item(row, self.constraints_table.columnCount() - 1) is not None
             else "0")
            for row in range(self.constraints_table.rowCount())
        ]
        constraint_names = [
            (self.constraints_table.item(row, 0).text()
             if self.constraints_table.item(row, 0) is not None else "")
            for row in range(self.constraints_table.rowCount())
        ]

        linear_texts = [
            (self.linear_table.item(0, column).text()
             if self.linear_table.item(0, column) is not None else "0")
            for column in range(self.linear_table.columnCount())
        ]
        self.linear_table.setColumnCount(size)
        self.linear_table.setHorizontalHeaderLabels(names)
        self.linear_table.setRowCount(1)
        for column in range(size):
            text = linear_texts[column] if column < len(linear_texts) else "0"
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            self.linear_table.setItem(0, column, item)
            self.linear_table.setColumnWidth(column, _MATRIX_COLUMN_WIDTH)

        self.constraints_table.setColumnCount(size + 3)
        self.constraints_table.setHorizontalHeaderLabels(self._constraint_headers(names) + [""])
        for row in range(self.constraints_table.rowCount()):
            self.constraints_table.setItem(row, 0, QTableWidgetItem(constraint_names[row]))
            for column in range(size):
                text = previous[row][column] if column < len(previous[row]) else "0"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.constraints_table.setItem(row, column + 1, item)
            combo = QComboBox()
            combo.setObjectName("qpConstraintRelation")
            for relation in Relation:
                combo.addItem(relation.symbol(), relation.symbol())
            existing = relations[row]
            if isinstance(existing, QComboBox):
                combo.setCurrentIndex(max(0, combo.findData(existing.currentData())))
            self.constraints_table.setCellWidget(row, size + 1, combo)
            rhs_item = QTableWidgetItem(rhs_values[row])
            rhs_item.setTextAlignment(Qt.AlignCenter)
            self.constraints_table.setItem(row, size + 2, rhs_item)
        self._update_constraints_state()
        self._fit_grids()
        self._update_formula()

    def _add_variable(self) -> None:
        rows = self.variables_section.rows()
        if self._compact or len(rows) >= MAX_VARIABLES:
            return
        existing = {row.edit_name.text().strip() for row in rows}
        index = len(rows) + 1
        name = f"x{index}"
        while name in existing:
            index += 1
            name = f"x{index}"
        variables = [_safe_variable(row, position) for position, row in enumerate(rows)]
        variables.append(QPVariable(name=name))
        self.variables_section.set_variables(variables)
        self._sync_structure()

    def _apply_compact_state(self) -> None:
        editable = not self._compact
        for widget in (
            self.matrix_label,
            self.matrix_hint,
            self.matrix_table,
            self.linear_label,
            self.linear_table,
        ):
            widget.setVisible(editable)
        self.large_matrix_notice.setText(
            S.t(
                "qp.objective.large_matrix",
                count=len(self._model.variables) if self._model is not None else 0,
                limit=MATRIX_EDITOR_LIMIT,
            )
        )
        self.large_matrix_notice.setVisible(self._compact)
        self.combo_sense.setEnabled(editable)
        self.edit_offset.setEnabled(editable)
        self.variables_section.setVisible(editable)
        self.constraints_section.setVisible(editable)
        self._update_constraints_state()

    def _update_formula(self) -> None:
        sense_key = "qp.objective.min" if self.combo_sense.currentIndex() == 0 else "qp.objective.max"
        self.formula_label.setText(S.t("qp.objective.formula", sense=S.t(sense_key)))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("qp.import.dialog_title"),
            "",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            self.set_model(qp_model_from_json(text))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                S.t("qp.import.error_title"),
                S.t("qp.import.error_body", detail=localized_error_detail("qp_import", exc)),
            )

    def _on_export_json(self) -> None:
        try:
            model = self.current_model()
        except ValueError as exc:
            self._warn_invalid_model(exc)
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            S.t("qp.export.dialog_title"),
            S.t("qp.export.default_name"),
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(qp_model_to_json(model), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self,
                S.t("qp.export.error_title"),
                S.t("qp.export.error_body", detail=localized_error_detail("qp_export", exc)),
            )

    def _on_solve(self) -> None:
        if self._solve_usecase is None:
            return
        try:
            model = self.current_model()
        except ValueError as exc:
            self._warn_invalid_model(exc)
            return
        self._model = model
        self.solve_completed.emit(self._solve_usecase.execute(model))

    def _warn_invalid_model(self, exc: Exception) -> None:
        QMessageBox.warning(
            self,
            S.t("qp.validation.title"),
            S.t("qp.validation.body", detail=localized_error_detail("qp_validation", exc)),
        )

    def _show_info(self, topic: str) -> None:
        dialog = _InfoDialog(
            S.t(f"qp.{topic}.info_title"),
            S.t(f"qp.{topic}.info_body"),
            S.t(f"qp.{topic}.info_html"),
            self,
        )
        dialog.exec()

    # ------------------------------------------------------------------
    # Localization and theme
    # ------------------------------------------------------------------
    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:26px; font-weight:700'>{S.t('qp.header.title')}</span>"
        )
        self.dependency_notice.setText(S.t("qp.dependency.unavailable"))
        self.intro_section.set_title(S.t("qp.header.section"))
        self.intro_text.setText(S.t("qp.header.description"))
        self.btn_import_json.setText(S.t("qp.import.button"))
        self.btn_export_json.setText(S.t("qp.export.button"))
        self.btn_json_info.setToolTip(S.t("qp.import.info_tooltip"))
        self.btn_example.setText(S.t("qp.header.buttons.example"))
        self.btn_problem.setText(S.t("qp.header.buttons.problem"))
        self.variables_section.refresh_strings()

        self.objective_section.set_title(S.t("qp.objective.section"))
        self.objective_hint.setText(S.t("qp.objective.hint"))
        self.btn_objective_info.setToolTip(S.t("qp.objective.info_tooltip"))
        self.lbl_sense.setText(S.t("qp.objective.sense"))
        self.combo_sense.setItemText(0, S.t("qp.objective.min"))
        self.combo_sense.setItemText(1, S.t("qp.objective.max"))
        self.combo_sense.setAccessibleName(S.t("qp.objective.sense"))
        self.lbl_offset.setText(S.t("qp.objective.offset"))
        self.edit_offset.setPlaceholderText(S.t("qp.objective.offset_placeholder"))
        self.edit_offset.setAccessibleName(S.t("qp.objective.offset"))
        self.matrix_label.setText(S.t("qp.objective.matrix_label"))
        self.matrix_hint.setText(S.t("qp.objective.matrix_hint"))
        self.matrix_table.setAccessibleName(S.t("qp.objective.matrix_label"))
        self.linear_label.setText(S.t("qp.objective.linear_label"))
        self.linear_table.setAccessibleName(S.t("qp.objective.linear_label"))
        self.large_matrix_notice.setText(
            S.t(
                "qp.objective.large_matrix",
                count=len(self._model.variables) if self._model is not None else 0,
                limit=MATRIX_EDITOR_LIMIT,
            )
        )

        self.constraints_section.set_title(S.t("qp.constraints.section"))
        self.constraints_hint.setText(S.t("qp.constraints.hint"))
        self.constraints_empty.setText(S.t("qp.constraints.empty"))
        self.btn_add_constraint.setText(S.t("qp.constraints.add"))
        self.btn_remove_constraint.setText(S.t("qp.constraints.remove"))
        self.constraints_limit_notice.setText(
            S.t("qp.constraints.limit_reached", limit=MAX_CONSTRAINTS)
        )
        self.constraints_table.setHorizontalHeaderLabels(
            self._constraint_headers(self._variable_names()) + [""]
        )

        self.solver_section.set_title(S.t("qp.solver.section"))
        self.solver_hint.setText(S.t("qp.solver.hint"))
        self.btn_solver_info.setToolTip(S.t("qp.solver.info_tooltip"))
        self.lbl_method.setText(S.t("qp.solver.method"))
        self.combo_method.setAccessibleName(S.t("qp.solver.method"))
        self.lbl_tolerance.setText(S.t("qp.solver.tolerance"))
        self.edit_tolerance.setPlaceholderText(S.t("qp.solver.tolerance_placeholder"))
        self.edit_tolerance.setAccessibleName(S.t("qp.solver.tolerance"))
        self.lbl_iterations.setText(S.t("qp.solver.max_iterations"))
        self.edit_iterations.setPlaceholderText(S.t("qp.solver.max_iterations_placeholder"))
        self.edit_iterations.setAccessibleName(S.t("qp.solver.max_iterations"))
        self.lbl_time_limit.setText(S.t("qp.solver.time_limit"))
        self.edit_time_limit.setPlaceholderText(S.t("qp.solver.time_limit_placeholder"))
        self.edit_time_limit.setAccessibleName(S.t("qp.solver.time_limit"))
        self.btn_solve.setText(S.t("qp.actions.solve"))
        self._update_formula()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.dependency_notice.setStyleSheet(f"color: {t.warning}; font-weight: 600;")
        self.intro_text.setStyleSheet(f"color: {t.text_muted};")
        self.objective_hint.setStyleSheet(f"color: {t.text_muted};")
        self.matrix_hint.setStyleSheet(f"color: {t.text_muted};")
        self.constraints_hint.setStyleSheet(f"color: {t.text_muted};")
        self.constraints_empty.setStyleSheet(f"color: {t.text_muted};")
        self.solver_hint.setStyleSheet(f"color: {t.text_muted};")
        self.large_matrix_notice.setStyleSheet(f"color: {t.warning};")
        self.formula_label.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        for label in (self.matrix_label, self.linear_label):
            label.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        self.variables_section.refresh_theme()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Let the grids use the available width without a horizontal scrollbar."""
        super().resizeEvent(event)
        for table in (self.matrix_table, self.linear_table, self.constraints_table):
            header = table.horizontalHeader()
            columns = table.columnCount()
            if columns == 0:
                continue
            mode = (
                QHeaderView.Stretch
                if columns * _MATRIX_COLUMN_WIDTH <= max(1, table.viewport().width())
                else QHeaderView.Interactive
            )
            header.setSectionResizeMode(mode)


def _safe_variable(row: _VariableRow, position: int) -> QPVariable:
    """Read a row without failing on a half-typed bound during structure edits."""
    name = row.edit_name.text().strip() or f"x{position + 1}"
    try:
        lower = _parse_number(row.edit_lower.text(), required=False, label="lower bound")
        upper = _parse_number(row.edit_upper.text(), required=False, label="upper bound")
        bounds = Bounds(lower, upper)
    except ValueError:
        bounds = Bounds(None, None)
    return QPVariable(name=name, label=row.edit_label.text(), bounds=bounds)


def _default_model() -> QPModel:
    """The boundary-constrained reference problem from the public contract."""
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
        constraints=[
            QPConstraint(name="sum_bound", coefs=(1.0, 1.0), relation=Relation.GE, rhs=2.0),
        ],
    )
