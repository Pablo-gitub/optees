from __future__ import annotations

import json
from threading import Event

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QPushButton

from _utils.fakes import FakeSolver
from optees.application.usecases.solve_single_container_packing_usecase import (
    SolveSingleContainerPackingUseCase,
)
from optees.core.string_manager import strings as S
from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D
from optees.domain.entities.packing.item import PackingItem
from optees.domain.entities.packing.resource import ResourceCapacity, ResourceConsumption
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.packing.rotation_policy import RotationPolicy
from optees.presentation.views.packing_view import _OrientationDialog


def _model() -> SingleContainerPackingModel:
    return SingleContainerPackingModel.from_parts(
        PackingContainer.from_parts(
            "container-1",
            "Demo container",
            Dimensions3D(10, 8, 6),
            [ResourceCapacity("weight", 30)],
        ),
        [
            PackingItem.from_parts(
                "machine",
                "Machine part",
                Dimensions3D(6, 4, 3),
                value=12,
                rotation_policy=RotationPolicy.KEEP_UPRIGHT,
                consumptions=[ResourceConsumption("weight", 16)],
            ),
            PackingItem.from_parts(
                "box",
                "Supply box",
                Dimensions3D(4, 4, 2),
                value=6,
                quantity=2,
                consumptions=[ResourceConsumption("weight", 6)],
            ),
        ],
        time_limit=30,
        mip_gap=0.01,
    )


def _solver_response() -> dict[str, object]:
    return {
        "status": "Optimal",
        "objective": 24,
        "placements": [
            {
                "instance_id": "machine#1", "item_id": "machine", "item_name": "Machine part",
                "unit_index": 1, "orientation_code": "LWH", "x": 0, "y": 0, "z": 0,
                "length": 6, "width": 4, "height": 3, "value": 12,
            },
            {
                "instance_id": "box#1", "item_id": "box", "item_name": "Supply box",
                "unit_index": 1, "orientation_code": "LWH", "x": 6, "y": 0, "z": 0,
                "length": 4, "width": 4, "height": 2, "value": 6,
            },
            {
                "instance_id": "box#2", "item_id": "box", "item_name": "Supply box",
                "unit_index": 2, "orientation_code": "LWH", "x": 6, "y": 4, "z": 3,
                "length": 4, "width": 4, "height": 2, "value": 6,
            },
        ],
        "excluded_instance_ids": [],
        "extras": {"backend": "fake", "relative_gap": 0, "wall_time_ms": 8},
    }


def test_home_card_opens_packing_page(window, qtbot) -> None:
    assert window.home_page.card_packing.parentWidget() is window.home_page.cat_lin

    qtbot.mouseClick(window.home_page.card_packing, Qt.LeftButton)

    assert window.stack.currentWidget() is window.packing_page


def test_toolbar_groups_machine_learning_actions(window) -> None:
    assert window.drop_ml.menu() is not None
    assert window.drop_ml.menu().actions() == [
        window.act_regression,
        window.act_classification,
        window.act_forecasting,
    ]


def test_packing_form_solves_asynchronously_and_renders_result(window, qtbot) -> None:
    fake = FakeSolver(_solver_response())
    page = window.packing_page
    page.load_model(_model())
    page.set_solve_usecase(SolveSingleContainerPackingUseCase(fake))
    window.goto("packing")

    with qtbot.waitSignal(page.solve_completed, timeout=3000) as blocker:
        qtbot.mouseClick(page.btn_solve, Qt.LeftButton)

    result = blocker.args[0]
    assert result.requested.objective == 24
    assert result.requested.placements[2].z == 0
    assert fake.last_problem["container"]["dimensions"] == [10.0, 8.0, 6.0]
    assert fake.last_problem["container"]["capacities"] == {"weight": 30.0}
    assert len(fake.last_problem["items"]) == 3
    assert window.stack.currentWidget() is window.packing_solution_page
    assert window.packing_solution_page.placements_table.rowCount() == 3
    assert window.packing_solution_page.plot.visualization_state == "ready"
    assert window.packing_solution_page.plot.legend.count() == 2
    assert "24" in window.packing_solution_page.metrics.text()


def test_solution_plot_legend_visibility_and_table_selection(window, qtbot) -> None:
    page = window.packing_page
    page.load_model(_model())
    page.set_solve_usecase(SolveSingleContainerPackingUseCase(FakeSolver(_solver_response())))

    with qtbot.waitSignal(page.solve_completed, timeout=3000):
        qtbot.mouseClick(page.btn_solve, Qt.LeftButton)

    solution = window.packing_solution_page
    legend_item = solution.plot.legend.item(0)
    hidden_id = legend_item.data(Qt.UserRole)
    legend_item.setCheckState(Qt.Unchecked)
    assert hidden_id not in solution.plot.visible_item_ids

    solution.placements_table.selectRow(1)
    assert solution.plot.highlighted_instance_id == "box#1"

    qtbot.mouseClick(solution.plot.btn_reset_view, Qt.LeftButton)
    assert solution.plot.highlighted_instance_id is None


def test_active_packing_solve_can_be_cancelled_from_the_gui(window, qtbot) -> None:
    class BlockingSolver:
        def __init__(self):
            self.released = Event()
            self.cancelled = False

        def solve(self, problem):
            self.released.wait(timeout=2)
            return _solver_response()

        def cancel(self):
            self.cancelled = True
            self.released.set()
            return True

    solver = BlockingSolver()
    page = window.packing_page
    page.load_model(_model())
    page.set_solve_usecase(SolveSingleContainerPackingUseCase(solver))
    window.goto("packing")

    with qtbot.waitSignal(page.solve_completed, timeout=3000):
        qtbot.mouseClick(page.btn_solve, Qt.LeftButton)
        qtbot.waitUntil(lambda: not page.btn_cancel.isHidden(), timeout=1000)
        qtbot.mouseClick(page.btn_cancel, Qt.LeftButton)

    assert solver.cancelled is True
    assert not page.btn_cancel.isVisible()


def test_packing_json_import_populates_dynamic_resources(window, qtbot, monkeypatch, tmp_path) -> None:
    payload = {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": "all_required",
        "gravity_mode": "none",
        "container": {
            "id": "c1", "name": "Truck", "dimensions": {"length": 12, "width": 3, "height": 4},
            "capacities": [{"name": "weight", "limit": 50}],
        },
        "items": [{
            "id": "crate", "name": "Crate", "dimensions": {"length": 2, "width": 3, "height": 1},
            "value": 7, "quantity": 2, "rotation_policy": "z_only", "allowed_orientations": [],
            "consumptions": [{"name": "weight", "amount": 9}],
        }],
        "solver_options": {"time_limit": 15, "mip_gap": 0.02},
    }
    path = tmp_path / "packing.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.packing_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )

    qtbot.mouseClick(window.packing_page.btn_import, Qt.LeftButton)

    page = window.packing_page
    assert page.container_name.text() == "Truck"
    assert page.resources_table.rowCount() == 1
    assert page.items_table.columnCount() == 11
    assert page.items_table.rowCount() == 1
    assert isinstance(page.items_table.cellWidget(0, 8), QComboBox)
    assert page.items_table.cellWidget(0, 8).currentData() == "z_only"
    assert page.items_table.cellWidget(0, 10).text() == "9"
    assert page.current_model().selection_policy.value == "all_required"
    assert page.current_model().gravity_mode.value == "none"


def test_packing_controls_info_pages_and_translations(window, qtbot) -> None:
    page = window.packing_page
    assert page.findChild(QPushButton, "packingImportJsonButton").text()
    assert page.findChild(QPushButton, "packingSolveButton").text()
    assert page.btn_import_info.property("variant") == "info"
    assert page.btn_import_info.text() == "i"
    assert page.items_table.columnWidth(0) >= 110
    assert page.items_table.columnWidth(2) >= 220
    assert page.items_table.columnWidth(8) >= 230

    qtbot.mouseClick(page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.packing_example_page
    window.goto("packing")
    qtbot.mouseClick(page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.packing_problem_page

    previous = S.current_language()
    try:
        for language in ("en", "it"):
            S.set_language(language)
            assert page.btn_solve.text() == S.t("packing.solve.button")
            assert page.btn_import.text() == S.t("packing.import.button")
            assert "packing." not in page.title.text()
    finally:
        S.set_language(previous)


def test_custom_rotation_field_is_enabled_only_for_custom_policy(window) -> None:
    page = window.packing_page
    page.load_model(_model())
    combo = page.items_table.cellWidget(0, 8)
    custom = page.items_table.cellWidget(0, 9)
    assert isinstance(combo, QComboBox)
    assert isinstance(custom, QPushButton)
    assert not custom.isEnabled()

    combo.setCurrentIndex(combo.findData("custom"))

    assert custom.isEnabled()


def test_custom_orientation_dialog_lists_only_distinct_geometries(qtbot) -> None:
    dialog = _OrientationDialog(Dimensions3D(2, 2, 5), (), None)
    qtbot.addWidget(dialog)

    boxes = dialog.findChildren(QCheckBox)
    assert len(boxes) == 3
    assert all(" x " in box.text() for box in boxes)
    boxes[1].setChecked(True)

    assert len(dialog.selected_codes()) == 1


def test_packing_information_documents_json_and_solver_fields() -> None:
    for language in ("en", "it"):
        previous = S.current_language()
        try:
            S.set_language(language)
            json_info = S.t("packing.info.import.html")
            solver_info = S.t("packing.info.options.html")
            assert "problem_type" in json_info
            assert "allowed_orientations" in json_info
            assert "time_limit" in json_info
            assert "mip_gap" in json_info
            assert "0.01" in solver_info
            assert "[0, 1)" in solver_info
        finally:
            S.set_language(previous)
