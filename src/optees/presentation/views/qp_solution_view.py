"""Result view for the continuous convex quadratic-programming capability.

Every authoritative fact shown here — mathematical status, objective value,
candidate vector, duals, residuals, backend diagnostics, and the independent
validation report — is produced by the application layer and rendered verbatim.
The view derives nothing except display-only conveniences (constraint activity
at the candidate and the bound position label), which are labelled as such and
never change the reported outcome.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optees.application.contracts.solution_validation import (
    SolutionValidation,
    SolutionValidationStatus,
    ValidationCheckStatus,
)
from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.qp.solution import QPSolution
from optees.domain.models.qp.qp_model import QPModel
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus
from optees.presentation.views.lp_view.section import Section
from optees.presentation.views.qp_contour_plot_widget import QPContourPlotWidget
from optees.utility.qp_json_io import qp_model_to_json

_ACTIVITY_TOLERANCE = 1e-7

_STATUS_KEYS = {
    QPSolveStatus.OPTIMAL: "optimal",
    QPSolveStatus.FEASIBLE: "feasible",
    QPSolveStatus.INFEASIBLE: "infeasible",
    QPSolveStatus.UNBOUNDED: "unbounded",
    QPSolveStatus.NOT_SOLVED: "not_solved",
}

_VALIDATION_STATUS_KEYS = {
    SolutionValidationStatus.VERIFIED: "status_verified",
    SolutionValidationStatus.PARTIAL: "status_partial",
    SolutionValidationStatus.FAILED: "status_failed",
    SolutionValidationStatus.NOT_AVAILABLE: "status_not_available",
}

_DIAGNOSTIC_ROWS = (
    "backend",
    "backend_version",
    "backend_status",
    "iterations",
    "solve_time",
    "setup_time",
    "message",
)

_RESIDUAL_ROWS = ("primal", "dual", "gap", "complementarity")


def _format_number(value: object) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "-"
    return f"{number:.10g}"


def _make_table(object_name: str) -> QTableWidget:
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(False)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return table


def _fit_table_height(table: QTableWidget) -> None:
    """Size a result table to its rows so sections do not carry dead space."""
    header = table.horizontalHeader().height()
    rows = sum(table.rowHeight(row) for row in range(table.rowCount()))
    table.setFixedHeight(header + rows + 2 * table.frameWidth() + 2)


class QPSolutionView(QWidget):
    """Result page for `qp.continuous`."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[QPModel] = None
        self._solution: Optional[QPSolution] = None
        self._validation: Optional[SolutionValidation] = None

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

        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        header.addWidget(self.title, 1)
        self.btn_export = QPushButton()
        self.btn_export.setObjectName("qpSolutionExportButton")
        self.btn_export.clicked.connect(self._on_export)
        header.addWidget(self.btn_export)
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("qpSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        summary = Section()
        self.status = QLabel()
        self.status.setObjectName("qpSolutionStatus")
        self.status.setWordWrap(True)
        summary.body.addWidget(self.status)
        self.explanation = QLabel()
        self.explanation.setObjectName("qpSolutionExplanation")
        self.explanation.setWordWrap(True)
        summary.body.addWidget(self.explanation)
        self.dependency_notice = QLabel()
        self.dependency_notice.setObjectName("qpSolutionDependencyNotice")
        self.dependency_notice.setWordWrap(True)
        self.dependency_notice.setVisible(False)
        summary.body.addWidget(self.dependency_notice)
        self.objective_value = QLabel()
        self.objective_value.setObjectName("qpSolutionObjective")
        self.objective_value.setWordWrap(True)
        summary.body.addWidget(self.objective_value)
        self.objective_formula = QLabel()
        self.objective_formula.setWordWrap(True)
        summary.body.addWidget(self.objective_formula)
        self.local_notice = QLabel()
        self.local_notice.setWordWrap(True)
        summary.body.addWidget(self.local_notice)
        self.summary_section = summary
        root.addWidget(summary)

        variables = Section()
        self.variables_hint = QLabel()
        self.variables_hint.setWordWrap(True)
        variables.body.addWidget(self.variables_hint)
        self.variables_table = _make_table("qpVariablesTable")
        variables.body.addWidget(self.variables_table)
        self.variables_empty = QLabel()
        self.variables_empty.setObjectName("qpVariablesEmpty")
        self.variables_empty.setWordWrap(True)
        variables.body.addWidget(self.variables_empty)
        self.variables_section = variables
        root.addWidget(variables)

        constraints = Section()
        self.constraints_hint = QLabel()
        self.constraints_hint.setWordWrap(True)
        constraints.body.addWidget(self.constraints_hint)
        self.constraints_table = _make_table("qpConstraintActivityTable")
        constraints.body.addWidget(self.constraints_table)
        self.constraints_empty = QLabel()
        self.constraints_empty.setObjectName("qpConstraintsEmpty")
        self.constraints_empty.setWordWrap(True)
        constraints.body.addWidget(self.constraints_empty)
        self.constraints_section = constraints
        root.addWidget(constraints)

        duals = Section()
        self.duals_hint = QLabel()
        self.duals_hint.setWordWrap(True)
        duals.body.addWidget(self.duals_hint)
        self.duals_table = _make_table("qpDualsTable")
        duals.body.addWidget(self.duals_table)
        self.duals_unavailable = QLabel()
        self.duals_unavailable.setObjectName("qpDualsUnavailable")
        self.duals_unavailable.setWordWrap(True)
        duals.body.addWidget(self.duals_unavailable)
        self.duals_section = duals
        root.addWidget(duals)

        residuals = Section()
        self.residuals_hint = QLabel()
        self.residuals_hint.setWordWrap(True)
        residuals.body.addWidget(self.residuals_hint)
        self.residual_labels: dict[str, QLabel] = {}
        for key in _RESIDUAL_ROWS:
            row = QHBoxLayout()
            label = QLabel()
            value = QLabel()
            value.setObjectName(f"qpResidual_{key}")
            value.setWordWrap(True)
            row.addWidget(label)
            row.addWidget(value, 1)
            residuals.body.addLayout(row)
            self.residual_labels[f"{key}_label"] = label
            self.residual_labels[key] = value
        self.residuals_section = residuals
        root.addWidget(residuals)

        validation = Section()
        self.validation_hint = QLabel()
        self.validation_hint.setWordWrap(True)
        validation.body.addWidget(self.validation_hint)
        self.validation_status = QLabel()
        self.validation_status.setObjectName("qpValidationStatus")
        self.validation_status.setWordWrap(True)
        validation.body.addWidget(self.validation_status)
        self.validation_table = _make_table("qpValidationTable")
        validation.body.addWidget(self.validation_table)
        self.validation_limitations = QLabel()
        self.validation_limitations.setObjectName("qpValidationLimitations")
        self.validation_limitations.setWordWrap(True)
        validation.body.addWidget(self.validation_limitations)
        self.validation_section = validation
        root.addWidget(validation)

        diagnostics = Section()
        self.diagnostic_labels: dict[str, QLabel] = {}
        for key in _DIAGNOSTIC_ROWS:
            row = QHBoxLayout()
            label = QLabel()
            value = QLabel()
            value.setObjectName(f"qpDiagnostic_{key}")
            value.setWordWrap(True)
            row.addWidget(label)
            row.addWidget(value, 1)
            diagnostics.body.addLayout(row)
            self.diagnostic_labels[f"{key}_label"] = label
            self.diagnostic_labels[key] = value
        self.diagnostics_hint = QLabel()
        self.diagnostics_hint.setWordWrap(True)
        diagnostics.body.addWidget(self.diagnostics_hint)
        self.diagnostics_section = diagnostics
        root.addWidget(diagnostics)

        visualization = Section()
        self.contour_plot = QPContourPlotWidget()
        visualization.body.addWidget(self.contour_plot)
        self.visualization_section = visualization
        root.addWidget(visualization)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render()

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    def set_problem(self, model: QPModel) -> None:
        self._model = model
        self.contour_plot.set_problem(model)
        self._render()

    def set_solution(self, solution: QPSolution) -> None:
        self._solution = solution
        self.contour_plot.set_solution(solution)
        self._render()

    def set_validation(self, validation: Optional[SolutionValidation]) -> None:
        """Accept the report produced by the registered independent validator."""
        self._validation = validation
        self._render()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render(self) -> None:
        self._render_summary()
        self._render_variables()
        self._render_constraints()
        self._render_duals()
        self._render_residuals()
        self._render_validation()
        self._render_diagnostics()

    def _render_summary(self) -> None:
        solution = self._solution
        if solution is None:
            self.status.setText(S.t("qp.solution.empty"))
            self.explanation.setText("")
            self.objective_value.setText("")
            self.objective_formula.setText("")
            self.dependency_notice.setVisible(False)
            return

        status_key = _STATUS_KEYS.get(solution.status, "not_solved")
        self.status.setText(
            S.t("qp.solution.status_line", status=S.t(f"qp.solution.status.{status_key}"))
        )
        self.explanation.setText(S.t(f"qp.solution.explanation.{status_key}"))
        self.dependency_notice.setVisible(_is_dependency_failure(solution))

        if solution.objective is None:
            self.objective_value.setText(S.t("qp.solution.objective.unavailable"))
            self.objective_formula.setText("")
            return
        sense_key = "sense_min"
        if self._model is not None and self._model.objective.sense is ObjectiveSense.MAX:
            sense_key = "sense_max"
        self.objective_value.setText(
            f"{S.t(f'qp.solution.objective.{sense_key}')}: {_format_number(solution.objective)}"
        )
        self.objective_formula.setText(S.t("qp.solution.objective.recomputed"))

    def _render_variables(self) -> None:
        headers = [
            S.t("qp.solution.variables.columns.variable"),
            S.t("qp.solution.variables.columns.description"),
            S.t("qp.solution.variables.columns.value"),
            S.t("qp.solution.variables.columns.lower"),
            S.t("qp.solution.variables.columns.upper"),
            S.t("qp.solution.variables.columns.status"),
        ]
        self.variables_table.setColumnCount(len(headers))
        self.variables_table.setHorizontalHeaderLabels(headers)
        header = self.variables_table.horizontalHeader()
        for column in range(len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        values = self._solution.values if self._solution is not None else {}
        variables = self._model.variables if self._model is not None else ()
        rows = [variable for variable in variables if variable.name in values]
        self.variables_table.setRowCount(len(rows))
        for index, variable in enumerate(rows):
            value = float(values[variable.name])
            cells = [
                variable.name,
                variable.label or "-",
                _format_number(value),
                _format_number(variable.bounds.lb) if variable.bounds.lb is not None else "-",
                _format_number(variable.bounds.ub) if variable.bounds.ub is not None else "-",
                S.t(f"qp.solution.variables.{_bound_position(variable, value)}"),
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column >= 2:
                    item.setTextAlignment(Qt.AlignCenter)
                self.variables_table.setItem(index, column, item)
        _fit_table_height(self.variables_table)
        empty = not rows
        self.variables_table.setVisible(not empty)
        self.variables_empty.setVisible(empty)

    def _render_constraints(self) -> None:
        headers = [
            S.t("qp.solution.constraints.columns.name"),
            S.t("qp.solution.constraints.columns.relation"),
            S.t("qp.solution.constraints.columns.lhs"),
            S.t("qp.solution.constraints.columns.rhs"),
            S.t("qp.solution.constraints.columns.slack"),
            S.t("qp.solution.constraints.columns.status"),
        ]
        self.constraints_table.setColumnCount(len(headers))
        self.constraints_table.setHorizontalHeaderLabels(headers)
        constraint_header = self.constraints_table.horizontalHeader()
        for column in range(len(headers)):
            constraint_header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        constraint_header.setSectionResizeMode(0, QHeaderView.Stretch)

        constraints = self._model.constraints if self._model is not None else ()
        values = self._solution.values if self._solution is not None else {}
        names = [variable.name for variable in (self._model.variables if self._model else ())]
        can_evaluate = bool(values) and all(name in values for name in names)
        self.constraints_table.setRowCount(len(constraints))
        for index, constraint in enumerate(constraints):
            if can_evaluate:
                lhs = sum(
                    float(constraint.coefs[position]) * float(values[name])
                    for position, name in enumerate(names)
                )
                slack = float(constraint.rhs) - lhs
                lhs_text = _format_number(lhs)
                slack_text = _format_number(slack)
                state = S.t(f"qp.solution.constraints.{_constraint_state(constraint, slack)}")
            else:
                lhs_text = slack_text = "-"
                state = "-"
            cells = [
                constraint.name or f"c{index + 1}",
                constraint.relation.symbol(),
                lhs_text,
                _format_number(constraint.rhs),
                slack_text,
                state,
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column >= 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.constraints_table.setItem(index, column, item)
        _fit_table_height(self.constraints_table)
        empty = not constraints
        self.constraints_table.setVisible(not empty)
        self.constraints_empty.setVisible(empty)

    def _render_duals(self) -> None:
        headers = [
            S.t("qp.solution.duals.columns.item"),
            S.t("qp.solution.duals.columns.kind"),
            S.t("qp.solution.duals.columns.value"),
        ]
        self.duals_table.setColumnCount(len(headers))
        self.duals_table.setHorizontalHeaderLabels(headers)
        duals_header = self.duals_table.horizontalHeader()
        for column in range(len(headers)):
            duals_header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        duals_header.setSectionResizeMode(0, QHeaderView.Stretch)

        duals = self._solution.dual_values if self._solution is not None else None
        if duals is None or self._model is None:
            self.duals_table.setRowCount(0)
            self.duals_table.setVisible(False)
            self.duals_unavailable.setVisible(True)
            return

        rows: list[tuple[str, str, float]] = []
        for index, constraint in enumerate(self._model.constraints):
            if index < len(duals.constraints):
                rows.append(
                    (
                        constraint.name or f"c{index + 1}",
                        S.t("qp.solution.duals.kind_constraint"),
                        duals.constraints[index],
                    )
                )
        for index, variable in enumerate(self._model.variables):
            if index < len(duals.lower_bounds):
                rows.append(
                    (variable.name, S.t("qp.solution.duals.kind_lower"), duals.lower_bounds[index])
                )
            if index < len(duals.upper_bounds):
                rows.append(
                    (variable.name, S.t("qp.solution.duals.kind_upper"), duals.upper_bounds[index])
                )

        self.duals_table.setRowCount(len(rows))
        for index, (name, kind, value) in enumerate(rows):
            for column, text in enumerate((name, kind, _format_number(value))):
                item = QTableWidgetItem(text)
                if column >= 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.duals_table.setItem(index, column, item)
        _fit_table_height(self.duals_table)
        self.duals_table.setVisible(bool(rows))
        self.duals_unavailable.setVisible(not rows)

    def _render_residuals(self) -> None:
        residuals = self._solution.kkt_residuals if self._solution is not None else None
        mapping = {
            "primal": getattr(residuals, "primal_residual", None),
            "dual": getattr(residuals, "dual_residual", None),
            "gap": getattr(residuals, "duality_gap", None),
            "complementarity": getattr(residuals, "complementarity_residual", None),
        }
        for key, value in mapping.items():
            text = (
                S.t("qp.solution.residuals.unavailable")
                if value is None
                else _format_number(value)
            )
            self.residual_labels[key].setText(text)

    def _render_validation(self) -> None:
        headers = [
            S.t("qp.solution.validation_report.columns.check"),
            S.t("qp.solution.validation_report.columns.result"),
            S.t("qp.solution.validation_report.columns.detail"),
        ]
        self.validation_table.setColumnCount(len(headers))
        self.validation_table.setHorizontalHeaderLabels(headers)
        validation_header = self.validation_table.horizontalHeader()
        validation_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        validation_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        validation_header.setSectionResizeMode(2, QHeaderView.Stretch)

        validation = self._validation
        if validation is None:
            self.validation_status.setText(S.t("qp.solution.validation_report.empty"))
            self.validation_table.setRowCount(0)
            _fit_table_height(self.validation_table)
            self.validation_table.setVisible(False)
            self.validation_limitations.setText("")
            return

        status_key = _VALIDATION_STATUS_KEYS.get(validation.status, "status_not_available")
        self.validation_status.setText(
            f"{S.t('qp.solution.validation_report.status')}: "
            f"{S.t(f'qp.solution.validation_report.{status_key}')}"
        )

        violations_by_check: dict[str, list[str]] = {}
        for violation in validation.violations:
            violations_by_check.setdefault(violation.check_code, []).append(violation.path)

        self.validation_table.setRowCount(len(validation.checks))
        for index, check in enumerate(validation.checks):
            passed = check.status is ValidationCheckStatus.PASSED
            result_key = "check_passed" if passed else "check_failed"
            paths = violations_by_check.get(check.code, ())
            # The public detail codes contain dots; the dotted-path lookup in the
            # string manager would split them, so address the leaf name instead.
            check_key = check.code.removeprefix("qp.")
            detail = S.t(f"qp.solution.validation_report.checks.{check_key}.detail")
            if paths:
                detail = (
                    f"{detail} — {S.t('qp.solution.validation_report.violations')}: "
                    f"{', '.join(paths)}"
                )
            cells = (
                S.t(f"qp.solution.validation_report.checks.{check_key}.name"),
                S.t(f"qp.solution.validation_report.{result_key}"),
                detail,
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                if column == 2 and paths:
                    item.setToolTip(
                        "\n".join(
                            violation.message
                            for violation in validation.violations
                            if violation.check_code == check.code
                        )
                    )
                self.validation_table.setItem(index, column, item)
        self.validation_table.resizeRowsToContents()
        _fit_table_height(self.validation_table)
        self.validation_table.setVisible(bool(validation.checks))

        limitations = [
            _localized_limitation(index, original)
            for index, original in enumerate(validation.limitations)
        ]
        if limitations:
            bullets = "".join(f"<li>{text}</li>" for text in limitations)
            self.validation_limitations.setText(
                f"<b>{S.t('qp.solution.validation_report.limitations')}</b><ul>{bullets}</ul>"
            )
        else:
            self.validation_limitations.setText("")

    def _render_diagnostics(self) -> None:
        diagnostics = self._solution.diagnostics if self._solution is not None else None
        mapping = {
            "backend": getattr(diagnostics, "backend", None),
            "backend_version": getattr(diagnostics, "backend_version", None),
            "backend_status": getattr(diagnostics, "status", None),
            "iterations": getattr(diagnostics, "iterations", None),
            "solve_time": getattr(diagnostics, "solve_time_seconds", None),
            "setup_time": getattr(diagnostics, "setup_time_seconds", None),
            "message": getattr(diagnostics, "message", None),
        }
        for key, value in mapping.items():
            if key in ("backend", "backend_version", "backend_status", "message"):
                text = str(value) if value else "-"
            else:
                text = _format_number(value)
            self.diagnostic_labels[key].setText(text)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_export(self) -> None:
        if self._model is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            S.t("qp.solution.export.dialog_title"),
            S.t("qp.solution.export.default_name"),
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        Path(path).write_text(qp_model_to_json(self._model), encoding="utf-8")

    # ------------------------------------------------------------------
    # Localization and theme
    # ------------------------------------------------------------------
    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('qp.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("qp.solution.back"))
        self.btn_export.setText(S.t("qp.solution.export.button"))
        self.summary_section.set_title(S.t("qp.solution.summary.section"))
        self.dependency_notice.setText(S.t("qp.solution.dependency_failure"))
        self.local_notice.setText(S.t("qp.solution.local_notice"))
        self.variables_section.set_title(S.t("qp.solution.variables.section"))
        self.variables_hint.setText(S.t("qp.solution.variables.hint"))
        self.variables_empty.setText(S.t("qp.solution.variables.empty"))
        self.constraints_section.set_title(S.t("qp.solution.constraints.section"))
        self.constraints_hint.setText(S.t("qp.solution.constraints.hint"))
        self.constraints_empty.setText(S.t("qp.solution.constraints.empty"))
        self.duals_section.set_title(S.t("qp.solution.duals.section"))
        self.duals_hint.setText(S.t("qp.solution.duals.hint"))
        self.duals_unavailable.setText(S.t("qp.solution.duals.unavailable"))
        self.residuals_section.set_title(S.t("qp.solution.residuals.section"))
        self.residuals_hint.setText(S.t("qp.solution.residuals.hint"))
        for key in _RESIDUAL_ROWS:
            self.residual_labels[f"{key}_label"].setText(S.t(f"qp.solution.residuals.{key}"))
        self.validation_section.set_title(S.t("qp.solution.validation_report.section"))
        self.validation_hint.setText(S.t("qp.solution.validation_report.hint"))
        self.diagnostics_section.set_title(S.t("qp.solution.diagnostics.section"))
        self.diagnostics_hint.setText(S.t("qp.solution.diagnostics.backend_status_hint"))
        for key in _DIAGNOSTIC_ROWS:
            self.diagnostic_labels[f"{key}_label"].setText(S.t(f"qp.solution.diagnostics.{key}"))
        self.visualization_section.set_title(S.t("qp.solution.visualization.section"))
        self.contour_plot.refresh_strings()
        self._render()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.status.setStyleSheet(f"color: {t.text}; font-size: 16px; font-weight: 700;")
        self.explanation.setStyleSheet(f"color: {t.text_muted};")
        self.dependency_notice.setStyleSheet(f"color: {t.danger}; font-weight: 600;")
        self.objective_value.setStyleSheet(f"color: {t.accent}; font-size: 15px; font-weight: 700;")
        self.objective_formula.setStyleSheet(f"color: {t.text_faint};")
        self.local_notice.setStyleSheet(f"color: {t.warning};")
        self.validation_status.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        self.validation_limitations.setStyleSheet(f"color: {t.text_muted};")
        for label in (
            self.variables_hint,
            self.variables_empty,
            self.constraints_hint,
            self.constraints_empty,
            self.duals_hint,
            self.duals_unavailable,
            self.residuals_hint,
            self.validation_hint,
            self.diagnostics_hint,
        ):
            label.setStyleSheet(f"color: {t.text_muted};")
        for key, label in list(self.residual_labels.items()) + list(self.diagnostic_labels.items()):
            color = t.text if key.endswith("_label") else t.text_muted
            label.setStyleSheet(f"color: {color};")
        self.contour_plot.refresh_theme()


def _localized_limitation(index: int, original: str) -> str:
    """Prefer the translated wording, falling back to the validator's own text.

    The fallback keeps a limitation visible if the validator ever reports more
    of them than this release has translations for. Silently dropping an honest
    caveat would be worse than showing it untranslated.
    """
    key = f"qp.solution.validation_report.limitation.{index + 1}"
    translated = S.t(key)
    return original if translated == key else translated


def _bound_position(variable, value: float) -> str:
    lower, upper = variable.bounds.lb, variable.bounds.ub
    if lower is not None and abs(value - float(lower)) <= _ACTIVITY_TOLERANCE:
        return "at_lower"
    if upper is not None and abs(value - float(upper)) <= _ACTIVITY_TOLERANCE:
        return "at_upper"
    return "interior"


def _constraint_state(constraint, slack: float) -> str:
    if constraint.relation is Relation.EQ:
        if abs(slack) <= _ACTIVITY_TOLERANCE:
            return "binding"
        return "violated"
    if constraint.relation is Relation.LE:
        if slack < -_ACTIVITY_TOLERANCE:
            return "violated"
    elif slack > _ACTIVITY_TOLERANCE:
        return "violated"
    if abs(slack) <= _ACTIVITY_TOLERANCE:
        return "binding"
    return "slack_state"


def _is_dependency_failure(solution: QPSolution) -> bool:
    """The backend reports a missing dependency without a backend version."""
    diagnostics = solution.diagnostics
    return (
        solution.status is QPSolveStatus.NOT_SOLVED
        and diagnostics.success is False
        and diagnostics.backend_version is None
        and diagnostics.status is None
    )
