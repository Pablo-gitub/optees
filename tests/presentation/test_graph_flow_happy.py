from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton

from optees.core.string_manager import strings as S
from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.solution import ShortestPathSolution
from optees.domain.entities.graph.vertex import GraphVertex
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.domain.value_objects.graph.shortest_path_status import ShortestPathStatus


def _delivery_model() -> ShortestPathModel:
    return ShortestPathModel.from_parts(
        vertices=[
            GraphVertex("A", "Depot"),
            GraphVertex("B", "Crossroad"),
            GraphVertex("C", "Warehouse"),
            GraphVertex("D", "Customer"),
        ],
        edges=[
            GraphEdge("A", "B", 4),
            GraphEdge("A", "C", 1),
            GraphEdge("C", "B", 2),
            GraphEdge("B", "D", 1),
            GraphEdge("C", "D", 8),
        ],
        source="A",
        destination="D",
        directed=True,
    )


def test_home_card_opens_graph_page(window, qtbot) -> None:
    qtbot.mouseClick(window.home_page.card_graph, Qt.LeftButton)

    assert window.stack.currentWidget() is window.graph_page


def test_graph_form_solves_and_shows_highlighted_route(window, qtbot) -> None:
    window.goto("graph")
    window.graph_page.load_model(_delivery_model())

    with qtbot.waitSignal(window.graph_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.graph_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]
    assert solution.status is ShortestPathStatus.PATH_FOUND
    assert solution.path == ("A", "C", "B", "D")
    assert window.stack.currentWidget() is window.graph_solution_page
    assert "Depot" in window.graph_solution_page.route.text()
    assert "Customer" in window.graph_solution_page.route.text()
    assert window.graph_solution_page.trace_table.rowCount() == 4
    assert window.graph_solution_page.diagram._solution is solution


def test_graph_json_import_populates_form(window, qtbot, monkeypatch, tmp_path) -> None:
    payload = {
        "version": "1",
        "problem_type": "shortest_path",
        "directed": False,
        "vertices": [{"id": "A", "label": "Alpha"}, {"id": "B", "label": "Beta"}],
        "edges": [{"from": "A", "to": "B", "weight": 2}],
        "source": "A",
        "destination": "B",
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.graph_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    window.goto("graph")

    qtbot.mouseClick(window.graph_page.btn_import_json, Qt.LeftButton)

    assert not window.graph_page.check_directed.isChecked()
    assert window.graph_page.vertices_table.rowCount() == 2
    assert window.graph_page.vertices_table.item(0, 1).text() == "Alpha"
    assert window.graph_page.edges_table.item(0, 0).checkState() == Qt.Unchecked
    source_editor = window.graph_page.edges_table.cellWidget(0, 1)
    target_editor = window.graph_page.edges_table.cellWidget(0, 2)
    weight_editor = window.graph_page.edges_table.cellWidget(0, 3)
    assert isinstance(source_editor, QComboBox) and source_editor.currentData() == "A"
    assert isinstance(target_editor, QComboBox) and target_editor.currentData() == "B"
    assert isinstance(weight_editor, QLineEdit) and weight_editor.text() == "2"
    assert window.graph_page.combo_source.currentData() == "A"
    assert window.graph_page.combo_destination.currentData() == "B"


def test_graph_edge_checkbox_selects_row_for_removal(window, qtbot) -> None:
    window.goto("graph")
    window.graph_page.load_model(_delivery_model())
    window.graph_page.edges_table.item(0, 0).setCheckState(Qt.Checked)

    qtbot.mouseClick(window.graph_page.btn_remove_edge, Qt.LeftButton)

    assert window.graph_page.edges_table.rowCount() == 4


def test_graph_solution_explains_unreachable_destination(window) -> None:
    model = ShortestPathModel.from_parts(
        vertices=[GraphVertex("A"), GraphVertex("B")],
        edges=[],
        source="A",
        destination="B",
    )
    solution = ShortestPathSolution.from_solver_result(
        status="Unreachable",
        distance=None,
        path=(),
        extras={"settled_order": ["A"], "settled_distances": {"A": 0}},
    )

    window.graph_solution_page.set_problem(model)
    window.graph_solution_page.set_solution(solution)

    assert S.t("graph.solution.status.unreachable") in window.graph_solution_page.status.text()
    assert window.graph_solution_page.trace_table.rowCount() == 1
    assert window.graph_solution_page.route.text() == "-"


def test_graph_view_uses_localized_controls(window) -> None:
    window.goto("graph")

    assert window.graph_page.findChild(QPushButton, "graphImportJsonButton").text()
    assert window.graph_page.findChild(QPushButton, "graphOptimizeButton").text()
    assert window.graph_page.btn_json_info.property("variant") == "info"
