import pytest

pytest.importorskip("PySide6")

from pathlib import Path

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
from optees.application.usecases.solve_unbounded_knapsack_usecase import (
    SolveUnboundedKnapsackUseCase,
)
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


def test_knapsack_variant_switch_enables_implemented_variants(window, qtbot):
    window.goto("knapsack")
    bounded = window.knap_page.findChild(QPushButton, "knapsackVariant_bounded")
    unbounded = window.knap_page.findChild(QPushButton, "knapsackVariant_unbounded")
    fractional = window.knap_page.findChild(QPushButton, "knapsackVariant_fractional")
    zero_one = window.knap_page.findChild(QPushButton, "knapsackVariant_zero_one")

    assert bounded is not None
    assert unbounded is not None
    assert fractional is not None
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
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_burkardt.isEnabled() is False
    assert window.knap_page.btn_optimize.isEnabled() is True

    qtbot.mouseClick(fractional, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.FRACTIONAL
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_burkardt.isEnabled() is False
    assert window.knap_page.btn_optimize.isEnabled() is True
    assert window.knap_page.findChild(QLineEdit, "knapsackItemMaxQuantity").isVisible() is False

    qtbot.mouseClick(zero_one, Qt.LeftButton)

    assert window.knap_page.current_variant() is KnapsackVariant.ZERO_ONE
    assert window.knap_page.variant_placeholder_sec.isVisible() is False
    assert window.knap_page.capacity_sec.isVisible() is True
    assert window.knap_page.items_sec.isVisible() is True
    assert window.knap_page.btn_import_burkardt.isEnabled() is True
    assert window.knap_page.btn_optimize.isEnabled() is True
