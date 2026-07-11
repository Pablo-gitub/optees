from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.models.nlp.nlp_model import NLPModel
from optees.presentation.views.lp_view.section import Section


class NLPSolutionView(QWidget):
    """Result view for local continuous nonlinear optimization runs."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solution: Optional[NLPSolution] = None
        self._model: Optional[NLPModel] = None

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
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("nlpSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        summary = Section()
        self.status = QLabel()
        self.status.setObjectName("nlpSolutionStatus")
        self.status.setWordWrap(True)
        summary.body.addWidget(self.status)
        self.local_notice = QLabel()
        self.local_notice.setWordWrap(True)
        summary.body.addWidget(self.local_notice)
        self.summary_section = summary
        root.addWidget(summary)

        details = Section()
        self.detail_labels: dict[str, QLabel] = {}
        for key in (
            "objective",
            "method",
            "iterations",
            "evaluations",
            "feasibility",
            "message",
        ):
            row = QHBoxLayout()
            label = QLabel()
            value = QLabel()
            value.setObjectName(f"nlpSolution{key.title()}")
            value.setWordWrap(True)
            row.addWidget(label)
            row.addWidget(value, 1)
            details.body.addLayout(row)
            self.detail_labels[f"{key}_label"] = label
            self.detail_labels[key] = value
        self.details_section = details
        root.addWidget(details)

        candidate = Section()
        self.candidate_hint = QLabel()
        self.candidate_hint.setWordWrap(True)
        candidate.body.addWidget(self.candidate_hint)
        self.candidate_table = _make_table()
        self.candidate_table.setObjectName("nlpCandidateTable")
        candidate.body.addWidget(self.candidate_table)
        self.candidate_section = candidate
        root.addWidget(candidate)

        trace = Section()
        self.trace_hint = QLabel()
        self.trace_hint.setWordWrap(True)
        trace.body.addWidget(self.trace_hint)
        self.trace_table = _make_table()
        self.trace_table.setObjectName("nlpConvergenceTable")
        trace.body.addWidget(self.trace_table)
        self.trace_section = trace
        root.addWidget(trace)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render_solution()

    def set_problem(self, model: NLPModel) -> None:
        """Keep bounds so the result view can report candidate feasibility."""
        self._model = model
        self._render_solution()

    def set_solution(self, solution: NLPSolution) -> None:
        self._solution = solution
        self._render_solution()

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('nlp.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("nlp.solution.back"))
        self.summary_section.set_title(S.t("nlp.solution.summary.section"))
        self.local_notice.setText(S.t("nlp.solution.local_notice"))
        self.details_section.set_title(S.t("nlp.solution.details.section"))
        for key in (
            "objective",
            "method",
            "iterations",
            "evaluations",
            "feasibility",
            "message",
        ):
            self.detail_labels[f"{key}_label"].setText(S.t(f"nlp.solution.details.{key}"))
        self.candidate_section.set_title(S.t("nlp.solution.candidate.section"))
        self.candidate_hint.setText(S.t("nlp.solution.candidate.hint"))
        self.trace_section.set_title(S.t("nlp.solution.trace.section"))
        self.trace_hint.setText(S.t("nlp.solution.trace.hint"))
        self._render_solution()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.status.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        self.local_notice.setStyleSheet(f"color: {t.warning};")
        self.candidate_hint.setStyleSheet(f"color: {t.text_muted};")
        self.trace_hint.setStyleSheet(f"color: {t.text_muted};")
        for key, label in self.detail_labels.items():
            color = t.text if key.endswith("_label") else t.text_muted
            label.setStyleSheet(f"color: {color};")

    def _render_solution(self) -> None:
        solution = self._solution
        if solution is None:
            self.status.setText(S.t("nlp.solution.empty"))
            for key in (
                "objective",
                "method",
                "iterations",
                "evaluations",
                "feasibility",
                "message",
            ):
                self.detail_labels[key].setText("-")
            self._set_candidate_rows({})
            self._set_trace_rows(())
            return

        self.status.setText(
            S.t(
                "nlp.solution.status_line",
                status=S.t(_status_key(solution.status.value)),
            )
        )
        extras = solution.extras
        self.detail_labels["objective"].setText(_format_number(solution.objective))
        self.detail_labels["method"].setText(str(extras.get("method") or "-"))
        self.detail_labels["iterations"].setText(_format_number(solution.iterations))
        self.detail_labels["evaluations"].setText(_format_number(solution.evaluations))
        self.detail_labels["feasibility"].setText(self._feasibility_text(solution))
        self.detail_labels["message"].setText(solution.termination_message or "-")
        self._set_candidate_rows(solution.values)
        self._set_trace_rows(solution.convergence_history)
        self.trace_hint.setText(
            S.t("nlp.solution.trace.hint")
            if solution.convergence_history
            else S.t("nlp.solution.trace.empty")
        )

    def _feasibility_text(self, solution: NLPSolution) -> str:
        if self._model is None:
            return S.t("nlp.solution.feasibility.unavailable")
        for variable in self._model.variables:
            value = solution.values.get(variable.name)
            if value is None:
                return S.t("nlp.solution.feasibility.unavailable")
            if not variable.contains(value):
                return S.t("nlp.solution.feasibility.violated")
        return S.t("nlp.solution.feasibility.within_bounds")

    def _set_candidate_rows(self, values: dict[str, float]) -> None:
        self.candidate_table.setColumnCount(2)
        self.candidate_table.setHorizontalHeaderLabels(
            [S.t("nlp.solution.candidate.variable"), S.t("nlp.solution.candidate.value")]
        )
        self.candidate_table.setRowCount(len(values))
        for row, (name, value) in enumerate(values.items()):
            self.candidate_table.setItem(row, 0, QTableWidgetItem(name))
            self.candidate_table.setItem(row, 1, QTableWidgetItem(_format_number(value)))

    def _set_trace_rows(self, history: tuple[float, ...]) -> None:
        self.trace_table.setColumnCount(2)
        self.trace_table.setHorizontalHeaderLabels(
            [S.t("nlp.solution.trace.iteration"), S.t("nlp.solution.trace.objective")]
        )
        self.trace_table.setRowCount(len(history))
        for index, value in enumerate(history):
            self.trace_table.setItem(index, 0, QTableWidgetItem(str(index)))
            self.trace_table.setItem(index, 1, QTableWidgetItem(_format_number(value)))


def _make_table() -> QTableWidget:
    table = QTableWidget()
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
    table.setMinimumHeight(130)
    return table


def _format_number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.10g}"
    except (TypeError, ValueError):
        return str(value)


def _status_key(status: str) -> str:
    normalized = status.lower()
    return {
        "converged": "nlp.solution.status.converged",
        "iterationlimit": "nlp.solution.status.iteration_limit",
        "failed": "nlp.solution.status.failed",
        "notsolved": "nlp.solution.status.not_solved",
    }.get(normalized, "nlp.solution.status.not_solved")
