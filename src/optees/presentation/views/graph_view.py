from __future__ import annotations

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
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.vertex import GraphVertex
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.presentation.views.lp_view.section import Section
from optees.utility.graph_json_io import shortest_path_model_from_file


class GraphView(QWidget):
    """Formulation screen for the first graph-theory workflow: Dijkstra."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solve_usecase = None
        self._updating_terminals = False

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
        self.btn_import_json.setObjectName("graphImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_json_info = _make_info_button("graphJsonInfoButton")
        self.btn_json_info.clicked.connect(lambda: self._show_info("import"))
        intro_header.addWidget(self.btn_import_json)
        intro_header.addWidget(self.btn_json_info)
        intro.body.addLayout(intro_header)
        intro_actions = QHBoxLayout()
        intro_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("graphExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("graphProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        intro_actions.addWidget(self.btn_example)
        intro_actions.addWidget(self.btn_problem)
        intro.body.addLayout(intro_actions)
        self.intro_section = intro
        root.addWidget(intro)

        terminals = Section()
        terminal_header = QHBoxLayout()
        self.terminals_hint = QLabel()
        self.terminals_hint.setWordWrap(True)
        terminal_header.addWidget(self.terminals_hint, 1)
        self.btn_terminals_info = _make_info_button("graphTerminalsInfoButton")
        self.btn_terminals_info.clicked.connect(lambda: self._show_info("terminals"))
        terminal_header.addWidget(self.btn_terminals_info)
        terminals.body.addLayout(terminal_header)
        terminal_row = QHBoxLayout()
        self.check_directed = QCheckBox()
        self.check_directed.setObjectName("graphDirectedCheckBox")
        self.lbl_source = QLabel()
        self.combo_source = QComboBox()
        self.combo_source.setObjectName("graphSourceCombo")
        self.lbl_destination = QLabel()
        self.combo_destination = QComboBox()
        self.combo_destination.setObjectName("graphDestinationCombo")
        terminal_row.addWidget(self.check_directed)
        terminal_row.addSpacing(16)
        terminal_row.addWidget(self.lbl_source)
        terminal_row.addWidget(self.combo_source)
        terminal_row.addWidget(self.lbl_destination)
        terminal_row.addWidget(self.combo_destination)
        terminal_row.addStretch(1)
        terminals.body.addLayout(terminal_row)
        self.terminals_section = terminals
        root.addWidget(terminals)

        vertices = Section()
        vertices_header = QHBoxLayout()
        self.vertices_hint = QLabel()
        self.vertices_hint.setWordWrap(True)
        vertices_header.addWidget(self.vertices_hint, 1)
        self.btn_vertices_info = _make_info_button("graphVerticesInfoButton")
        self.btn_vertices_info.clicked.connect(lambda: self._show_info("vertices"))
        vertices_header.addWidget(self.btn_vertices_info)
        vertices.body.addLayout(vertices_header)
        self.vertices_table = _make_table("graphVerticesTable", 2)
        self.vertices_table.cellChanged.connect(self._on_vertices_changed)
        vertices.body.addWidget(self.vertices_table)
        vertices_actions = QHBoxLayout()
        vertices_actions.addStretch(1)
        self.btn_add_vertex = QPushButton()
        self.btn_add_vertex.setObjectName("graphAddVertexButton")
        self.btn_add_vertex.clicked.connect(self._add_vertex)
        self.btn_remove_vertex = QPushButton()
        self.btn_remove_vertex.setObjectName("graphRemoveVertexButton")
        self.btn_remove_vertex.clicked.connect(self._remove_selected_vertex)
        vertices_actions.addWidget(self.btn_add_vertex)
        vertices_actions.addWidget(self.btn_remove_vertex)
        vertices.body.addLayout(vertices_actions)
        self.vertices_section = vertices
        root.addWidget(vertices)

        edges = Section()
        edges_header = QHBoxLayout()
        self.edges_hint = QLabel()
        self.edges_hint.setWordWrap(True)
        edges_header.addWidget(self.edges_hint, 1)
        self.btn_edges_info = _make_info_button("graphEdgesInfoButton")
        self.btn_edges_info.clicked.connect(lambda: self._show_info("edges"))
        edges_header.addWidget(self.btn_edges_info)
        edges.body.addLayout(edges_header)
        self.edges_table = _make_table("graphEdgesTable", 4)
        edges_header = self.edges_table.horizontalHeader()
        edges_header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.edges_table.setColumnWidth(0, 38)
        for column in (1, 2, 3):
            edges_header.setSectionResizeMode(column, QHeaderView.Stretch)
        edges.body.addWidget(self.edges_table)
        edges_actions = QHBoxLayout()
        edges_actions.addStretch(1)
        self.btn_add_edge = QPushButton()
        self.btn_add_edge.setObjectName("graphAddEdgeButton")
        self.btn_add_edge.clicked.connect(self._add_edge)
        self.btn_remove_edge = QPushButton()
        self.btn_remove_edge.setObjectName("graphRemoveEdgeButton")
        self.btn_remove_edge.clicked.connect(self._remove_selected_edge)
        edges_actions.addWidget(self.btn_add_edge)
        edges_actions.addWidget(self.btn_remove_edge)
        edges.body.addLayout(edges_actions)
        self.edges_section = edges
        root.addWidget(edges)

        model_section = Section()
        model_header = QHBoxLayout()
        self.model_text = QLabel()
        self.model_text.setWordWrap(True)
        model_header.addWidget(self.model_text, 1)
        self.btn_model_info = _make_info_button("graphModelInfoButton")
        self.btn_model_info.clicked.connect(lambda: self._show_info("model"))
        model_header.addWidget(self.btn_model_info)
        model_section.body.addLayout(model_header)
        self.model_section = model_section
        root.addWidget(model_section)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setObjectName("graphOptimizeButton")
        self.btn_optimize.setProperty("variant", "primary")
        self.btn_optimize.clicked.connect(self._on_solve)
        actions.addWidget(self.btn_optimize)
        root.addLayout(actions)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self._load_default_rows()
        self.refresh_strings()
        self.refresh_theme()

    def set_solve_usecase(self, usecase: object) -> None:
        self._solve_usecase = usecase

    def current_model(self) -> ShortestPathModel:
        return self._build_model()

    def load_model(self, model: ShortestPathModel) -> None:
        self._updating_terminals = True
        try:
            self.check_directed.setChecked(model.directed)
            self.vertices_table.setRowCount(0)
            for vertex in model.vertices:
                self._append_vertex_row(vertex.identifier, vertex.label)
            self.edges_table.setRowCount(0)
            for edge in model.edges:
                self._append_edge_row(edge.source, edge.target, _format_number(edge.weight))
        finally:
            self._updating_terminals = False
        self._refresh_terminal_choices(source=model.source, destination=model.destination)

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('graph.header.title')}</span>"
        )
        self.intro_section.set_title(S.t("graph.header.section"))
        self.intro_text.setText(S.t("graph.header.description"))
        self.btn_import_json.setText(S.t("graph.import.button"))
        self.btn_import_json.setToolTip(S.t("graph.import.tooltip"))
        self.btn_json_info.setToolTip(S.t("graph.import.info_tooltip"))
        self.btn_example.setText(S.t("graph.header.buttons.example"))
        self.btn_problem.setText(S.t("graph.header.buttons.problem"))
        self.terminals_section.set_title(S.t("graph.terminals.section"))
        self.terminals_hint.setText(S.t("graph.terminals.hint"))
        self.check_directed.setText(S.t("graph.terminals.directed"))
        self.lbl_source.setText(S.t("graph.terminals.source"))
        self.lbl_destination.setText(S.t("graph.terminals.destination"))
        self.btn_terminals_info.setToolTip(S.t("graph.terminals.info_tooltip"))
        self.vertices_section.set_title(S.t("graph.vertices.section"))
        self.vertices_hint.setText(S.t("graph.vertices.hint"))
        self.vertices_table.setHorizontalHeaderLabels(
            [S.t("graph.vertices.id"), S.t("graph.vertices.label")]
        )
        self.btn_add_vertex.setText(S.t("graph.vertices.add"))
        self.btn_remove_vertex.setText(S.t("graph.vertices.remove"))
        self.btn_vertices_info.setToolTip(S.t("graph.vertices.info_tooltip"))
        self.edges_section.set_title(S.t("graph.edges.section"))
        self.edges_hint.setText(S.t("graph.edges.hint"))
        self.edges_table.setHorizontalHeaderLabels(
            [
                S.t("graph.edges.select"),
                S.t("graph.edges.from"),
                S.t("graph.edges.to"),
                S.t("graph.edges.weight"),
            ]
        )
        for row in range(self.edges_table.rowCount()):
            weight_editor = self.edges_table.cellWidget(row, 3)
            if isinstance(weight_editor, QLineEdit):
                weight_editor.setPlaceholderText(S.t("graph.edges.weight_placeholder"))
        self.btn_add_edge.setText(S.t("graph.edges.add"))
        self.btn_remove_edge.setText(S.t("graph.edges.remove"))
        self.btn_edges_info.setToolTip(S.t("graph.edges.info_tooltip"))
        self.model_section.set_title(S.t("graph.model.section"))
        self.model_text.setText(S.t("graph.model.text"))
        self.btn_model_info.setToolTip(S.t("graph.model.info_tooltip"))
        self.btn_optimize.setText(S.t("graph.actions.solve"))

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        for label in (self.intro_text, self.terminals_hint, self.vertices_hint, self.edges_hint, self.model_text):
            label.setStyleSheet(f"color: {t.text_muted};")

    def _load_default_rows(self) -> None:
        self._append_vertex_row("A", "")
        self._append_vertex_row("B", "")
        self._refresh_terminal_choices(source="A", destination="B")

    def _add_vertex(self) -> None:
        existing = set(self._vertex_identifiers())
        index = 1
        while f"V{index}" in existing:
            index += 1
        self._append_vertex_row(f"V{index}", "")
        self._refresh_choices_after_vertices_changed()

    def _remove_selected_vertex(self) -> None:
        selected_rows = sorted({item.row() for item in self.vertices_table.selectedItems()}, reverse=True)
        if self.vertices_table.rowCount() - len(selected_rows) < 2:
            return
        for row in selected_rows:
            self.vertices_table.removeRow(row)
        self._refresh_choices_after_vertices_changed()

    def _add_edge(self) -> None:
        vertices = self._vertex_identifiers()
        if len(vertices) < 2:
            return
        self._append_edge_row(vertices[0], vertices[1], "")

    def _remove_selected_edge(self) -> None:
        checked_rows = {
            row
            for row in range(self.edges_table.rowCount())
            if (item := self.edges_table.item(row, 0)) is not None
            and item.checkState() == Qt.Checked
        }
        selected_rows = {item.row() for item in self.edges_table.selectedItems()}
        for row in sorted(checked_rows | selected_rows, reverse=True):
            self.edges_table.removeRow(row)

    def _append_vertex_row(self, identifier: str, label: str) -> None:
        row = self.vertices_table.rowCount()
        self.vertices_table.insertRow(row)
        self.vertices_table.setItem(row, 0, QTableWidgetItem(identifier))
        self.vertices_table.setItem(row, 1, QTableWidgetItem(label))

    def _append_edge_row(self, source: str, target: str, weight: str) -> None:
        row = self.edges_table.rowCount()
        self.edges_table.insertRow(row)
        select_item = QTableWidgetItem()
        select_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        select_item.setCheckState(Qt.Unchecked)
        self.edges_table.setItem(row, 0, select_item)
        self.edges_table.setCellWidget(row, 1, self._edge_vertex_combo(source))
        self.edges_table.setCellWidget(row, 2, self._edge_vertex_combo(target))
        weight_editor = QLineEdit(weight)
        weight_editor.setObjectName("graphEdgeWeight")
        weight_editor.setPlaceholderText(S.t("graph.edges.weight_placeholder"))
        weight_editor.setAlignment(Qt.AlignCenter)
        self.edges_table.setCellWidget(row, 3, weight_editor)

    def _edge_vertex_combo(self, selected: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("graphEdgeVertexCombo")
        for identifier in self._vertex_identifiers():
            combo.addItem(identifier, identifier)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        return combo

    def _on_vertices_changed(self, *_args) -> None:
        if self._updating_terminals:
            return
        self._refresh_choices_after_vertices_changed()

    def _refresh_choices_after_vertices_changed(self) -> None:
        self._refresh_terminal_choices()
        self._refresh_edge_vertex_combos()

    def _refresh_edge_vertex_combos(self) -> None:
        identifiers = self._vertex_identifiers()
        for row in range(self.edges_table.rowCount()):
            for column in (1, 2):
                combo = self.edges_table.cellWidget(row, column)
                if not isinstance(combo, QComboBox):
                    continue
                selected = combo.currentData()
                combo.blockSignals(True)
                combo.clear()
                for identifier in identifiers:
                    combo.addItem(identifier, identifier)
                index = combo.findData(selected)
                combo.setCurrentIndex(index if index >= 0 else 0)
                combo.blockSignals(False)

    def _refresh_terminal_choices(self, *_args, source: Optional[str] = None, destination: Optional[str] = None) -> None:
        if self._updating_terminals:
            return
        identifiers = self._vertex_identifiers()
        source = source or self.combo_source.currentData()
        destination = destination or self.combo_destination.currentData()
        self._updating_terminals = True
        try:
            for combo, selected in ((self.combo_source, source), (self.combo_destination, destination)):
                combo.clear()
                for identifier in identifiers:
                    combo.addItem(identifier, identifier)
                index = combo.findData(selected)
                combo.setCurrentIndex(index if index >= 0 else 0)
            if len(identifiers) > 1 and self.combo_destination.currentData() == self.combo_source.currentData():
                self.combo_destination.setCurrentIndex(1)
        finally:
            self._updating_terminals = False

    def _vertex_identifiers(self) -> list[str]:
        return [
            _table_text(self.vertices_table, row, 0)
            for row in range(self.vertices_table.rowCount())
            if _table_text(self.vertices_table, row, 0)
        ]

    def _build_model(self) -> ShortestPathModel:
        vertices = [
            GraphVertex(
                _table_text(self.vertices_table, row, 0),
                _table_text(self.vertices_table, row, 1),
            )
            for row in range(self.vertices_table.rowCount())
        ]
        edges = [
            GraphEdge(
                _table_text(self.edges_table, row, 1),
                _table_text(self.edges_table, row, 2),
                _table_text(self.edges_table, row, 3),
            )
            for row in range(self.edges_table.rowCount())
        ]
        return ShortestPathModel.from_parts(
            vertices=vertices,
            edges=edges,
            source=str(self.combo_source.currentData() or ""),
            destination=str(self.combo_destination.currentData() or ""),
            directed=self.check_directed.isChecked(),
        )

    def _on_solve(self) -> None:
        if self._solve_usecase is None:
            self._show_error("solver is not configured")
            return
        try:
            model = self._build_model()
            solution = self._solve_usecase.execute(model)
        except Exception as exc:
            self._show_error(str(exc))
            return
        self.solve_completed.emit(solution)

    def _on_import_json(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            S.t("graph.import.dialog_title"),
            "",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            self.load_model(shortest_path_model_from_file(Path(path)))
        except Exception as exc:
            QMessageBox.warning(
                self,
                S.t("graph.import.error_title"),
                S.t("graph.import.error_body", detail=str(exc)),
            )

    def _show_info(self, section: str) -> None:
        dialog = _InfoDialog(
            S.t(f"graph.{section}.info_title"),
            S.t(f"graph.{section}.info_body"),
            S.t(f"graph.{section}.info_html"),
            self,
        )
        dialog.exec()

    def _show_error(self, detail: str) -> None:
        QMessageBox.warning(
            self,
            S.t("graph.validation.title"),
            S.t("graph.validation.body", detail=detail),
        )


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
        browser.setHtml(html)
        root.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


def _make_info_button(object_name: str) -> QPushButton:
    button = QPushButton("i")
    button.setObjectName(object_name)
    button.setProperty("variant", "info")
    button.setFixedSize(24, 24)
    button.setCursor(Qt.PointingHandCursor)
    return button


def _make_table(object_name: str, columns: int) -> QTableWidget:
    table = QTableWidget(0, columns)
    table.setObjectName(object_name)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Stretch)
    table.setMinimumHeight(126)
    return table


def _table_text(table: QTableWidget, row: int, column: int) -> str:
    editor = table.cellWidget(row, column)
    if isinstance(editor, QComboBox):
        return str(editor.currentData() or editor.currentText()).strip()
    if isinstance(editor, QLineEdit):
        return editor.text().strip()
    item = table.item(row, column)
    return item.text().strip() if item is not None else ""


def _format_number(value: float) -> str:
    return f"{value:.10g}"
