from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.knapsack.solution import KnapsackSolution
from optees.domain.models.knapsack.knapsack_model import KnapsackModel
from optees.presentation.views.lp_view.section import Section


class KnapsackSolutionView(QWidget):
    """Result page for 0/1 knapsack solves."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop)
        outer.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("btnBack")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setFlat(True)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        header.addStretch(1)
        root.addLayout(header)

        self.status_sec = Section()
        self.status_line = QLabel()
        self.status_line.setObjectName("knapsackStatusLine")
        self.status_line.setTextFormat(Qt.RichText)
        self.status_line.setWordWrap(True)
        self.summary_line = QLabel()
        self.summary_line.setWordWrap(True)
        self.message_line = QLabel()
        self.message_line.setWordWrap(True)
        self.status_sec.body.addWidget(self.status_line)
        self.status_sec.body.addWidget(self.summary_line)
        self.status_sec.body.addWidget(self.message_line)
        root.addWidget(self.status_sec)

        self.table_sec = Section()
        self.table = QTableView()
        self.table.setObjectName("knapsackSolutionTable")
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setMinimumHeight(340)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._model = QStandardItemModel(self)
        self.table.setModel(self._model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_sec.body.addWidget(self.table)
        root.addWidget(self.table_sec)

        root.addStretch(1)

        self.solution_table = self.table
        self._problem: Optional[KnapsackModel] = None
        self._solution: Optional[KnapsackSolution] = None

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def set_problem(self, model: KnapsackModel) -> None:
        self._problem = model
        self._rebuild()

    def set_solution(self, solution: KnapsackSolution) -> None:
        self._solution = solution
        self._rebuild()

    def refresh_strings(self) -> None:
        self.btn_back.setText(S.t("knapsack.sol.back"))
        self.status_sec.set_title(S.t("knapsack.sol.status_section"))
        self.table_sec.set_title(S.t("knapsack.sol.table_section"))
        self._rebuild()

    def refresh_theme(self) -> None:
        self.status_sec.refresh_theme()
        self.table_sec.refresh_theme()
        fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        secondary = theme.secondary_text_css(self)
        self.status_line.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {fg};")
        self.summary_line.setStyleSheet(secondary)
        self.message_line.setStyleSheet(secondary)

    def _rebuild(self) -> None:
        self._model.clear()
        self._model.setHorizontalHeaderLabels(
            [
                S.t("knapsack.sol.columns.selected"),
                S.t("knapsack.sol.columns.item"),
                S.t("knapsack.sol.columns.value"),
                S.t("knapsack.sol.columns.weight"),
                S.t("knapsack.sol.columns.ratio"),
            ]
        )

        if self._solution is None:
            self.status_line.setText(S.t("knapsack.sol.empty"))
            self.summary_line.setText("")
            self.message_line.setText("")
            return

        status = getattr(self._solution.status, "value", self._solution.status)
        objective = self._solution.objective
        self.status_line.setText(
            S.t(
                "knapsack.sol.status_line",
                status=status,
                objective=_fmt(objective),
            )
        )

        capacity = self._problem.capacity if self._problem is not None else None
        self.summary_line.setText(
            S.t(
                "knapsack.sol.summary",
                total_weight=self._solution.total_weight,
                capacity=_fmt(capacity),
                remaining=_fmt(self._solution.remaining_capacity),
                selected=len(self._solution.selected_indices),
            )
        )

        message = self._solution.diagnostics.message
        method = self._solution.diagnostics.method
        if message:
            self.message_line.setText(
                S.t("knapsack.sol.message", method=method or "-", message=message)
            )
        else:
            self.message_line.setText(S.t("knapsack.sol.method", method=method or "-"))

        if self._problem is None:
            return

        selected = set(self._solution.selected_indices)
        for index, item in enumerate(self._problem.items):
            ratio = None if item.weight == 0 else item.value / item.weight
            row = [
                QStandardItem(S.t("knapsack.sol.yes") if index in selected else S.t("knapsack.sol.no")),
                QStandardItem(item.name),
                QStandardItem(_fmt(item.value)),
                QStandardItem(str(item.weight)),
                QStandardItem(_fmt(ratio)),
            ]
            for col, cell in enumerate(row):
                cell.setEditable(False)
                if col in (2, 3, 4):
                    cell.setData(Qt.AlignRight | Qt.AlignVCenter, Qt.TextAlignmentRole)
                if index in selected:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
            self._model.appendRow(row)


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)

