# src/optees/presentation/main_window.py
from __future__ import annotations
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QToolBar, QToolButton, QMenu,
    QStatusBar, QSizePolicy
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSize

from optees.core.theme import theme
from optees.core.assets import asset
from optees.core.string_manager import strings as S

from optees.presentation.views.home_view import HomePage
from optees.presentation.views.lp_view.lp_view import LPView
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView
from optees.presentation.views.knapsack_solution_view import KnapsackSolutionView
from optees.presentation.views.settings_view import SettingsView
from optees.presentation.views.lp_info_view import (
    LPExampleView,
    LPProblemDescriptionView,
    MILPExampleView,
    MILPProblemDescriptionView,
    KnapsackExampleView,
    KnapsackProblemDescriptionView,
)
from optees.presentation.controllers.lp_controller import LPController
from optees.presentation.controllers.milp_controller import MILPController
from optees.presentation.controllers.knapsack_controller import KnapsackController
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.data.adapters.milp.milp_solver_adapter import MILPSolverAdapter
from optees.data.adapters.knapsack.knapsack_solver_adapter import KnapsackSolverAdapter
from optees.presentation.views.lp_solution_view.lp_solution_view import LPSolutionView
from optees.presentation.controllers.main_controller import MainController


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

        self.knap_page = KnapsackView()
        self.knapsack_controller = KnapsackController()
        self.knap_page.set_controller(self.knapsack_controller)
        self.knapsack_solver_port = KnapsackSolverAdapter()
        self.solve_knapsack_uc = SolveKnapsackUseCase(self.knapsack_solver_port)
        self.knap_page.set_solve_usecase(self.solve_knapsack_uc)
        self.settings_page = SettingsView()
        self.lp_example_page = LPExampleView()
        self.lp_problem_page = LPProblemDescriptionView()
        self.milp_example_page = MILPExampleView()
        self.milp_problem_page = MILPProblemDescriptionView()
        self.knapsack_example_page = KnapsackExampleView()
        self.knapsack_problem_page = KnapsackProblemDescriptionView()

        # (NEW) solution page placeholder
        self.lp_solution_page = LPSolutionView()
        self.milp_solution_page = LPSolutionView()
        self.knapsack_solution_page = KnapsackSolutionView()

        # register pages
        self.register_page("home", self.home_page)
        self.register_page("lp", self.lp_page)
        self.register_page("lp_example", self.lp_example_page)
        self.register_page("lp_problem", self.lp_problem_page)
        self.register_page("milp_example", self.milp_example_page)
        self.register_page("milp_problem", self.milp_problem_page)
        self.register_page("knapsack_example", self.knapsack_example_page)
        self.register_page("knapsack_problem", self.knapsack_problem_page)
        self.register_page("lp_solution", self.lp_solution_page)
        self.register_page("milp", self.milp_page)
        self.register_page("milp_solution", self.milp_solution_page)
        self.register_page("knapsack", self.knap_page)
        self.register_page("knapsack_solution", self.knapsack_solution_page)
        self.register_page("settings", self.settings_page)

        self.stack.setCurrentWidget(self.home_page)

        self._build_toolbar()
        self.setStatusBar(QStatusBar(self))
        self._apply_window_icon()
        theme.theme_changed.connect(self._on_theme_changed)
        S.language_changed.connect(self._retranslate_toolbar)

        # (NEW) create MainController here
        self.main_controller = MainController(self)

    # --- page registry ---
    def register_page(self, name: str, widget: QWidget) -> None:
        self._pages[name] = widget
        self.stack.addWidget(widget)

    def page(self, name: str) -> QWidget:
        return self._pages[name]

    def goto(self, name: str) -> None:
        self.stack.setCurrentWidget(self._pages[name])

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

        self.drop.setMenu(menu)
        self.toolbar.addWidget(self.drop)

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
                    self.milp_page, self.knap_page, self.settings_page):
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
        self.act_settings.setText(S.t("nav.settings"))
        self.act_settings.setToolTip(S.t("nav.settings"))

        # retranslate pages
        for page in (self.home_page, self.lp_page, self.lp_example_page, self.lp_problem_page,
                 self.milp_example_page, self.milp_problem_page,
                 self.knapsack_example_page, self.knapsack_problem_page,
                 self.lp_solution_page, self.milp_solution_page, self.knapsack_solution_page,
                 self.milp_page, self.knap_page, self.settings_page):
            if hasattr(page, "refresh_strings"):
                try: page.refresh_strings()
                except Exception: pass
