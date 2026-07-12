from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QPolygonF
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
from optees.domain.entities.graph.solution import ShortestPathSolution
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.domain.value_objects.graph.shortest_path_status import ShortestPathStatus
from optees.presentation.views.lp_view.section import Section


class GraphSolutionView(QWidget):
    """Explain and draw the route returned by a Dijkstra run."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[ShortestPathModel] = None
        self._solution: Optional[ShortestPathSolution] = None

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
        self.btn_back.setObjectName("graphSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        summary = Section()
        self.status = QLabel()
        self.status.setObjectName("graphSolutionStatus")
        self.status.setWordWrap(True)
        summary.body.addWidget(self.status)
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        summary.body.addWidget(self.explanation)
        self.summary_section = summary
        root.addWidget(summary)

        route = Section()
        self.route = QLabel()
        self.route.setObjectName("graphRouteText")
        self.route.setWordWrap(True)
        route.body.addWidget(self.route)
        self.distance = QLabel()
        self.distance.setObjectName("graphDistanceText")
        route.body.addWidget(self.distance)
        self.route_section = route
        root.addWidget(route)

        diagram = Section()
        self.diagram_hint = QLabel()
        self.diagram_hint.setWordWrap(True)
        diagram.body.addWidget(self.diagram_hint)
        self.diagram = GraphDiagram()
        self.diagram.setObjectName("graphRouteDiagram")
        diagram.body.addWidget(self.diagram)
        self.diagram_section = diagram
        root.addWidget(diagram)

        trace = Section()
        self.trace_hint = QLabel()
        self.trace_hint.setWordWrap(True)
        trace.body.addWidget(self.trace_hint)
        self.trace_table = _make_table()
        self.trace_table.setObjectName("graphSettledTable")
        trace.body.addWidget(self.trace_table)
        self.trace_section = trace
        root.addWidget(trace)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render_solution()

    def set_problem(self, model: ShortestPathModel) -> None:
        self._model = model
        self.diagram.set_problem(model)
        self._render_solution()

    def set_solution(self, solution: ShortestPathSolution) -> None:
        self._solution = solution
        self.diagram.set_solution(solution)
        self._render_solution()

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('graph.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("graph.solution.back"))
        self.summary_section.set_title(S.t("graph.solution.summary.section"))
        self.route_section.set_title(S.t("graph.solution.route.section"))
        self.diagram_section.set_title(S.t("graph.solution.diagram.section"))
        self.diagram_hint.setText(S.t("graph.solution.diagram.hint"))
        self.trace_section.set_title(S.t("graph.solution.trace.section"))
        self.trace_hint.setText(S.t("graph.solution.trace.hint"))
        self._render_solution()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.status.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        for label in (self.explanation, self.route, self.distance, self.diagram_hint, self.trace_hint):
            label.setStyleSheet(f"color: {t.text_muted};")
        self.diagram.refresh_theme()

    def _render_solution(self) -> None:
        solution = self._solution
        model = self._model
        if solution is None or model is None:
            self.status.setText(S.t("graph.solution.empty"))
            self.explanation.setText("")
            self.route.setText("-")
            self.distance.setText("-")
            self._set_trace_rows(())
            return
        self.status.setText(
            S.t("graph.solution.status_line", status=S.t(_status_key(solution.status)))
        )
        if solution.status is ShortestPathStatus.PATH_FOUND:
            self.explanation.setText(S.t("graph.solution.explanation.found"))
            labels = [model.vertex_label(identifier) for identifier in solution.path]
            self.route.setText(
                f"<b>{S.t('graph.solution.route.label')}</b> " + " -> ".join(labels)
            )
            self.distance.setText(
                f"<b>{S.t('graph.solution.route.distance.label')}</b> {_format_number(solution.distance)}"
            )
        elif solution.status is ShortestPathStatus.UNREACHABLE:
            self.explanation.setText(S.t("graph.solution.explanation.unreachable"))
            self.route.setText("-")
            self.distance.setText("-")
        else:
            self.explanation.setText(solution.message or S.t("graph.solution.explanation.not_solved"))
            self.route.setText("-")
            self.distance.setText("-")
        self._set_trace_rows(solution.settled_order)

    def _set_trace_rows(self, settled_order: tuple[str, ...]) -> None:
        self.trace_table.setColumnCount(4)
        self.trace_table.setHorizontalHeaderLabels(
            [
                S.t("graph.solution.trace.step"),
                S.t("graph.solution.trace.vertex"),
                S.t("graph.solution.trace.description"),
                S.t("graph.solution.trace.distance"),
            ]
        )
        self.trace_table.setRowCount(len(settled_order))
        distances = self._solution.settled_distances if self._solution is not None else {}
        for row, identifier in enumerate(settled_order, start=1):
            self.trace_table.setItem(row - 1, 0, QTableWidgetItem(str(row)))
            self.trace_table.setItem(row - 1, 1, QTableWidgetItem(identifier))
            description = self._model.vertex_label(identifier) if self._model is not None else "-"
            self.trace_table.setItem(row - 1, 2, QTableWidgetItem(description))
            distance_item = QTableWidgetItem(_format_number(distances.get(identifier)))
            distance_item.setTextAlignment(Qt.AlignCenter)
            self.trace_table.setItem(row - 1, 3, distance_item)


class GraphDiagram(QWidget):
    """Small deterministic graph drawing with the returned path highlighted."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[ShortestPathModel] = None
        self._solution: Optional[ShortestPathSolution] = None
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_problem(self, model: ShortestPathModel) -> None:
        self._model = model
        self.update()

    def set_solution(self, solution: ShortestPathSolution) -> None:
        self._solution = solution
        self.update()

    def refresh_theme(self) -> None:
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = tokens(theme.is_dark())
        painter.fillRect(self.rect(), QColor(t.base))
        if self._model is None:
            painter.setPen(QColor(t.text_muted))
            painter.drawText(self.rect(), Qt.AlignCenter, S.t("graph.solution.diagram.empty"))
            return
        positions = self._positions()
        for index, edge in enumerate(self._model.edges):
            start = positions[edge.source]
            end = positions[edge.target]
            highlighted = self._edge_is_on_path(edge.source, edge.target)
            color = QColor(t.accent if highlighted else t.border_strong)
            painter.setPen(QPen(color, 3 if highlighted else 2))
            line_start, line_end = _shortened_line(start, end, 24)
            painter.drawLine(line_start, line_end)
            if self._model.directed:
                _draw_arrow(painter, line_start, line_end, color)
            midpoint = (line_start + line_end) / 2
            offset = QPointF(0, -10 if index % 2 == 0 else 16)
            weight_text = _format_number(edge.weight)
            metrics = QFontMetrics(painter.font())
            text_rect = metrics.boundingRect(weight_text)
            label_rect = text_rect.adjusted(-5, -2, 5, 2)
            label_rect.moveCenter((midpoint + offset).toPoint())
            painter.fillRect(label_rect, QColor(t.surface_solid))
            painter.setPen(QColor(t.text if highlighted else t.text_muted))
            painter.drawText(label_rect, Qt.AlignCenter, weight_text)

        for vertex in self._model.vertices:
            position = positions[vertex.identifier]
            is_path_vertex = self._solution is not None and vertex.identifier in self._solution.path
            fill = QColor(t.accent if is_path_vertex else t.surface_solid)
            painter.setBrush(fill)
            painter.setPen(QPen(QColor(t.on_accent if is_path_vertex else t.border_strong), 2))
            painter.drawEllipse(position, 24, 24)
            painter.setPen(QColor(t.on_accent if is_path_vertex else t.text))
            painter.drawText(
                int(position.x() - 20),
                int(position.y() - 10),
                40,
                20,
                Qt.AlignCenter,
                vertex.identifier,
            )

    def _positions(self) -> dict[str, QPointF]:
        assert self._model is not None
        count = len(self._model.vertices)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = max(35, min(self.width(), self.height()) / 2 - 58)
        if count == 1:
            return {self._model.vertices[0].identifier: center}
        return {
            vertex.identifier: QPointF(
                center.x() + radius * math.cos(-math.pi / 2 + 2 * math.pi * index / count),
                center.y() + radius * math.sin(-math.pi / 2 + 2 * math.pi * index / count),
            )
            for index, vertex in enumerate(self._model.vertices)
        }

    def _edge_is_on_path(self, source: str, target: str) -> bool:
        if self._solution is None or not self._solution.found() or self._model is None:
            return False
        segments = tuple(zip(self._solution.path, self._solution.path[1:]))
        if self._model.directed:
            return (source, target) in segments
        return any({source, target} == {origin, destination} for origin, destination in segments)


def _draw_arrow(painter: QPainter, start: QPointF, end: QPointF, color: QColor) -> None:
    angle = math.atan2(end.y() - start.y(), end.x() - start.x())
    size = 9.0
    left = QPointF(
        end.x() - size * math.cos(angle - math.pi / 6),
        end.y() - size * math.sin(angle - math.pi / 6),
    )
    right = QPointF(
        end.x() - size * math.cos(angle + math.pi / 6),
        end.y() - size * math.sin(angle + math.pi / 6),
    )
    painter.setBrush(color)
    painter.setPen(Qt.NoPen)
    painter.drawPolygon(QPolygonF([end, left, right]))


def _shortened_line(start: QPointF, end: QPointF, offset: float) -> tuple[QPointF, QPointF]:
    delta = end - start
    length = math.hypot(delta.x(), delta.y())
    if length <= 2 * offset:
        return start, end
    direction = QPointF(delta.x() / length, delta.y() / length)
    return start + direction * offset, end - direction * offset


def _make_table() -> QTableWidget:
    table = QTableWidget()
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setMinimumHeight(150)
    return table


def _status_key(status: ShortestPathStatus) -> str:
    return {
        ShortestPathStatus.PATH_FOUND: "graph.solution.status.path_found",
        ShortestPathStatus.UNREACHABLE: "graph.solution.status.unreachable",
    }.get(status, "graph.solution.status.not_solved")


def _format_number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.10g}"
    except (TypeError, ValueError):
        return str(value)
