from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QStandardItem, QStandardItemModel
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
from optees.core.design import tokens
from optees.core.qss import qcolor
from optees.application.services.categorical_presentation import bounded_categories
from optees.presentation.views.lp_view.section import Section


class _CapacityUsageWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("knapsackCapacityChart")
        self.setMinimumHeight(130)
        self.setMinimumWidth(320)
        self._problem: Optional[object] = None
        self._solution: Optional[object] = None

    def set_data(
        self,
        problem: Optional[object],
        solution: Optional[object],
    ) -> None:
        self._problem = problem
        self._solution = solution
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(14, 12, -14, -12)

        t = tokens(theme.is_dark())
        fg = qcolor(t.text)
        muted = qcolor(t.text_muted)
        used_color = qcolor(t.success)
        remaining_color = qcolor(t.text_muted)
        remaining_color.setAlpha(60)

        painter.setPen(fg)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        painter.setFont(title_font)
        title_key = (
            "knapsack.sol.charts.resource_title"
            if self._problem is not None
            and self._solution is not None
            and hasattr(self._problem, "resources")
            and hasattr(self._solution, "resource_usage_totals")
            else "knapsack.sol.charts.capacity_title"
        )
        painter.drawText(rect.left(), rect.top(), rect.width(), 22, Qt.AlignLeft, S.t(title_key))

        if self._problem is None or self._solution is None:
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignCenter, S.t("knapsack.sol.charts.no_data"))
            return

        if hasattr(self._problem, "resources") and hasattr(
            self._solution,
            "resource_usage_totals",
        ):
            self._paint_resource_usage(painter, rect, fg, muted, used_color, remaining_color)
            return

        if not hasattr(self._problem, "capacity") or not hasattr(
            self._solution,
            "total_weight",
        ):
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignCenter, S.t("knapsack.sol.charts.no_data"))
            return

        capacity = max(float(self._problem.capacity), 0.0)
        used = max(float(self._solution.total_weight), 0.0)
        ratio = 0.0 if capacity <= 0 else min(used / capacity, 1.0)

        bar = QRectF(rect.left(), rect.top() + 42, rect.width(), 28)
        painter.setPen(QPen(muted, 1))
        painter.setBrush(remaining_color)
        painter.drawRoundedRect(bar, 6, 6)
        if ratio > 0:
            used_bar = QRectF(bar.left(), bar.top(), bar.width() * ratio, bar.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(used_color)
            painter.drawRoundedRect(used_bar, 6, 6)

        painter.setPen(fg)
        painter.setFont(QFont())
        painter.drawText(
            rect.left(),
            rect.top() + 86,
            rect.width(),
            22,
            Qt.AlignLeft,
            S.t(
                "knapsack.sol.charts.capacity_text",
                used=_fmt(self._solution.total_weight),
                capacity=_fmt(self._problem.capacity),
                remaining=_fmt(self._solution.remaining_capacity),
            ),
        )

    def _paint_resource_usage(
        self,
        painter: QPainter,
        rect,
        fg: QColor,
        muted: QColor,
        used_color: QColor,
        remaining_color: QColor,
    ) -> None:
        resources = list(getattr(self._problem, "resources", ()))
        usages = list(getattr(self._solution, "resource_usage_totals", ()))
        remaining = list(getattr(self._solution, "remaining_capacities", ()))
        if not resources:
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignCenter, S.t("knapsack.sol.charts.no_data"))
            return

        painter.setFont(QFont())
        bar_height = 14
        row_height = 34
        top = rect.top() + 36
        for index, resource in enumerate(resources):
            if top + index * row_height + row_height > rect.bottom():
                break
            capacity = max(float(resource.capacity), 0.0)
            used = max(float(usages[index] if index < len(usages) else 0.0), 0.0)
            left = float(remaining[index] if index < len(remaining) else capacity - used)
            ratio = 0.0 if capacity <= 0 else min(used / capacity, 1.0)
            y = top + index * row_height

            painter.setPen(fg)
            painter.drawText(
                rect.left(),
                y,
                rect.width(),
                16,
                Qt.AlignLeft,
                f"{resource.name}: {_fmt(used)} / {_fmt(capacity)}; {_fmt(left)}",
            )

            bar = QRectF(rect.left(), y + 18, rect.width(), bar_height)
            painter.setPen(QPen(muted, 1))
            painter.setBrush(remaining_color)
            painter.drawRoundedRect(bar, 4, 4)
            if ratio > 0:
                used_bar = QRectF(bar.left(), bar.top(), bar.width() * ratio, bar.height())
                painter.setPen(Qt.NoPen)
                painter.setBrush(used_color)
                painter.drawRoundedRect(used_bar, 4, 4)


class _ItemBarsWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("knapsackItemBars")
        self.setMinimumHeight(240)
        self.setMinimumWidth(420)
        self._problem: Optional[object] = None
        self._solution: Optional[object] = None

    def set_data(
        self,
        problem: Optional[object],
        solution: Optional[object],
    ) -> None:
        self._problem = problem
        self._solution = solution
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(14, 12, -14, -12)

        t = tokens(theme.is_dark())
        fg = qcolor(t.text)
        muted = qcolor(t.text_muted)
        value_color = qcolor(t.accent)
        weight_color = qcolor(t.warning)
        selected_outline = qcolor(t.success)
        dim_alpha = 85

        painter.setPen(fg)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        painter.setFont(title_font)
        painter.drawText(rect.left(), rect.top(), rect.width(), 22, Qt.AlignLeft, S.t("knapsack.sol.charts.items_title"))

        if self._problem is None or self._solution is None or not self._problem.items:
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignCenter, S.t("knapsack.sol.charts.no_data"))
            return

        all_items = list(self._problem.items)
        items, window = bounded_categories(all_items)
        selected = set(self._solution.selected_indices)
        max_value = max([item.value for item in items] + [1.0])
        weight_metrics = [_resource_metric(item) for item in items]
        max_weight = max(weight_metrics + [1.0])

        chart = rect.adjusted(0, 46, 0, -34)
        painter.setPen(QPen(muted, 1))
        painter.drawLine(chart.left(), chart.bottom(), chart.right(), chart.bottom())

        group_w = chart.width() / max(len(items), 1)
        bar_w = max(6.0, min(18.0, group_w * 0.22))
        gap = max(3.0, bar_w * 0.35)

        for index, item in enumerate(items):
            cx = chart.left() + group_w * index + group_w / 2
            value_h = 0.0 if max_value <= 0 else chart.height() * (item.value / max_value)
            weight_h = 0.0 if max_weight <= 0 else chart.height() * (weight_metrics[index] / max_weight)

            value_rect = QRectF(cx - bar_w - gap / 2, chart.bottom() - value_h, bar_w, value_h)
            weight_rect = QRectF(cx + gap / 2, chart.bottom() - weight_h, bar_w, weight_h)

            value_brush = QColor(value_color)
            weight_brush = QColor(weight_color)
            if index not in selected:
                value_brush.setAlpha(dim_alpha)
                weight_brush.setAlpha(dim_alpha)

            painter.setPen(Qt.NoPen)
            painter.setBrush(value_brush)
            painter.drawRoundedRect(value_rect, 3, 3)
            painter.setBrush(weight_brush)
            painter.drawRoundedRect(weight_rect, 3, 3)

            if index in selected:
                outline = QRectF(
                    min(value_rect.left(), weight_rect.left()) - 4,
                    min(value_rect.top(), weight_rect.top()) - 4,
                    (weight_rect.right() - value_rect.left()) + 8,
                    (chart.bottom() - min(value_rect.top(), weight_rect.top())) + 8,
                )
                painter.setPen(QPen(selected_outline, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(outline, 6, 6)

            label = item.name
            if len(label) > 8:
                label = label[:7] + "…"
            painter.setPen(muted)
            painter.setFont(QFont())
            painter.drawText(
                int(chart.left() + group_w * index),
                int(chart.bottom() + 4),
                int(group_w),
                18,
                Qt.AlignCenter,
                label,
            )

        painter.setPen(fg)
        legend_key = (
            "knapsack.sol.charts.multi_legend"
            if any(hasattr(item, "resource_usage") for item in items)
            else "knapsack.sol.charts.legend"
        )
        painter.drawText(
            rect.left(),
            rect.bottom() - 18,
            rect.width(),
            18,
            Qt.AlignLeft,
            S.t(legend_key),
        )
        if window.truncated:
            painter.setPen(muted)
            painter.drawText(
                rect.left(),
                rect.top(),
                rect.width(),
                22,
                Qt.AlignRight,
                S.t(
                    "knapsack.sol.charts.window",
                    shown=window.displayed,
                    total=window.total,
                ),
            )


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

        self.chart_sec = Section()
        chart_row = QHBoxLayout()
        chart_row.setContentsMargins(0, 0, 0, 0)
        chart_row.setSpacing(12)
        self.capacity_chart = _CapacityUsageWidget()
        self.item_bars = _ItemBarsWidget()
        chart_row.addWidget(self.capacity_chart, 1)
        chart_row.addWidget(self.item_bars, 2)
        self.chart_sec.body.addLayout(chart_row)
        root.addWidget(self.chart_sec)

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
        self._problem: Optional[object] = None
        self._solution: Optional[object] = None

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def set_problem(self, model: object) -> None:
        self._problem = model
        self._rebuild()

    def set_solution(self, solution: object) -> None:
        self._solution = solution
        self._rebuild()

    def refresh_strings(self) -> None:
        self.btn_back.setText(S.t("knapsack.sol.back"))
        self.status_sec.set_title(S.t("knapsack.sol.status_section"))
        self.chart_sec.set_title(S.t("knapsack.sol.charts.section"))
        self.table_sec.set_title(S.t("knapsack.sol.table_section"))
        self._rebuild()

    def refresh_theme(self) -> None:
        self.status_sec.refresh_theme()
        self.chart_sec.refresh_theme()
        self.table_sec.refresh_theme()
        fg = tokens(theme.is_dark()).text
        secondary = theme.secondary_text_css(self)
        self.status_line.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {fg};")
        self.summary_line.setStyleSheet(secondary)
        self.message_line.setStyleSheet(secondary)
        self.capacity_chart.update()
        self.item_bars.update()

    def _rebuild(self) -> None:
        self._model.clear()
        self.capacity_chart.set_data(self._problem, self._solution)
        self.item_bars.set_data(self._problem, self._solution)
        has_quantities = self._solution is not None and hasattr(self._solution, "quantities")
        has_fractions = self._solution is not None and hasattr(self._solution, "fractions")
        has_resource_usage = (
            self._problem is not None
            and bool(getattr(self._problem, "items", ()))
            and hasattr(getattr(self._problem, "items")[0], "resource_usage")
        )
        resource_names = (
            list(self._problem.resource_names())
            if has_resource_usage and hasattr(self._problem, "resource_names")
            else []
        )
        has_max_quantity = (
            self._problem is not None
            and bool(getattr(self._problem, "items", ()))
            and hasattr(getattr(self._problem, "items")[0], "max_quantity")
        )
        headers = [S.t("knapsack.sol.columns.selected")]
        if has_quantities:
            headers.append(S.t("knapsack.sol.columns.quantity"))
        if has_fractions:
            headers.append(S.t("knapsack.sol.columns.fraction"))
        headers.extend(
            [
                S.t("knapsack.sol.columns.item"),
                S.t("knapsack.sol.columns.value"),
            ]
        )
        if has_resource_usage:
            headers.extend(resource_names)
        else:
            headers.append(S.t("knapsack.sol.columns.weight"))
        if has_max_quantity:
            headers.append(S.t("knapsack.sol.columns.max_quantity"))
        headers.append(
            S.t("knapsack.sol.columns.value_usage")
            if has_resource_usage
            else S.t("knapsack.sol.columns.ratio")
        )
        self._model.setHorizontalHeaderLabels(headers)

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

        if hasattr(self._solution, "resource_usage_totals"):
            resources_text = self._format_resource_summary()
            self.summary_line.setText(
                S.t(
                    "knapsack.sol.multi_summary",
                    resources=resources_text,
                    selected=len(self._solution.selected_indices),
                )
            )
        else:
            capacity = (
                self._problem.capacity
                if self._problem is not None and hasattr(self._problem, "capacity")
                else None
            )
            self.summary_line.setText(
                S.t(
                    "knapsack.sol.summary",
                    total_weight=_fmt(self._solution.total_weight),
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
        quantities = getattr(self._solution, "quantities", None)
        fractions = getattr(self._solution, "fractions", None)
        for index, item in enumerate(self._problem.items):
            metric = _resource_metric(item)
            ratio = None if metric == 0 else item.value / metric
            row = [
                QStandardItem(S.t("knapsack.sol.yes") if index in selected else S.t("knapsack.sol.no")),
            ]
            if quantities is not None:
                quantity = quantities[index] if index < len(quantities) else 0
                row.append(QStandardItem(_fmt(quantity)))
            if fractions is not None:
                fraction = fractions[index] if index < len(fractions) else 0.0
                row.append(QStandardItem(_fmt(fraction)))
            row.extend(
                [
                    QStandardItem(item.name),
                    QStandardItem(_fmt(item.value)),
                ]
            )
            if has_resource_usage:
                for amount in item.resource_usage:
                    row.append(QStandardItem(_fmt(amount)))
            else:
                row.append(QStandardItem(str(item.weight)))
            if has_max_quantity:
                row.append(QStandardItem(str(getattr(item, "max_quantity", ""))))
            row.append(QStandardItem(_fmt(ratio)))
            for col, cell in enumerate(row):
                cell.setEditable(False)
                if col != 0 and cell.text() != item.name:
                    cell.setData(Qt.AlignRight | Qt.AlignVCenter, Qt.TextAlignmentRole)
                if index in selected:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
            self._model.appendRow(row)

    def _format_resource_summary(self) -> str:
        if self._problem is None or self._solution is None:
            return "-"
        resources = list(getattr(self._problem, "resources", ()))
        usages = list(getattr(self._solution, "resource_usage_totals", ()))
        remaining = list(getattr(self._solution, "remaining_capacities", ()))
        chunks = []
        for index, resource in enumerate(resources):
            used = usages[index] if index < len(usages) else 0.0
            left = remaining[index] if index < len(remaining) else resource.capacity - used
            chunks.append(
                f"{resource.name} {_fmt(used)}/{_fmt(resource.capacity)} ({_fmt(left)})"
            )
        return "; ".join(chunks) if chunks else "-"


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)


def _resource_metric(item: object) -> float:
    if hasattr(item, "weight"):
        return float(getattr(item, "weight"))
    if hasattr(item, "resource_usage"):
        return float(sum(getattr(item, "resource_usage")))
    return 0.0
