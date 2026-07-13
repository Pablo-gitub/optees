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
from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.vertex import GraphVertex
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.entities.nlp.objective import NLPObjective
from optees.domain.entities.nlp.variable import NLPVariable
from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.lp.variable import Variable
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.domain.models.nlp.nlp_model import NLPModel, NLPOptions
from optees.domain.models.regression.regression_model import RegressionModel, RegressionOptions
from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
    ClassificationOptions,
)
from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.value_objects.knapsack.variant import KnapsackVariant
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod
from optees.presentation.main_window import MainWindow


def _install_dark_palette(app: QApplication) -> None:
    """Apply the app's real dark theme (token-based) for the landing shots.

    Setting the dark palette makes ``theme.is_dark()`` resolve to True via its
    luminance fallback, so every view and chart renders in dark mode.
    """
    from optees.core.design import DARK
    from optees.core.qss import build_palette, build_stylesheet

    app.setStyle("Fusion")
    app.setPalette(build_palette(DARK))
    app.setStyleSheet(build_stylesheet(DARK))


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


def _nlp_model() -> NLPModel:
    return NLPModel.from_parts(
        variables=[
            NLPVariable("x1", "first coordinate", -2.0, 2.0, -1.0),
            NLPVariable("x2", "second coordinate", -2.0, 2.0, 1.0),
        ],
        objective=NLPObjective("(x1 - 1)**2 + (x2 + 1)**2"),
        options=NLPOptions(method=NLPSolverMethod.L_BFGS_B),
    )


def _delivery_graph_model() -> ShortestPathModel:
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


def _regression_model() -> RegressionModel:
    return RegressionModel(
        RegressionDataset.from_rows(
            feature_names=("floor_area",),
            target_name="price",
            rows=[
                ((40,), 100),
                ((50,), 130),
                ((60,), 150),
                ((70,), 180),
                ((80,), 200),
                ((90,), 235),
                ((100,), 255),
                ((110,), 285),
            ],
        ),
        RegressionOptions(test_fraction=0.25, random_seed=42),
    )


def _classification_model() -> BinaryClassificationModel:
    return BinaryClassificationModel(
        ClassificationDataset.from_rows(
            feature_names=("score", "debt_ratio"),
            target_name="approved",
            rows=[
                ((38, 0.78), "no"),
                ((44, 0.70), "no"),
                ((51, 0.64), "no"),
                ((57, 0.55), "no"),
                ((68, 0.42), "yes"),
                ((74, 0.35), "yes"),
                ((81, 0.28), "yes"),
                ((88, 0.19), "yes"),
            ],
        ),
        ClassificationOptions(test_fraction=0.25, random_seed=42, l2_alpha=0.2),
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

    nlp_model = _nlp_model()
    nlp_solution = window.solve_nlp_uc.execute(nlp_model)
    window.nlp_solution_page.set_problem(nlp_model)
    window.nlp_solution_page.set_solution(nlp_solution)
    _capture(window, "optees-nlp-solution.png", "nlp_solution")

    graph_model = _delivery_graph_model()
    graph_solution = window.solve_shortest_path_uc.execute(graph_model)
    window.graph_solution_page.set_problem(graph_model)
    window.graph_solution_page.set_solution(graph_solution)
    _capture(window, "optees-graph-solution.png", "graph_solution")

    regression_model = _regression_model()
    regression_solution = window.train_regression_uc.execute(regression_model)
    window.regression_solution_page.set_problem(regression_model)
    window.regression_solution_page.set_solution(regression_solution)
    _capture(window, "optees-regression-solution.png", "regression_solution")

    classification_model = _classification_model()
    classification_solution = window.train_classification_uc.execute(classification_model)
    window.classification_solution_page.set_problem(classification_model)
    window.classification_solution_page.set_solution(classification_solution)
    _capture(window, "optees-classification-solution.png", "classification_solution")

    window.close()


if __name__ == "__main__":
    main()
