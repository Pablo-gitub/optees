import pytest

pytest.importorskip("PySide6")

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QPushButton, QWidget

from _utils.fakes import FakeSolver
from optees.application.usecases.solve_bounded_knapsack_usecase import (
    SolveBoundedKnapsackUseCase,
)
from optees.application.usecases.solve_fractional_knapsack_usecase import (
    SolveFractionalKnapsackUseCase,
)
from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.application.usecases.solve_multi_dimensional_knapsack_usecase import (
    SolveMultiDimensionalKnapsackUseCase,
)
from optees.application.usecases.solve_unbounded_knapsack_usecase import (
    SolveUnboundedKnapsackUseCase,
)
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.value_objects.knapsack.variant import KnapsackVariant
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


def _import_knapsack_json(window, qtbot, monkeypatch, tmp_path, data):
    window.goto("knapsack")
    path = tmp_path / "knapsack.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.knapsack_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    qtbot.mouseClick(window.knap_page.btn_import_json, Qt.LeftButton)


def _fill_small_multi_dimensional_form(window, qtbot):
    multi = window.knap_page.findChild(QPushButton, "knapsackVariant_multi_dimensional")
    assert multi is not None
    qtbot.mouseClick(multi, Qt.LeftButton)

    resource_rows = window.knap_page.resources_sec.rows()
    resource_rows[0].edit_name.setText("weight")
    resource_rows[0].edit_capacity.setText("13")
    resource_rows[1].edit_name.setText("volume")
    resource_rows[1].edit_capacity.setText("6")
    window.knap_page._on_resources_changed()

    item_rows = window.knap_page.multi_items_sec.rows()
    data = [
        ("A", "8", ("4", "2")),
        ("B", "9", ("5", "2")),
    ]
    for row, (name, value, usages) in zip(item_rows, data):
        row.edit_name.setText(name)
        row.edit_value.setText(value)
        for edit, usage in zip(row.usage_edits(), usages):
            edit.setText(usage)


def test_knapsack_flow_solves_and_navigates_to_solution(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 7.0,
            "selected_indices": [0, 1],
            "x": {"A": 1.0, "B": 1.0, "C": 0.0},
            "extras": {
                "method": "dynamic_programming",
                "item_count": 3,
                "capacity": 5,
            },
        }
    )
    window.knap_page.set_solve_usecase(SolveKnapsackUseCase(fake))

    window.knapsack_controller.load_model(
        Knapsack01Model.from_parts(
            (
                KnapsackItem("A", 3, 2),
                KnapsackItem("B", 4, 3),
                KnapsackItem("C", 5, 4),
            ),
            capacity=5,
        )
    )

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(7.0)
    assert solution.selected_indices == (0, 1)
    assert solution.total_weight == 5
    assert solution.remaining_capacity == 0

    assert fake.last_problem == {
        "values": [3.0, 4.0, 5.0],
        "weights": [2, 3, 4],
        "capacity": 5,
        "var_names": ["A", "B", "C"],
    }
    assert window.stack.currentWidget() is window.knapsack_solution_page
    assert window.knapsack_solution_page.solution_table.model().rowCount() == 3
    assert window.knapsack_solution_page.findChild(QWidget, "knapsackCapacityChart") is not None
    assert window.knapsack_solution_page.findChild(QWidget, "knapsackItemBars") is not None


def test_knapsack_initial_form_uses_labels_and_empty_placeholders(window):
    window.goto("knapsack")

    rows = window.knap_page.items_sec.rows()

    assert len(rows) == 2
    assert window.knap_page.edit_capacity.text() == ""
    assert rows[0].lbl_index.text() == "X1"
    assert rows[1].lbl_index.text() == "X2"
    assert rows[0].edit_name.text() == ""
    assert rows[0].edit_value.text() == ""
    assert rows[0].edit_weight.text() == ""
    assert rows[0].edit_name.placeholderText()
    assert rows[0].edit_value.placeholderText()
    assert rows[0].edit_weight.placeholderText()


def test_bounded_knapsack_flow_solves_quantities_and_navigates(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 22.0,
            "quantities": [2, 1],
            "x": {"A": 2, "B": 1},
            "extras": {
                "method": "bounded_dynamic_programming",
                "item_count": 2,
                "capacity": 7,
            },
        }
    )
    window.knap_page.set_bounded_solve_usecase(SolveBoundedKnapsackUseCase(fake))

    window.knapsack_controller.load_model(
        Knapsack01Model.from_parts(
            (
                KnapsackItem("A", 6, 2),
                KnapsackItem("B", 10, 3),
            ),
            capacity=7,
        )
    )
    bounded = window.knap_page.findChild(QPushButton, "knapsackVariant_bounded")
    assert bounded is not None
    qtbot.mouseClick(bounded, Qt.LeftButton)

    rows = window.knap_page.items_sec.rows()
    rows[0].edit_max_quantity.setText("3")
    rows[1].edit_max_quantity.setText("2")

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.objective == pytest.approx(22.0)
    assert solution.quantities == (2, 1)
    assert solution.total_weight == 7
    assert fake.last_problem == {
        "values": [6.0, 10.0],
        "weights": [2, 3],
        "max_quantities": [3, 2],
        "capacity": 7,
        "var_names": ["A", "B"],
    }
    assert window.stack.currentWidget() is window.knapsack_solution_page
    table_model = window.knapsack_solution_page.solution_table.model()
    assert table_model.rowCount() == 2
    assert table_model.columnCount() == 7
    assert table_model.item(0, 1).text() == "2"


def test_unbounded_knapsack_flow_solves_quantities_and_navigates(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 13.0,
            "quantities": [1, 2],
            "x": {"A": 1, "B": 2},
            "extras": {
                "method": "unbounded_dynamic_programming",
                "item_count": 2,
                "capacity": 7,
            },
        }
    )
    window.knap_page.set_unbounded_solve_usecase(SolveUnboundedKnapsackUseCase(fake))

    window.knapsack_controller.load_model(
        Knapsack01Model.from_parts(
            (
                KnapsackItem("A", 3, 1),
                KnapsackItem("B", 5, 3),
            ),
            capacity=7,
        )
    )
    unbounded = window.knap_page.findChild(QPushButton, "knapsackVariant_unbounded")
    assert unbounded is not None
    qtbot.mouseClick(unbounded, Qt.LeftButton)

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.objective == pytest.approx(13.0)
    assert solution.quantities == (1, 2)
    assert solution.total_weight == 7
    assert fake.last_problem == {
        "values": [3.0, 5.0],
        "weights": [1, 3],
        "capacity": 7,
        "var_names": ["A", "B"],
    }
    assert window.stack.currentWidget() is window.knapsack_solution_page
    table_model = window.knapsack_solution_page.solution_table.model()
    assert table_model.rowCount() == 2
    assert table_model.columnCount() == 6
    assert table_model.item(1, 1).text() == "2"


def test_fractional_knapsack_flow_solves_fractions_and_navigates(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 240.0,
            "fractions": [1.0, 1.0, 2.0 / 3.0],
            "x": {"A": 1.0, "B": 1.0, "C": 2.0 / 3.0},
            "extras": {
                "method": "fractional_greedy_density",
                "item_count": 3,
                "capacity": 50.5,
            },
        }
    )
    window.knap_page.set_fractional_solve_usecase(SolveFractionalKnapsackUseCase(fake))

    window.knapsack_controller.load_model(
        Knapsack01Model.from_parts(
            (
                KnapsackItem("A", 60, 10),
                KnapsackItem("B", 100, 20),
                KnapsackItem("C", 120, 30),
            ),
            capacity=50,
        )
    )
    fractional = window.knap_page.findChild(QPushButton, "knapsackVariant_fractional")
    assert fractional is not None
    qtbot.mouseClick(fractional, Qt.LeftButton)

    window.knap_page.edit_capacity.setText("50.5")
    rows = window.knap_page.items_sec.rows()
    rows[0].edit_weight.setText("10.0")
    rows[1].edit_weight.setText("20.0")
    rows[2].edit_weight.setText("30.0")

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.objective == pytest.approx(240.0)
    assert solution.fractions == pytest.approx((1.0, 1.0, 2.0 / 3.0))
    assert solution.selected_indices == (0, 1, 2)
    assert solution.total_weight == pytest.approx(50.0)
    assert solution.remaining_capacity == pytest.approx(0.5)
    assert fake.last_problem == {
        "values": [60.0, 100.0, 120.0],
        "weights": [10.0, 20.0, 30.0],
        "capacity": 50.5,
        "var_names": ["A", "B", "C"],
    }
    assert window.stack.currentWidget() is window.knapsack_solution_page
    table_model = window.knapsack_solution_page.solution_table.model()
    assert table_model.rowCount() == 3
    assert table_model.columnCount() == 6
    assert table_model.item(2, 1).text() == "0.666667"


def test_multi_dimensional_knapsack_flow_solves_selection_and_navigates(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 22.0,
            "selected_indices": [0, 2],
            "x": {"A": 1.0, "B": 0.0, "C": 1.0, "D": 0.0},
            "extras": {
                "method": "multidimensional_branch_and_bound",
                "item_count": 4,
                "resource_count": 2,
            },
        }
    )
    window.knap_page.set_multi_dimensional_solve_usecase(
        SolveMultiDimensionalKnapsackUseCase(fake)
    )

    multi = window.knap_page.findChild(QPushButton, "knapsackVariant_multi_dimensional")
    assert multi is not None
    qtbot.mouseClick(multi, Qt.LeftButton)

    resource_rows = window.knap_page.resources_sec.rows()
    resource_rows[0].edit_name.setText("weight")
    resource_rows[0].edit_capacity.setText("10")
    resource_rows[1].edit_name.setText("volume")
    resource_rows[1].edit_capacity.setText("6")
    window.knap_page._on_resources_changed()

    window.knap_page.multi_items_sec.add_item()
    window.knap_page.multi_items_sec.add_item()
    item_rows = window.knap_page.multi_items_sec.rows()
    data = [
        ("A", "8", ("4", "1.5")),
        ("B", "9", ("5", "2")),
        ("C", "14", ("6", "4.5")),
        ("D", "7", ("3", "2")),
    ]
    for row, (name, value, usages) in zip(item_rows, data):
        row.edit_name.setText(name)
        row.edit_value.setText(value)
        for edit, usage in zip(row.usage_edits(), usages):
            edit.setText(usage)

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.objective == pytest.approx(22.0)
    assert solution.selected_indices == (0, 2)
    assert solution.resource_usage_totals == pytest.approx((10.0, 6.0))
    assert solution.remaining_capacities == pytest.approx((0.0, 0.0))
    assert fake.last_problem == {
        "values": [8.0, 9.0, 14.0, 7.0],
        "usage_matrix": [
            [4.0, 1.5],
            [5.0, 2.0],
            [6.0, 4.5],
            [3.0, 2.0],
        ],
        "capacities": [10.0, 6.0],
        "var_names": ["A", "B", "C", "D"],
        "resource_names": ["weight", "volume"],
    }
    assert window.stack.currentWidget() is window.knapsack_solution_page
    table_model = window.knapsack_solution_page.solution_table.model()
    assert table_model.rowCount() == 4
    assert table_model.columnCount() == 6
    assert table_model.item(0, 3).text() == "4"
    assert table_model.item(2, 4).text() == "4.5"


def test_multi_dimensional_bounded_domain_maps_to_milp_quantities(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 25.0,
            "x": {"X1": 2.0, "X2": 1.0},
            "extras": {"method": "milp_test"},
        }
    )
    window.knap_page.set_multi_dimensional_milp_solve_usecase(SolveMILPUseCase(fake))
    _fill_small_multi_dimensional_form(window, qtbot)

    bounded = window.knap_page.findChild(QPushButton, "knapsackMultiDomain_bounded")
    assert bounded is not None
    qtbot.mouseClick(bounded, Qt.LeftButton)
    rows = window.knap_page.multi_items_sec.rows()
    rows[0].edit_quantity_limit.setText("3")
    rows[1].edit_quantity_limit.setText("2")

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.objective == pytest.approx(25.0)
    assert solution.quantities == pytest.approx((2.0, 1.0))
    assert solution.resource_usage_totals == pytest.approx((13.0, 6.0))
    assert fake.last_problem["sense"] == "max"
    assert fake.last_problem["c"] == [8.0, 9.0]
    assert fake.last_problem["A_ub"] == [[4.0, 5.0], [2.0, 2.0]]
    assert fake.last_problem["b_ub"] == [13.0, 6.0]
    assert fake.last_problem["bounds"] == [(0.0, 3.0), (0.0, 2.0)]
    assert fake.last_problem["integrality"] == ["I", "I"]
    assert fake.last_problem["var_names"] == ["X1", "X2"]
    table_model = window.knapsack_solution_page.solution_table.model()
    assert table_model.columnCount() == 7
    assert table_model.item(0, 1).text() == "2"


def test_multi_dimensional_fractional_domain_maps_to_continuous_lp(window, qtbot):
    fake = FakeSolver(
        {
            "status": "Optimal",
            "objective": 12.5,
            "x": {"X1": 0.5, "X2": 1.0},
            "extras": {"method": "lp_test"},
        }
    )
    window.knap_page.set_multi_dimensional_milp_solve_usecase(SolveMILPUseCase(fake))
    _fill_small_multi_dimensional_form(window, qtbot)

    fractional = window.knap_page.findChild(QPushButton, "knapsackMultiDomain_fractional")
    assert fractional is not None
    qtbot.mouseClick(fractional, Qt.LeftButton)
    rows = window.knap_page.multi_items_sec.rows()
    rows[0].edit_quantity_limit.setText("1")
    rows[1].edit_quantity_limit.setText("inf")

    with qtbot.waitSignal(window.knap_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.knap_page.btn_optimize, Qt.LeftButton)

    solution = blocker.args[0]

    assert solution.objective == pytest.approx(12.5)
    assert solution.quantities == pytest.approx((0.5, 1.0))
    assert solution.resource_usage_totals == pytest.approx((7.0, 3.0))
    assert fake.last_problem["bounds"] == [(0.0, 1.0), (0.0, None)]
    assert fake.last_problem["integrality"] == [None, None]


def test_knapsack_imports_zero_one_json_from_gui(window, qtbot, monkeypatch, tmp_path):
    _import_knapsack_json(
        window,
        qtbot,
        monkeypatch,
        tmp_path,
        {
            "version": "1",
            "variant": "zero_one",
            "capacity": 5,
            "items": [
                {"name": "A", "value": 3, "weight": 2},
                {"name": "B", "value": 4, "weight": 3},
            ],
        },
    )

    rows = window.knap_page.items_sec.rows()
    assert window.knap_page.current_variant() is KnapsackVariant.ZERO_ONE
    assert window.knap_page.edit_capacity.text() == "5"
    assert rows[0].edit_name.text() == "A"
    assert rows[0].edit_value.text() == "3"
    assert rows[0].edit_weight.text() == "2"
    assert rows[1].edit_name.text() == "B"
    assert rows[1].edit_weight.text() == "3"


def test_knapsack_imports_bounded_json_from_gui(window, qtbot, monkeypatch, tmp_path):
    _import_knapsack_json(
        window,
        qtbot,
        monkeypatch,
        tmp_path,
        {
            "version": "1",
            "variant": "bounded",
            "capacity": 7,
            "items": [
                {"name": "A", "value": 6, "weight": 2, "max_quantity": 3},
                {"name": "B", "value": 10, "weight": 3, "max_quantity": 2},
            ],
        },
    )

    rows = window.knap_page.items_sec.rows()
    assert window.knap_page.current_variant() is KnapsackVariant.BOUNDED
    assert window.knap_page.edit_capacity.text() == "7"
    assert rows[0].edit_name.text() == "A"
    assert rows[0].edit_max_quantity.isHidden() is False
    assert rows[0].edit_max_quantity.text() == "3"
    assert rows[1].edit_max_quantity.text() == "2"


def test_knapsack_imports_unbounded_json_from_gui(window, qtbot, monkeypatch, tmp_path):
    _import_knapsack_json(
        window,
        qtbot,
        monkeypatch,
        tmp_path,
        {
            "version": "1",
            "variant": "unbounded",
            "capacity": 8,
            "items": [
                {"name": "A", "value": 3, "weight": 1},
                {"name": "B", "value": 5, "weight": 3},
            ],
        },
    )

    rows = window.knap_page.items_sec.rows()
    assert window.knap_page.current_variant() is KnapsackVariant.UNBOUNDED
    assert window.knap_page.edit_capacity.text() == "8"
    assert rows[0].edit_name.text() == "A"
    assert rows[0].edit_weight.text() == "1"
    assert rows[0].edit_max_quantity.isVisible() is False


def test_knapsack_imports_fractional_json_from_gui(window, qtbot, monkeypatch, tmp_path):
    _import_knapsack_json(
        window,
        qtbot,
        monkeypatch,
        tmp_path,
        {
            "version": "1",
            "variant": "fractional",
            "capacity": 50.5,
            "items": [
                {"name": "A", "value": 60, "weight": 10.5},
                {"name": "B", "value": 100, "weight": 20},
            ],
        },
    )

    rows = window.knap_page.items_sec.rows()
    assert window.knap_page.current_variant() is KnapsackVariant.FRACTIONAL
    assert window.knap_page.edit_capacity.text() == "50.5"
    assert rows[0].edit_name.text() == "A"
    assert rows[0].edit_weight.text() == "10.5"
    assert rows[0].edit_max_quantity.isVisible() is False


def test_knapsack_imports_multi_dimensional_json_from_gui(
    window,
    qtbot,
    monkeypatch,
    tmp_path,
):
    _import_knapsack_json(
        window,
        qtbot,
        monkeypatch,
        tmp_path,
        {
            "version": "1",
            "variant": "multi_dimensional",
            "domain": "fractional",
            "resources": [
                {"name": "weight", "capacity": 10},
                {"name": "volume", "capacity": 6},
            ],
            "items": [
                {"name": "A", "value": 8, "usage": [4, 1.5], "max_quantity": 1},
                {"name": "B", "value": 9, "usage": [5, 2], "max_quantity": "inf"},
            ],
        },
    )

    resource_rows = window.knap_page.resources_sec.rows()
    item_rows = window.knap_page.multi_items_sec.rows()
    fractional_domain = window.knap_page.findChild(
        QPushButton,
        "knapsackMultiDomain_fractional",
    )
    assert window.knap_page.current_variant() is KnapsackVariant.MULTI_DIMENSIONAL
    assert fractional_domain is not None
    assert fractional_domain.isChecked() is True
    assert resource_rows[0].edit_name.text() == "weight"
    assert resource_rows[0].edit_capacity.text() == "10"
    assert resource_rows[1].edit_name.text() == "volume"
    assert resource_rows[1].edit_capacity.text() == "6"
    assert item_rows[0].edit_name.text() == "A"
    assert item_rows[0].edit_quantity_limit.isHidden() is False
    assert item_rows[0].edit_quantity_limit.text() == "1"
    assert [edit.text() for edit in item_rows[0].usage_edits()] == ["4", "1.5"]
    assert item_rows[1].edit_quantity_limit.text() == "inf"
    assert [edit.text() for edit in item_rows[1].usage_edits()] == ["5", "2"]


def test_knapsack_variant_switch_enables_implemented_variants(window, qtbot):
    window.goto("knapsack")
    bounded = window.knap_page.findChild(QPushButton, "knapsackVariant_bounded")
    unbounded = window.knap_page.findChild(QPushButton, "knapsackVariant_unbounded")
    fractional = window.knap_page.findChild(QPushButton, "knapsackVariant_fractional")
    multi = window.knap_page.findChild(QPushButton, "knapsackVariant_multi_dimensional")
    zero_one = window.knap_page.findChild(QPushButton, "knapsackVariant_zero_one")

    assert bounded is not None
    assert unbounded is not None
    assert fractional is not None
    assert multi is not None
    assert zero_one is not None
    assert window.knap_page.current_variant() is KnapsackVariant.ZERO_ONE
    assert window.knap_page.btn_optimize.isEnabled() is True
    assert window.knap_page.btn_import_json.isEnabled() is True
    assert window.knap_page.findChild(QPushButton, "knapsackImportBurkardtButton") is None

    qtbot.mouseClick(bounded, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.BOUNDED
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_json.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True
    assert window.knap_page.findChild(QLineEdit, "knapsackItemMaxQuantity") is not None

    qtbot.mouseClick(unbounded, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.UNBOUNDED
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_json.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True

    qtbot.mouseClick(fractional, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.FRACTIONAL
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_json.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True
    assert window.knap_page.findChild(QLineEdit, "knapsackItemMaxQuantity").isVisible() is False

    qtbot.mouseClick(multi, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.MULTI_DIMENSIONAL
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is False
    assert window.knap_page.items_sec.isVisible() is False
    assert window.knap_page.resources_sec.isVisible() is True
    assert window.knap_page.multi_items_sec.isVisible() is True
    assert window.knap_page.multi_domain_sec.isVisible() is True
    assert window.knap_page.btn_import_json.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True
    assert window.knap_page.findChild(QLineEdit, "knapsackMultiItemQuantityLimit").isVisible() is False

    multi_bounded = window.knap_page.findChild(QPushButton, "knapsackMultiDomain_bounded")
    assert multi_bounded is not None
    qtbot.mouseClick(multi_bounded, Qt.LeftButton)

    assert window.knap_page.findChild(QLineEdit, "knapsackMultiItemQuantityLimit").isVisible() is True

    qtbot.mouseClick(zero_one, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.ZERO_ONE
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_json.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True
