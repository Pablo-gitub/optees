# src/optees/presentation/main_window.py
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QToolBar, QToolButton, QMenu,
    QStatusBar, QSizePolicy
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QEvent, Qt, QSize, QTimer

from optees.core.theme import theme
from optees.core.assets import asset
from optees.core.string_manager import strings as S
from optees.core.version import get_app_version, is_packaged_app

from optees.presentation.views.home_view import HomePage
from optees.presentation.views.lp_view.lp_view import LPView
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView
from optees.presentation.views.knapsack_solution_view import KnapsackSolutionView
from optees.presentation.views.nlp_view import NLPView
from optees.presentation.views.nlp_solution_view import NLPSolutionView
from optees.presentation.views.graph_view import GraphView
from optees.presentation.views.graph_solution_view import GraphSolutionView
from optees.presentation.views.packing_view import PackingView
from optees.presentation.views.packing_solution_view import PackingSolutionView
from optees.presentation.views.regression_view import RegressionView
from optees.presentation.views.forecasting_view import ForecastingView
from optees.presentation.views.regression_solution_view import RegressionSolutionView
from optees.presentation.views.classification_view import ClassificationView
from optees.presentation.views.classification_solution_view import ClassificationSolutionView
from optees.presentation.views.assistant_view import AssistantView
from optees.presentation.views.widgets.floating_assistant_button import (
    FloatingAssistantButton,
)
from optees.presentation.views.settings_view import SettingsView
from optees.presentation.views.lp_info_view import (
    LPExampleView,
    LPProblemDescriptionView,
    MILPExampleView,
    MILPProblemDescriptionView,
    KnapsackExampleView,
    KnapsackProblemDescriptionView,
    NLPExampleView,
    NLPProblemDescriptionView,
    GraphExampleView,
    GraphProblemDescriptionView,
    RegressionExampleView,
    RegressionProblemDescriptionView,
    ClassificationExampleView,
    ClassificationProblemDescriptionView,
    PackingExampleView,
    PackingProblemDescriptionView,
)
from optees.presentation.controllers.lp_controller import LPController
from optees.presentation.controllers.milp_controller import MILPController
from optees.presentation.controllers.knapsack_controller import KnapsackController
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.application.usecases.solve_nlp_usecase import SolveNLPUseCase
from optees.application.usecases.solve_shortest_path_usecase import SolveShortestPathUseCase
from optees.application.usecases.train_regression_usecase import TrainRegressionUseCase
from optees.application.usecases.forecast_time_series_usecase import ForecastTimeSeriesUseCase
from optees.application.usecases.train_classification_usecase import TrainClassificationUseCase
from optees.application.usecases.solve_single_container_packing_usecase import (
    SolveSingleContainerPackingUseCase,
)
from optees.application.usecases.solve_bounded_knapsack_usecase import SolveBoundedKnapsackUseCase
from optees.application.usecases.solve_fractional_knapsack_usecase import SolveFractionalKnapsackUseCase
from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.application.usecases.solve_multi_dimensional_knapsack_usecase import (
    SolveMultiDimensionalKnapsackUseCase,
)
from optees.application.usecases.solve_unbounded_knapsack_usecase import SolveUnboundedKnapsackUseCase
from optees.application.usecases.check_for_updates_usecase import CheckForUpdatesUseCase
from optees.application.usecases.download_update_usecase import DownloadUpdateUseCase
from optees.application.usecases.handoff_update_usecase import HandoffUpdateUseCase
from optees.application.usecases.execute_update_usecase import ExecuteUpdateUseCase
from optees.application.services.update_staging import UpdateStagingService
from optees.application.usecases.analyze_problem_description_usecase import (
    AnalyzeProblemDescriptionUseCase,
)
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.data.adapters.milp.milp_solver_adapter import MILPSolverAdapter
from optees.data.adapters.nlp.nlp_solver_adapter import ScipyNLPSolverAdapter
from optees.data.adapters.graph.dijkstra_solver_adapter import DijkstraSolverAdapter
from optees.data.adapters.regression.numpy_regression_adapter import NumpyRegressionAdapter
from optees.data.adapters.forecasting import (
    BaselineForecastingAdapter,
    HoltWintersForecastingAdapter,
)
from optees.domain.value_objects.forecasting import ForecastingMethod
from optees.data.adapters.classification.numpy_classification_adapter import NumpyClassificationAdapter
from optees.data.adapters.packing.ortools_single_container_packing_adapter import (
    OrtoolsSingleContainerPackingAdapter,
)
from optees.data.adapters.knapsack.bounded_knapsack_solver_adapter import BoundedKnapsackSolverAdapter
from optees.data.adapters.knapsack.fractional_knapsack_solver_adapter import FractionalKnapsackSolverAdapter
from optees.data.adapters.knapsack.knapsack_solver_adapter import KnapsackSolverAdapter
from optees.data.adapters.knapsack.multi_dimensional_knapsack_solver_adapter import (
    MultiDimensionalKnapsackSolverAdapter,
)
from optees.data.adapters.knapsack.unbounded_knapsack_solver_adapter import UnboundedKnapsackSolverAdapter
from optees.data.adapters.github.update_provider_adapter import GitHubUpdateProvider
from optees.data.adapters.system import DesktopUpdateHandoffAdapter
from optees.data.adapters.assistant import RuleBasedAssistantAdapter
from optees.presentation.views.lp_solution_view.lp_solution_view import LPSolutionView
from optees.presentation.controllers.main_controller import MainController
from optees.presentation.controllers.update_controller import UpdateController
from optees.presentation.controllers.local_server_controller import LocalServerController
from optees.application.services.local_server_process import LocalServerProcessManager


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Optees")
        self.resize(1100, 720)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._pages = {}  # <- registry

        # --- pages ---
        self.home_page = HomePage()
        self.assistant_page = AssistantView()
        self.assistant_adapter = RuleBasedAssistantAdapter()
        self.analyze_problem_description_uc = AnalyzeProblemDescriptionUseCase(
            self.assistant_adapter,
        )
        self.assistant_page.set_usecase(self.analyze_problem_description_uc)

        self.lp_page = LPView()
        self.lp_controller = LPController()
        self.lp_page.set_controller(self.lp_controller)

        # use case wiring (composition root)
        self.solver_port = LPSolverAdapter()
        self.solve_lp_uc = SolveLPUseCase(self.solver_port)
        self.lp_page.set_solve_usecase(self.solve_lp_uc)

        self.milp_page = MILPView()
        self.milp_controller = MILPController()
        self.milp_page.set_controller(self.milp_controller)
        self.milp_solver_port = MILPSolverAdapter()
        self.solve_milp_uc = SolveMILPUseCase(self.milp_solver_port)
        self.milp_page.set_solve_usecase(self.solve_milp_uc)

        self.nlp_page = NLPView()
        self.nlp_solver_port = ScipyNLPSolverAdapter()
        self.solve_nlp_uc = SolveNLPUseCase(self.nlp_solver_port)
        self.nlp_page.set_solve_usecase(self.solve_nlp_uc)

        self.graph_page = GraphView()
        self.graph_solver_port = DijkstraSolverAdapter()
        self.solve_shortest_path_uc = SolveShortestPathUseCase(self.graph_solver_port)
        self.graph_page.set_solve_usecase(self.solve_shortest_path_uc)

        self.packing_page = PackingView()
        self.packing_solver_port = OrtoolsSingleContainerPackingAdapter()
        self.solve_packing_uc = SolveSingleContainerPackingUseCase(self.packing_solver_port)
        self.packing_page.set_solve_usecase(self.solve_packing_uc)

        self.regression_page = RegressionView()
        self.regression_solver_port = NumpyRegressionAdapter()
        self.train_regression_uc = TrainRegressionUseCase(self.regression_solver_port)
        self.regression_page.set_solve_usecase(self.train_regression_uc)

        self.classification_page = ClassificationView()
        self.classification_solver_port = NumpyClassificationAdapter()
        self.train_classification_uc = TrainClassificationUseCase(self.classification_solver_port)
        self.classification_page.set_solve_usecase(self.train_classification_uc)

        self.forecasting_page = ForecastingView()
        forecasting_baseline = BaselineForecastingAdapter()
        forecasting_trend = HoltWintersForecastingAdapter()
        self.forecast_uc = ForecastTimeSeriesUseCase(
            {
                ForecastingMethod.NAIVE: forecasting_baseline,
                ForecastingMethod.SEASONAL_NAIVE: forecasting_baseline,
                ForecastingMethod.HOLT_WINTERS_ADDITIVE: forecasting_trend,
            }
        )
        self.forecasting_page.set_solve_usecase(self.forecast_uc)

        self.knap_page = KnapsackView()
        self.knapsack_controller = KnapsackController()
        self.knap_page.set_controller(self.knapsack_controller)
        self.knapsack_solver_port = KnapsackSolverAdapter()
        self.solve_knapsack_uc = SolveKnapsackUseCase(self.knapsack_solver_port)
        self.knap_page.set_solve_usecase(self.solve_knapsack_uc)
        self.bounded_knapsack_solver_port = BoundedKnapsackSolverAdapter()
        self.solve_bounded_knapsack_uc = SolveBoundedKnapsackUseCase(
            self.bounded_knapsack_solver_port,
        )
        self.knap_page.set_bounded_solve_usecase(self.solve_bounded_knapsack_uc)
        self.unbounded_knapsack_solver_port = UnboundedKnapsackSolverAdapter()
        self.solve_unbounded_knapsack_uc = SolveUnboundedKnapsackUseCase(
            self.unbounded_knapsack_solver_port,
        )
        self.knap_page.set_unbounded_solve_usecase(self.solve_unbounded_knapsack_uc)
        self.fractional_knapsack_solver_port = FractionalKnapsackSolverAdapter()
        self.solve_fractional_knapsack_uc = SolveFractionalKnapsackUseCase(
            self.fractional_knapsack_solver_port,
        )
        self.knap_page.set_fractional_solve_usecase(self.solve_fractional_knapsack_uc)
        self.multi_dimensional_knapsack_solver_port = MultiDimensionalKnapsackSolverAdapter()
        self.solve_multi_dimensional_knapsack_uc = SolveMultiDimensionalKnapsackUseCase(
            self.multi_dimensional_knapsack_solver_port,
        )
        self.knap_page.set_multi_dimensional_solve_usecase(
            self.solve_multi_dimensional_knapsack_uc,
        )
        self.knap_page.set_multi_dimensional_milp_solve_usecase(self.solve_milp_uc)
        self.settings_page = SettingsView()
        self.local_server_manager = LocalServerProcessManager()
        self.local_server_controller = LocalServerController(
            self.settings_page,
            self.local_server_manager,
            self,
        )
        self.lp_example_page = LPExampleView()
        self.lp_problem_page = LPProblemDescriptionView()
        self.milp_example_page = MILPExampleView()
        self.milp_problem_page = MILPProblemDescriptionView()
        self.knapsack_example_page = KnapsackExampleView()
        self.knapsack_problem_page = KnapsackProblemDescriptionView()
        self.nlp_example_page = NLPExampleView()
        self.nlp_problem_page = NLPProblemDescriptionView()
        self.graph_example_page = GraphExampleView()
        self.graph_problem_page = GraphProblemDescriptionView()
        self.packing_example_page = PackingExampleView()
        self.packing_problem_page = PackingProblemDescriptionView()
        self.regression_example_page = RegressionExampleView()
        self.regression_problem_page = RegressionProblemDescriptionView()
        self.classification_example_page = ClassificationExampleView()
        self.classification_problem_page = ClassificationProblemDescriptionView()

        # (NEW) solution page placeholder
        self.lp_solution_page = LPSolutionView()
        self.milp_solution_page = LPSolutionView()
        self.knapsack_solution_page = KnapsackSolutionView()
        self.nlp_solution_page = NLPSolutionView()
        self.graph_solution_page = GraphSolutionView()
        self.packing_solution_page = PackingSolutionView()
        self.regression_solution_page = RegressionSolutionView()
        self.classification_solution_page = ClassificationSolutionView()

        # register pages
        self.register_page("home", self.home_page)
        self.register_page("assistant", self.assistant_page)
        self.register_page("lp", self.lp_page)
        self.register_page("lp_example", self.lp_example_page)
        self.register_page("lp_problem", self.lp_problem_page)
        self.register_page("milp_example", self.milp_example_page)
        self.register_page("milp_problem", self.milp_problem_page)
        self.register_page("knapsack_example", self.knapsack_example_page)
        self.register_page("knapsack_problem", self.knapsack_problem_page)
        self.register_page("nlp", self.nlp_page)
        self.register_page("nlp_example", self.nlp_example_page)
        self.register_page("nlp_problem", self.nlp_problem_page)
        self.register_page("nlp_solution", self.nlp_solution_page)
        self.register_page("graph", self.graph_page)
        self.register_page("graph_example", self.graph_example_page)
        self.register_page("graph_problem", self.graph_problem_page)
        self.register_page("graph_solution", self.graph_solution_page)
        self.register_page("packing", self.packing_page)
        self.register_page("packing_example", self.packing_example_page)
        self.register_page("packing_problem", self.packing_problem_page)
        self.register_page("packing_solution", self.packing_solution_page)
        self.register_page("regression", self.regression_page)
        self.register_page("regression_example", self.regression_example_page)
        self.register_page("regression_problem", self.regression_problem_page)
        self.register_page("regression_solution", self.regression_solution_page)
        self.register_page("classification", self.classification_page)
        self.register_page("classification_example", self.classification_example_page)
        self.register_page("classification_problem", self.classification_problem_page)
        self.register_page("classification_solution", self.classification_solution_page)
        self.register_page("forecasting", self.forecasting_page)
        self.register_page("lp_solution", self.lp_solution_page)
        self.register_page("milp", self.milp_page)
        self.register_page("milp_solution", self.milp_solution_page)
        self.register_page("knapsack", self.knap_page)
        self.register_page("knapsack_solution", self.knapsack_solution_page)
        self.register_page("settings", self.settings_page)

        self.stack.setCurrentWidget(self.home_page)

        self._build_toolbar()
        self._build_assistant_bubble()
        self.setStatusBar(QStatusBar(self))
        self._apply_window_icon()
        theme.theme_changed.connect(self._on_theme_changed)
        S.language_changed.connect(self._retranslate_toolbar)

        self.update_provider = GitHubUpdateProvider()
        self.check_updates_uc = CheckForUpdatesUseCase(
            self.update_provider,
            current_version=get_app_version(),
        )
        self.download_update_uc = DownloadUpdateUseCase(self.update_provider)
        self.update_handoff = DesktopUpdateHandoffAdapter()
        self.handoff_update_uc = HandoffUpdateUseCase(self.update_handoff)
        self.update_staging = UpdateStagingService()
        self.execute_update_uc = ExecuteUpdateUseCase(
            self.download_update_uc,
            self.handoff_update_uc,
            self.update_staging,
        )
        self.update_controller = UpdateController(
            self.check_updates_uc,
            self.execute_update_uc,
            self,
        )
        packaged = is_packaged_app()
        updates_disabled = os.getenv("OPTEES_DISABLE_UPDATE_CHECK") == "1"
        if not packaged:
            self.settings_page.set_update_development_build(get_app_version())
        elif updates_disabled:
            self.settings_page.set_update_disabled(get_app_version())
        else:
            self.settings_page.set_update_checking(get_app_version())

        # (NEW) create MainController here
        self.main_controller = MainController(self)
        if packaged and not updates_disabled:
            QTimer.singleShot(900, self.update_controller.check_for_updates)

    def closeEvent(self, event) -> None:
        self.local_server_controller.shutdown()
        super().closeEvent(event)

    # --- page registry ---
    def register_page(self, name: str, widget: QWidget) -> None:
        self._pages[name] = widget
        self.stack.addWidget(widget)

    def page(self, name: str) -> QWidget:
        return self._pages[name]

    def goto(self, name: str) -> None:
        self.stack.setCurrentWidget(self._pages[name])
        self._update_assistant_bubble_visibility()

    def _build_assistant_bubble(self) -> None:
        self.assistant_bubble = FloatingAssistantButton(
            asset("icons/assistant.png"),
            self.stack,
        )
        self.assistant_bubble.setToolTip(S.t("assistant.bubble_tooltip"))
        self.assistant_bubble.clicked_without_drag.connect(lambda: self.goto("assistant"))
        self.stack.installEventFilter(self)
        self.stack.currentChanged.connect(lambda _index: self._update_assistant_bubble_visibility())
        QTimer.singleShot(0, self._update_assistant_bubble_visibility)

    def _update_assistant_bubble_visibility(self) -> None:
        if not hasattr(self, "assistant_bubble"):
            return
        is_assistant = self.stack.currentWidget() is self.assistant_page
        self.assistant_bubble.setVisible(not is_assistant)
        if is_assistant:
            return
        if self.assistant_bubble.was_manually_positioned():
            self.assistant_bubble.keep_inside_parent()
        else:
            self.assistant_bubble.anchor_bottom_right()
        self.assistant_bubble.raise_()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.stack and event.type() in (QEvent.Resize, QEvent.Show):
            QTimer.singleShot(0, self._update_assistant_bubble_visibility)
        return super().eventFilter(watched, event)

    # ---------------- toolbar with dropdown + settings button (right) -------------
    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(S.t("nav.toolbar.title"))
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # Home
        self.act_home = QAction(S.t("nav.home"), self)
        self.act_home.triggered.connect(lambda: self.goto("home"))
        self.toolbar.addAction(self.act_home)

        # Dropdown: Linear Optimization
        self.drop = QToolButton(self)
        self.drop.setText(S.t("nav.linear_optimization"))
        self.drop.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(self.drop)

        self.act_lp = QAction(S.t("alg.lp"), self)
        self.act_lp.triggered.connect(lambda: self.goto("lp"))
        menu.addAction(self.act_lp)

        self.act_milp = QAction(S.t("alg.milp"), self)
        self.act_milp.triggered.connect(lambda: self.goto("milp"))
        menu.addAction(self.act_milp)

        self.act_knap = QAction(S.t("alg.knap"), self)
        self.act_knap.triggered.connect(lambda: self.goto("knapsack"))
        menu.addAction(self.act_knap)

        self.act_packing = QAction(S.t("alg.packing"), self)
        self.act_packing.triggered.connect(lambda: self.goto("packing"))
        menu.addAction(self.act_packing)

        self.drop.setMenu(menu)
        self.toolbar.addWidget(self.drop)

        self.act_nlp = QAction(S.t("alg.nlp"), self)
        self.act_nlp.triggered.connect(lambda: self.goto("nlp"))
        self.toolbar.addAction(self.act_nlp)

        self.act_graph = QAction(S.t("alg.graph"), self)
        self.act_graph.triggered.connect(lambda: self.goto("graph"))
        self.toolbar.addAction(self.act_graph)

        self.drop_ml = QToolButton(self)
        self.drop_ml.setText(S.t("nav.machine_learning").replace("&", "&&"))
        self.drop_ml.setPopupMode(QToolButton.InstantPopup)
        ml_menu = QMenu(self.drop_ml)
        self.act_regression = QAction(S.t("alg.regression"), self)
        self.act_regression.triggered.connect(lambda: self.goto("regression"))
        ml_menu.addAction(self.act_regression)
        self.act_classification = QAction(S.t("alg.classification"), self)
        self.act_classification.triggered.connect(lambda: self.goto("classification"))
        ml_menu.addAction(self.act_classification)
        self.drop_ml.setMenu(ml_menu)
        self.toolbar.addWidget(self.drop_ml)

        # spacer
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        # Settings
        self.act_settings = QAction(S.t("nav.settings"), self)
        self.act_settings.setToolTip(S.t("nav.settings"))
        self.act_settings.setIcon(QIcon())
        self.act_settings.triggered.connect(lambda: self.goto("settings"))
        self.toolbar.addAction(self.act_settings)


    # ---------------- theming helpers ----------------

    def _apply_window_icon(self) -> None:
        try:
            sub = "dark" if theme.is_dark() else "light"
            self.setWindowIcon(QIcon(str(asset(f"logo/{sub}/appicon_256.png"))))
        except Exception:
            pass

    def _on_theme_changed(self) -> None:
        self._apply_window_icon()
        for page in (self.home_page, self.lp_page, self.lp_example_page, self.lp_problem_page,
                    self.milp_example_page, self.milp_problem_page,
                    self.knapsack_example_page, self.knapsack_problem_page,
                    self.lp_solution_page, self.milp_solution_page, self.knapsack_solution_page,
                    self.milp_page, self.knap_page, self.nlp_page, self.nlp_example_page,
                    self.nlp_problem_page, self.nlp_solution_page, self.graph_page,
                    self.graph_example_page, self.graph_problem_page, self.graph_solution_page,
                    self.packing_page, self.packing_example_page, self.packing_problem_page,
                    self.packing_solution_page,
                    self.regression_page, self.regression_example_page,
                    self.regression_problem_page, self.regression_solution_page,
                    self.classification_page, self.classification_example_page,
                    self.classification_problem_page, self.classification_solution_page,
                    self.forecasting_page,
                    self.assistant_page,
                    self.settings_page):
            if hasattr(page, "refresh_theme"):
                try: page.refresh_theme()
                except Exception: pass

    def _retranslate_toolbar(self) -> None:
        # niente findChild: abbiamo self.toolbar
        self.toolbar.setWindowTitle(S.t("nav.toolbar.title"))
        self.act_home.setText(S.t("nav.home"))
        self.drop.setText(S.t("nav.linear_optimization"))
        self.act_lp.setText(S.t("alg.lp"))
        self.act_milp.setText(S.t("alg.milp"))
        self.act_knap.setText(S.t("alg.knap"))
        self.act_nlp.setText(S.t("alg.nlp"))
        self.act_graph.setText(S.t("alg.graph"))
        self.act_packing.setText(S.t("alg.packing"))
        self.drop_ml.setText(S.t("nav.machine_learning").replace("&", "&&"))
        self.act_regression.setText(S.t("alg.regression"))
        self.act_classification.setText(S.t("alg.classification"))
        self.act_settings.setText(S.t("nav.settings"))
        self.act_settings.setToolTip(S.t("nav.settings"))
        if hasattr(self, "assistant_bubble"):
            self.assistant_bubble.setToolTip(S.t("assistant.bubble_tooltip"))

        # retranslate pages
        for page in (self.home_page, self.lp_page, self.lp_example_page, self.lp_problem_page,
                 self.milp_example_page, self.milp_problem_page,
                 self.knapsack_example_page, self.knapsack_problem_page,
                 self.lp_solution_page, self.milp_solution_page, self.knapsack_solution_page,
                 self.milp_page, self.knap_page, self.nlp_page, self.nlp_example_page,
                 self.nlp_problem_page, self.nlp_solution_page, self.graph_page,
                 self.graph_example_page, self.graph_problem_page, self.graph_solution_page,
                 self.packing_page, self.packing_example_page, self.packing_problem_page,
                 self.packing_solution_page,
                 self.regression_page, self.regression_example_page,
                 self.regression_problem_page, self.regression_solution_page,
                 self.classification_page, self.classification_example_page,
                 self.classification_problem_page, self.classification_solution_page,
                 self.forecasting_page,
                 self.assistant_page,
                 self.settings_page):
            if hasattr(page, "refresh_strings"):
                try: page.refresh_strings()
                except Exception: pass
