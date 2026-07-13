from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.error_feedback import localized_error_detail
from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.models.nlp.nlp_model import NLPModel, NLPOptions
from optees.domain.value_objects.nlp.objective_sense import NLPObjectiveSense
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.presentation.views.lp_view.section import Section
from optees.utility.nlp_json_io import nlp_model_from_file


_VARIABLE_NAME_WIDTH = 110
_NUMERIC_WIDTH = 120
_REMOVE_WIDTH = 28


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


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setMinimumSize(520, 360)
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
    bounds_changed = Signal()

    def __init__(self, index: int, variable: NLPVariable, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit_name = QLineEdit(variable.name)
        self.edit_name.setObjectName("nlpVariableName")
        self.edit_name.setFixedWidth(_VARIABLE_NAME_WIDTH)

        self.edit_label = QLineEdit(variable.label)
        self.edit_label.setObjectName("nlpVariableLabel")
        self.edit_label.setMinimumWidth(160)

        self.edit_lower = QLineEdit(_format_optional(variable.lower_bound))
        self.edit_lower.setObjectName("nlpVariableLowerBound")
        self.edit_lower.setFixedWidth(_NUMERIC_WIDTH)
        self.edit_lower.textChanged.connect(lambda _text: self.bounds_changed.emit())

        self.edit_upper = QLineEdit(_format_optional(variable.upper_bound))
        self.edit_upper.setObjectName("nlpVariableUpperBound")
        self.edit_upper.setFixedWidth(_NUMERIC_WIDTH)
        self.edit_upper.textChanged.connect(lambda _text: self.bounds_changed.emit())

        self.edit_initial = QLineEdit(_format_optional(variable.initial_value))
        self.edit_initial.setObjectName("nlpVariableInitial")
        self.edit_initial.setFixedWidth(_NUMERIC_WIDTH)

        self.btn_remove = QToolButton()
        self.btn_remove.setObjectName("rowRemoveButton")
        icon = QIcon.fromTheme("edit-delete")
        if icon.isNull():
            self.btn_remove.setText("x")
        else:
            self.btn_remove.setIcon(icon)
        self.btn_remove.setAutoRaise(True)
        self.btn_remove.setFixedSize(_REMOVE_WIDTH, 28)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self._index))

        layout.addWidget(self.edit_name)
        layout.addWidget(self.edit_label, 1)
        layout.addWidget(self.edit_lower)
        layout.addWidget(self.edit_upper)
        layout.addWidget(self.edit_initial)
        layout.addWidget(self.btn_remove)
        self.refresh_strings()

    def set_index(self, index: int) -> None:
        self._index = index

    def refresh_strings(self) -> None:
        self.edit_name.setPlaceholderText(S.t("nlp.variables.name_placeholder"))
        self.edit_label.setPlaceholderText(S.t("nlp.variables.label_placeholder"))
        self.edit_lower.setPlaceholderText(S.t("nlp.variables.bound_placeholder"))
        self.edit_upper.setPlaceholderText(S.t("nlp.variables.bound_placeholder"))
        self.edit_initial.setPlaceholderText(S.t("nlp.variables.initial_placeholder"))
        self.btn_remove.setToolTip(S.t("nlp.variables.remove"))


class _VariablesSection(Section):
    add_requested = Signal()
    bounds_edited = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)
        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self.body.addWidget(self._hint)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.col_name = QLabel()
        self.col_label = QLabel()
        self.col_lower = QLabel()
        self.col_upper = QLabel()
        self.col_initial = QLabel()
        self.col_name.setFixedWidth(_VARIABLE_NAME_WIDTH)
        self.col_lower.setFixedWidth(_NUMERIC_WIDTH)
        self.col_upper.setFixedWidth(_NUMERIC_WIDTH)
        self.col_initial.setFixedWidth(_NUMERIC_WIDTH)
        for label in (self.col_name, self.col_label, self.col_lower, self.col_upper, self.col_initial):
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.addWidget(self.col_name)
        header.addWidget(self.col_label, 1)
        header.addWidget(self.col_lower)
        header.addWidget(self.col_upper)
        header.addWidget(self.col_initial)
        header.addSpacing(_REMOVE_WIDTH)
        self.body.addLayout(header)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)
        self.body.addLayout(self._rows_layout)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("nlpAddVariableButton")
        self.btn_add.clicked.connect(self.add_requested.emit)
        footer.addWidget(self.btn_add)
        self.body.addLayout(footer)
        self.refresh_strings()

    def set_variables(self, variables: tuple[NLPVariable, ...] | list[NLPVariable]) -> None:
        _clear_layout(self._rows_layout)
        for index, variable in enumerate(variables):
            row = _VariableRow(index, variable)
            row.remove_requested.connect(self.remove_row)
            row.bounds_changed.connect(self.bounds_edited.emit)
            self._rows_layout.addWidget(row)

    def rows(self) -> list[_VariableRow]:
        rows: list[_VariableRow] = []
        for index in range(self._rows_layout.count()):
            widget = self._rows_layout.itemAt(index).widget()
            if isinstance(widget, _VariableRow):
                rows.append(widget)
        return rows

    def remove_row(self, index: int) -> None:
        rows = self.rows()
        if len(rows) <= 1 or not 0 <= index < len(rows):
            return
        row = rows[index]
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        for new_index, remaining in enumerate(self.rows()):
            remaining.set_index(new_index)
        self.bounds_edited.emit()

    def refresh_strings(self) -> None:
        self.set_title(S.t("nlp.variables.section"))
        self._hint.setText(S.t("nlp.variables.hint"))
        self.col_name.setText(S.t("nlp.variables.columns.name"))
        self.col_label.setText(S.t("nlp.variables.columns.label"))
        self.col_lower.setText(S.t("nlp.variables.columns.lower"))
        self.col_upper.setText(S.t("nlp.variables.columns.upper"))
        self.col_initial.setText(S.t("nlp.variables.columns.initial"))
        self.btn_add.setText(S.t("nlp.variables.add"))
        for row in self.rows():
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(f"color: {tokens(theme.is_dark()).text_muted};")


class NLPView(QWidget):
    """Formulation view for the first continuous nonlinear-programming slice."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solve_usecase = None

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

        intro = Section()
        intro_header = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        intro_header.addWidget(self.intro_text, 1)
        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("nlpImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_json_info = _make_info_button("nlpJsonInfoButton")
        self.btn_json_info.clicked.connect(
            lambda: self._show_info("import")
        )
        intro_header.addWidget(self.btn_import_json)
        intro_header.addWidget(self.btn_json_info)
        intro.body.addLayout(intro_header)
        intro_actions = QHBoxLayout()
        intro_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("nlpExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("nlpProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        intro_actions.addWidget(self.btn_example)
        intro_actions.addWidget(self.btn_problem)
        intro.body.addLayout(intro_actions)
        self.intro_section = intro
        root.addWidget(intro)

        self.variables_section = _VariablesSection()
        self.variables_section.add_requested.connect(self._add_variable)
        self.variables_section.bounds_edited.connect(self._update_method_hint)
        root.addWidget(self.variables_section)

        objective = Section()
        objective_header = QHBoxLayout()
        self.objective_hint = QLabel()
        self.objective_hint.setWordWrap(True)
        objective_header.addWidget(self.objective_hint, 1)
        self.btn_objective_info = _make_info_button("nlpObjectiveInfoButton")
        self.btn_objective_info.clicked.connect(lambda: self._show_info("objective"))
        objective_header.addWidget(self.btn_objective_info)
        objective.body.addLayout(objective_header)
        objective_row = QHBoxLayout()
        self.lbl_sense = QLabel()
        self.combo_sense = QComboBox()
        self.combo_sense.setObjectName("nlpObjectiveSense")
        self.combo_sense.addItem("", NLPObjectiveSense.MIN.value)
        self.combo_sense.addItem("", NLPObjectiveSense.MAX.value)
        self.lbl_expression = QLabel()
        self.edit_expression = QLineEdit()
        self.edit_expression.setObjectName("nlpObjectiveExpression")
        objective_row.addWidget(self.lbl_sense)
        objective_row.addWidget(self.combo_sense)
        objective_row.addWidget(self.lbl_expression)
        objective_row.addWidget(self.edit_expression, 1)
        objective.body.addLayout(objective_row)
        self.objective_section = objective
        root.addWidget(objective)

        solver = Section()
        solver_header = QHBoxLayout()
        self.solver_hint = QLabel()
        self.solver_hint.setWordWrap(True)
        solver_header.addWidget(self.solver_hint, 1)
        self.btn_solver_info = _make_info_button("nlpSolverInfoButton")
        self.btn_solver_info.clicked.connect(lambda: self._show_info("solver"))
        solver_header.addWidget(self.btn_solver_info)
        solver.body.addLayout(solver_header)
        solver_row = QHBoxLayout()
        self.lbl_method = QLabel()
        self.combo_method = QComboBox()
        self.combo_method.setObjectName("nlpSolverMethod")
        for method in NLPSolverMethod:
            self.combo_method.addItem(method.value, method.value)
        self.lbl_iterations = QLabel()
        self.edit_iterations = QLineEdit("1000")
        self.edit_iterations.setObjectName("nlpMaxIterations")
        self.edit_iterations.setFixedWidth(_NUMERIC_WIDTH)
        self.lbl_tolerance = QLabel()
        self.edit_tolerance = QLineEdit("1e-8")
        self.edit_tolerance.setObjectName("nlpTolerance")
        self.edit_tolerance.setFixedWidth(_NUMERIC_WIDTH)
        solver_row.addWidget(self.lbl_method)
        solver_row.addWidget(self.combo_method)
        solver_row.addSpacing(16)
        solver_row.addWidget(self.lbl_iterations)
        solver_row.addWidget(self.edit_iterations)
        solver_row.addSpacing(16)
        solver_row.addWidget(self.lbl_tolerance)
        solver_row.addWidget(self.edit_tolerance)
        solver_row.addStretch(1)
        solver.body.addLayout(solver_row)
        self.method_hint = QLabel()
        self.method_hint.setWordWrap(True)
        solver.body.addWidget(self.method_hint)
        self.solver_section = solver
        root.addWidget(solver)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setObjectName("nlpOptimizeButton")
        self.btn_optimize.clicked.connect(self._on_optimize)
        actions.addWidget(self.btn_optimize)
        root.addLayout(actions)
        root.addStretch(1)

        self.set_model(
            NLPModel.from_parts(
                variables=[NLPVariable("x1"), NLPVariable("x2")],
                objective=NLPObjective("x1**2 + x2**2"),
            )
        )
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def set_solve_usecase(self, usecase) -> None:
        self._solve_usecase = usecase

    def set_model(self, model: NLPModel) -> None:
        self.variables_section.set_variables(model.variables)
        self.combo_sense.setCurrentIndex(
            max(0, self.combo_sense.findData(model.objective.sense.value))
        )
        self.edit_expression.setText(model.objective.expression)
        self.combo_method.setCurrentIndex(
            max(0, self.combo_method.findData(model.options.method.value))
        )
        self.edit_iterations.setText(str(model.options.max_iterations))
        self.edit_tolerance.setText(_format_optional(model.options.tolerance))
        self._update_method_hint()

    def current_model(self) -> NLPModel:
        variables = []
        for row_number, row in enumerate(self.variables_section.rows(), start=1):
            name = row.edit_name.text().strip()
            if not name:
                raise ValueError(f"variable {row_number} name is required")
            variables.append(
                NLPVariable(
                    name=name,
                    label=row.edit_label.text(),
                    lower_bound=_parse_number(
                        row.edit_lower.text(), required=False, label=f"{name} lower bound"
                    ),
                    upper_bound=_parse_number(
                        row.edit_upper.text(), required=False, label=f"{name} upper bound"
                    ),
                    initial_value=_parse_number(
                        row.edit_initial.text(), required=True, label=f"{name} initial value"
                    ),
                )
            )

        sense = NLPObjectiveSense.from_str(self.combo_sense.currentData())
        method = NLPSolverMethod.from_str(self.combo_method.currentData())
        iterations_raw = self.edit_iterations.text().strip()
        try:
            max_iterations = int(iterations_raw)
        except ValueError as exc:
            raise ValueError("max iterations must be a positive integer") from exc
        tolerance = _parse_number(
            self.edit_tolerance.text(), required=False, label="tolerance"
        )
        return NLPModel.from_parts(
            variables=variables,
            objective=NLPObjective(self.edit_expression.text(), sense),
            options=NLPOptions(
                method=method,
                max_iterations=max_iterations,
                tolerance=tolerance,
            ),
        )

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:26px; font-weight:700'>{S.t('nlp.header.title')}</span>"
        )
        self.intro_section.set_title(S.t("nlp.header.section"))
        self.intro_text.setText(S.t("nlp.header.description"))
        self.btn_import_json.setText(S.t("nlp.import.button"))
        self.btn_json_info.setToolTip(S.t("nlp.import.info_tooltip"))
        self.btn_example.setText(S.t("nlp.header.buttons.example"))
        self.btn_problem.setText(S.t("nlp.header.buttons.problem"))
        self.variables_section.refresh_strings()
        self.objective_section.set_title(S.t("nlp.objective.section"))
        self.objective_hint.setText(S.t("nlp.objective.hint"))
        self.btn_objective_info.setToolTip(S.t("nlp.objective.info_tooltip"))
        self.lbl_sense.setText(S.t("nlp.objective.sense"))
        self.combo_sense.setItemText(0, S.t("nlp.objective.min"))
        self.combo_sense.setItemText(1, S.t("nlp.objective.max"))
        self.lbl_expression.setText(S.t("nlp.objective.expression"))
        self.edit_expression.setPlaceholderText(S.t("nlp.objective.expression_placeholder"))
        self.solver_section.set_title(S.t("nlp.solver.section"))
        self.solver_hint.setText(S.t("nlp.solver.hint"))
        self.btn_solver_info.setToolTip(S.t("nlp.solver.info_tooltip"))
        self.lbl_method.setText(S.t("nlp.solver.method"))
        self.lbl_iterations.setText(S.t("nlp.solver.max_iterations"))
        self.edit_iterations.setPlaceholderText(S.t("nlp.solver.max_iterations_placeholder"))
        self.lbl_tolerance.setText(S.t("nlp.solver.tolerance"))
        self.edit_tolerance.setPlaceholderText(S.t("nlp.solver.tolerance_placeholder"))
        self.btn_optimize.setText(S.t("nlp.actions.optimize"))
        self._update_method_hint()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.intro_text.setStyleSheet(f"color: {t.text_muted};")
        self.objective_hint.setStyleSheet(f"color: {t.text_muted};")
        self.solver_hint.setStyleSheet(f"color: {t.text_muted};")
        self.method_hint.setStyleSheet(f"color: {t.text_muted};")
        self.variables_section.refresh_theme()

    def _add_variable(self) -> None:
        rows = self.variables_section.rows()
        existing = {row.edit_name.text().strip() for row in rows}
        index = len(rows) + 1
        name = f"x{index}"
        while name in existing:
            index += 1
            name = f"x{index}"
        variables = [self._variable_from_row(row) for row in rows]
        variables.append(NLPVariable(name))
        self.variables_section.set_variables(variables)
        self._update_method_hint()

    def _variable_from_row(self, row: _VariableRow) -> NLPVariable:
        name = row.edit_name.text().strip() or "x"
        return NLPVariable(
            name=name,
            label=row.edit_label.text(),
            lower_bound=_parse_number(row.edit_lower.text(), required=False, label="lower bound"),
            upper_bound=_parse_number(row.edit_upper.text(), required=False, label="upper bound"),
            initial_value=_parse_number(row.edit_initial.text(), required=False, label="initial value") or 0.0,
        )

    def _update_method_hint(self) -> None:
        has_bounds = any(
            row.edit_lower.text().strip() or row.edit_upper.text().strip()
            for row in self.variables_section.rows()
        )
        if has_bounds:
            self.method_hint.setText(S.t("nlp.solver.bounds_required"))
            index = self.combo_method.findData(NLPSolverMethod.L_BFGS_B.value)
            if index >= 0:
                self.combo_method.setCurrentIndex(index)
        else:
            self.method_hint.setText(S.t("nlp.solver.unbounded_hint"))

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("nlp.import.dialog_title"),
            "",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            self.set_model(nlp_model_from_file(path))
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("nlp.import.error_title"),
                S.t("nlp.import.error_body", detail=localized_error_detail("nlp_import", exc)),
            )

    def _on_optimize(self) -> None:
        if self._solve_usecase is None:
            return
        try:
            model = self.current_model()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("nlp.validation.title"),
                S.t("nlp.validation.body", detail=localized_error_detail("nlp_validation", exc)),
            )
            return
        self.solve_completed.emit(self._solve_usecase.execute(model))

    def _show_info(self, topic: str) -> None:
        dialog = _InfoDialog(
            S.t(f"nlp.{topic}.info_title"),
            S.t(f"nlp.{topic}.info_body"),
            S.t(f"nlp.{topic}.info_html"),
            self,
        )
        dialog.exec()


def _format_optional(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{float(value):.10g}"
