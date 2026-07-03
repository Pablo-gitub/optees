import pytest

pytest.importorskip("PySide6")

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QPushButton, QWidget

from _utils.fakes import FakeSolver
from optees.application.usecases.solve_bounded_knapsack_usecase import (
    SolveBoundedKnapsackUseCase,
)
from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.value_objects.knapsack.variant import KnapsackVariant
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.utility.data_adapters.knapsack_burkardt_adapter import load_knapsack_burkardt


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


def test_knapsack_imports_burkardt_instance(window, qtbot, monkeypatch):
    path = Path("tests/data/knapsack/p01/p01_c.txt").resolve()
    expected = load_knapsack_burkardt(str(path.parent), "p01")

    monkeypatch.setattr(
        "optees.presentation.views.knapsack_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )

    qtbot.mouseClick(window.knap_page.btn_import_burkardt, Qt.LeftButton)

    model = window.knapsack_controller.model()
    assert model.capacity == expected["capacity"]
    assert len(model.items) == len(expected["values"])
    assert model.items[0].name == "p01_item_1"
    assert model.items[0].value == pytest.approx(expected["values"][0])
    assert model.items[0].weight == expected["weights"][0]
    assert len(window.knap_page.items_sec.rows()) == len(expected["values"])


def test_knapsack_variant_switch_enables_bounded_and_keeps_placeholders_for_future_variants(window, qtbot):
    window.goto("knapsack")
    bounded = window.knap_page.findChild(QPushButton, "knapsackVariant_bounded")
    unbounded = window.knap_page.findChild(QPushButton, "knapsackVariant_unbounded")
    zero_one = window.knap_page.findChild(QPushButton, "knapsackVariant_zero_one")

    assert bounded is not None
    assert unbounded is not None
    assert zero_one is not None
    assert window.knap_page.current_variant() is KnapsackVariant.ZERO_ONE
    assert window.knap_page.btn_optimize.isEnabled() is True

    qtbot.mouseClick(bounded, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.BOUNDED
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_burkardt.isEnabled() is False
    assert window.knap_page.btn_optimize.isEnabled() is True
    assert window.knap_page.findChild(QLineEdit, "knapsackItemMaxQuantity") is not None

    qtbot.mouseClick(unbounded, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.UNBOUNDED
    assert window.knap_page.variant_placeholder_sec.isVisible() is True
    assert window.knap_page.capacity_sec.isVisible() is False
    assert window.knap_page.items_sec.isVisible() is False
    assert window.knap_page.btn_import_burkardt.isEnabled() is False
    assert window.knap_page.btn_optimize.isEnabled() is False

    qtbot.mouseClick(zero_one, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.ZERO_ONE
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_burkardt.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True
