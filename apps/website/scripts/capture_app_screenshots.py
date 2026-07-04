from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "apps" / "website" / "public" / "screenshots"
MPL_CONFIG_DIR = Path(os.getenv("TMPDIR") or "/tmp") / "optees-matplotlib"
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OPTEES_DISABLE_UPDATE_CHECK", "1")
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from optees.core.string_manager import strings as S
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.lp.variable import Variable
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.value_objects.knapsack.variant import KnapsackVariant
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.presentation.main_window import MainWindow


def _install_dark_palette(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, QColor(245, 245, 245))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ToolTipBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipText, QColor(30, 30, 30))
    palette.setColor(QPalette.Text, QColor(245, 245, 245))
    palette.setColor(QPalette.Button, QColor(70, 70, 70))
    palette.setColor(QPalette.ButtonText, QColor(245, 245, 245))
    palette.setColor(QPalette.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.Highlight, QColor(20, 125, 245))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def _capture(window: MainWindow, name: str, page: str) -> None:
    window.goto(page)
    QTest.qWait(300)
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    path = OUT_DIR / name
    if not window.grab().save(str(path)):
        raise RuntimeError(f"Could not save screenshot: {path}")
    print(path.relative_to(ROOT))


def _multiple_optima_lp_model() -> LPModel:
    return LPModel.from_parts(
        [
            Variable("X1", "desktop licenses", Bounds(0.0, None)),
            Variable("X2", "cloud seats", Bounds(0.0, None)),
        ],
        Objective(ObjectiveSense.MAX, (1.0, 1.0), 0.0),
        [
            Constraint((1.0, 1.0), Relation.LE, 10.0),
            Constraint((1.0, 0.0), Relation.LE, 8.0),
            Constraint((0.0, 1.0), Relation.LE, 8.0),
        ],
    )


def _knapsack_model() -> Knapsack01Model:
    return Knapsack01Model.from_parts(
        [
            KnapsackItem("Laptop", 10, 4),
            KnapsackItem("Camera", 7, 3),
            KnapsackItem("Notebook", 4, 2),
            KnapsackItem("Jacket", 6, 5),
            KnapsackItem("Charger", 5, 1),
        ],
        capacity=7,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    _install_dark_palette(app)
    S.set_language("en", emit=False)

    window = MainWindow()
    window.resize(1440, 940)
    window.show()
    QTest.qWait(350)
    app.processEvents()

    _capture(window, "optees-home.png", "home")

    lp_model = _multiple_optima_lp_model()
    lp_solution = window.solve_lp_uc.execute(lp_model)
    window.lp_solution_page.set_problem(lp_model)
    window.lp_solution_page.set_solution(lp_solution)
    _capture(window, "optees-lp-solution.png", "lp_solution")

    knapsack_model = _knapsack_model()
    window.knap_page._set_variant(KnapsackVariant.ZERO_ONE)
    window.knapsack_controller.load_model(knapsack_model)
    QTest.qWait(250)
    _capture(window, "optees-knapsack.png", "knapsack")

    knapsack_solution = window.solve_knapsack_uc.execute(knapsack_model)
    window.knapsack_solution_page.set_problem(knapsack_model)
    window.knapsack_solution_page.set_solution(knapsack_solution)
    _capture(window, "optees-knapsack-solution.png", "knapsack_solution")

    window.close()


if __name__ == "__main__":
    main()
