from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.packing.solution import PackingSolution, PackingSolveResult
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus
from optees.presentation.views.lp_view.section import Section
from optees.presentation.views.packing_plot_widget import Packing3DPlotWidget


class PackingSolutionView(QWidget):
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[SingleContainerPackingModel] = None
        self._result: Optional[PackingSolveResult] = None

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
        self.btn_back.setObjectName("packingSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        self.summary_section = Section()
        self.status = QLabel()
        self.status.setObjectName("packingSolutionStatus")
        self.status.setWordWrap(True)
        self.summary_section.body.addWidget(self.status)
        self.recovery_notice = QLabel()
        self.recovery_notice.setObjectName("packingRecoveryNotice")
        self.recovery_notice.setWordWrap(True)
        self.summary_section.body.addWidget(self.recovery_notice)
        self.metrics = QLabel()
        self.metrics.setObjectName("packingSolutionMetrics")
        self.metrics.setWordWrap(True)
        self.summary_section.body.addWidget(self.metrics)
        self.safety_notice = QLabel()
        self.safety_notice.setObjectName("packingSafetyNotice")
        self.safety_notice.setWordWrap(True)
        self.summary_section.body.addWidget(self.safety_notice)
        root.addWidget(self.summary_section)

        self.plot_section = Section()
        self.plot = Packing3DPlotWidget()
        self.plot.setObjectName("packing3DPlot")
        self.plot_section.body.addWidget(self.plot)
        root.addWidget(self.plot_section)

        self.placements_section = Section()
        self.placements_table = _table("packingPlacementsTable")
        self.placements_table.itemSelectionChanged.connect(self._select_placement)
        self.placements_section.body.addWidget(self.placements_table)
        root.addWidget(self.placements_section)

        self.excluded_section = Section()
        self.excluded = QLabel()
        self.excluded.setObjectName("packingExcludedItems")
        self.excluded.setWordWrap(True)
        self.excluded_section.body.addWidget(self.excluded)
        root.addWidget(self.excluded_section)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render()

    def set_problem(self, model: SingleContainerPackingModel) -> None:
        self._model = model
        self.plot.set_problem(model)
        self._render()

    def set_solution(self, result: PackingSolveResult) -> None:
        self._result = result
        self.plot.set_solution(self._display_solution())
        self._render()

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('packing.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("packing.solution.back"))
        self.summary_section.set_title(S.t("packing.solution.summary.section"))
        self.plot_section.set_title(S.t("packing.solution.visualization.section"))
        self.placements_section.set_title(S.t("packing.solution.placements.section"))
        self.excluded_section.set_title(S.t("packing.solution.excluded.section"))
        self.plot.refresh_strings()
        self.safety_notice.setText(S.t("packing.solution.safety_notice"))
        self._render()

    def refresh_theme(self) -> None:
        palette = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {palette.text};")
        self.status.setStyleSheet(f"color: {palette.text}; font-weight: 600;")
        self.recovery_notice.setStyleSheet(f"color: {palette.warning}; font-weight: 600;")
        self.metrics.setStyleSheet(f"color: {palette.text_muted};")
        self.safety_notice.setStyleSheet(f"color: {palette.warning};")
        self.excluded.setStyleSheet(f"color: {palette.text_muted};")
        self.plot.refresh_theme()

    def _display_solution(self) -> Optional[PackingSolution]:
        if self._result is None:
            return None
        if self._result.requested.has_incumbent():
            return self._result.requested
        if self._result.has_recovery():
            return self._result.recovery
        return self._result.requested

    def _render(self) -> None:
        if self._result is None or self._model is None:
            self.status.setText(S.t("packing.solution.empty"))
            self.recovery_notice.clear()
            self.metrics.clear()
            self._set_placement_rows(None)
            self.excluded.setText("-")
            return

        requested = self._result.requested
        displayed = self._display_solution()
        self.status.setText(
            S.t(
                "packing.solution.status_line",
                status=S.t(_status_key(requested.status)),
            )
        )
        if self._result.has_recovery():
            self.recovery_notice.setText(S.t("packing.solution.recovery_notice"))
        else:
            self.recovery_notice.clear()

        if displayed is None or not displayed.has_incumbent():
            detail = displayed.diagnostics.message if displayed is not None else None
            self.metrics.setText(detail or S.t("packing.solution.no_incumbent"))
            self._set_placement_rows(None)
            self.excluded.setText("-")
            self.plot.set_solution(displayed)
            return

        container_volume = self._model.container.dimensions.volume()
        free_volume = max(0.0, container_volume - displayed.used_volume)
        item_by_id = {item.item_id: item for item in self._model.items}
        resource_parts = []
        for capacity in self._model.container.capacities:
            used = sum(
                item_by_id[placement.item_id].consumption(capacity.name)
                for placement in displayed.placements
            )
            resource_parts.append(
                f"{capacity.name}: {_number(used)} / {_number(capacity.limit)}"
            )
        self.metrics.setText(
            S.t(
                "packing.solution.metrics",
                objective=_number(displayed.objective),
                loaded=len(displayed.placements),
                excluded=len(displayed.excluded_instance_ids),
                used_volume=_number(displayed.used_volume),
                free_volume=_number(free_volume),
                gap=_number(displayed.diagnostics.relative_gap),
                bound=_number(displayed.diagnostics.best_bound),
                time=_elapsed(displayed),
                resources="; ".join(resource_parts) or "-",
                gravity=S.t(f"packing.options.gravity_{self._model.gravity_mode.value}"),
            )
        )
        self._set_placement_rows(displayed)
        self.excluded.setText(
            ", ".join(displayed.excluded_instance_ids)
            if displayed.excluded_instance_ids
            else S.t("packing.solution.excluded.none")
        )
        self.plot.set_solution(displayed)

    def _set_placement_rows(self, solution: Optional[PackingSolution]) -> None:
        headers = (
            "item", "unit", "x", "y", "z", "length", "width", "height",
            "orientation", "value",
        )
        self.placements_table.setColumnCount(len(headers))
        self.placements_table.setHorizontalHeaderLabels(
            [S.t(f"packing.solution.placements.{header}") for header in headers]
        )
        placements = solution.placements if solution is not None else ()
        self.placements_table.setRowCount(len(placements))
        for row, placement in enumerate(placements):
            values = (
                placement.item_name,
                placement.unit_index,
                placement.x,
                placement.y,
                placement.z,
                placement.length,
                placement.width,
                placement.height,
                placement.orientation_code,
                placement.value,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value) if column in (0, 1, 8) else _number(value))
                item.setTextAlignment(Qt.AlignCenter)
                if column == 0:
                    item.setData(Qt.UserRole, placement.instance_id)
                self.placements_table.setItem(row, column, item)

    def _select_placement(self) -> None:
        row = self.placements_table.currentRow()
        item = self.placements_table.item(row, 0) if row >= 0 else None
        self.plot.select_instance(str(item.data(Qt.UserRole)) if item is not None else None)


def _table(object_name: str) -> QTableWidget:
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setMinimumHeight(180)
    return table


def _status_key(status: MILPSolveStatus) -> str:
    return {
        MILPSolveStatus.OPTIMAL: "packing.solution.status.optimal",
        MILPSolveStatus.FEASIBLE: "packing.solution.status.feasible",
        MILPSolveStatus.INFEASIBLE: "packing.solution.status.infeasible",
        MILPSolveStatus.UNBOUNDED: "packing.solution.status.unbounded",
    }.get(status, "packing.solution.status.not_solved")


def _number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


def _elapsed(solution: PackingSolution) -> str:
    if solution.diagnostics.wall_time_ms is not None:
        return f"{solution.diagnostics.wall_time_ms / 1000:.3g} s"
    if solution.diagnostics.wall_time is not None:
        return f"{solution.diagnostics.wall_time:.3g} s"
    return "-"
