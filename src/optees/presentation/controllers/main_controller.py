# src/optees/presentation/controllers/main_controller.py
from __future__ import annotations
from PySide6.QtCore import QObject
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from optees.presentation.main_window import MainWindow

from optees.presentation.views.lp_view.lp_view import LPView
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView
from optees.presentation.views.home_view import HomePage  # usa lo stesso nome che usi nel MainWindow
import logging
log = logging.getLogger(__name__)

class MainController(QObject):
    """Presentation controller: centralizza routing e wiring segnali -> azioni UI."""

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.window = window

        # Home -> navigation
        home: HomePage = self.window.page("home")  # type: ignore[assignment]
        if hasattr(home, "go_lp"):
            home.go_lp.connect(lambda: self.window.goto("lp"))
        if hasattr(home, "go_milp"):
            home.go_milp.connect(lambda: self.window.goto("milp"))
        if hasattr(home, "go_knap"):
            home.go_knap.connect(lambda: self.window.goto("knapsack"))

        # LP -> Solution
        lp: LPView = self.window.page("lp")  # type: ignore[assignment]
        lp.solve_completed.connect(self._on_lp_solved)
        if hasattr(lp, "example_requested"):
            lp.example_requested.connect(lambda: self.window.goto("lp_example"))
        if hasattr(lp, "problem_description_requested"):
            lp.problem_description_requested.connect(lambda: self.window.goto("lp_problem"))

        for name in ("lp_example", "lp_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("lp"))

        # Solution -> Back to LP
        sol_view = self.window.page("lp_solution")
        if hasattr(sol_view, "back_requested"):
            sol_view.back_requested.connect(lambda: self.window.goto("lp"))

        # MILP -> Solution
        milp: MILPView = self.window.page("milp")  # type: ignore[assignment]
        if hasattr(milp, "solve_completed"):
            milp.solve_completed.connect(self._on_milp_solved)
        if hasattr(milp, "example_requested"):
            milp.example_requested.connect(lambda: self.window.goto("milp_example"))
        if hasattr(milp, "problem_description_requested"):
            milp.problem_description_requested.connect(lambda: self.window.goto("milp_problem"))

        for name in ("milp_example", "milp_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("milp"))

        milp_sol_view = self.window.page("milp_solution")
        if hasattr(milp_sol_view, "back_requested"):
            milp_sol_view.back_requested.connect(lambda: self.window.goto("milp"))

        # Knapsack -> Solution
        knap: KnapsackView = self.window.page("knapsack")  # type: ignore[assignment]
        if hasattr(knap, "solve_completed"):
            knap.solve_completed.connect(self._on_knapsack_solved)
        if hasattr(knap, "example_requested"):
            knap.example_requested.connect(lambda: self.window.goto("knapsack_example"))
        if hasattr(knap, "problem_description_requested"):
            knap.problem_description_requested.connect(lambda: self.window.goto("knapsack_problem"))

        for name in ("knapsack_example", "knapsack_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("knapsack"))

        knap_sol_view = self.window.page("knapsack_solution")
        if hasattr(knap_sol_view, "back_requested"):
            knap_sol_view.back_requested.connect(lambda: self.window.goto("knapsack"))

    def _on_lp_solved(self, solution) -> None:
        # 1) Recover the Solution page
        sol_view = self.window.page("lp_solution")

        # 2) Pass the problem context (variable names, objective coefs, offset)
        try:
            model_snapshot = self.window.lp_controller.model()
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(model_snapshot)  # type: ignore[attr-defined]
        except Exception:
            # If anything goes wrong, still proceed with the solution
            pass

        # 3) Pass the solution itself
        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]

        try:
            log.debug("Solution received: status=%s objective=%s",
                    getattr(solution, "status", None),
                    getattr(solution, "objective", None))
        except Exception:
            pass

        # 4) Navigate to the solution page
        self.window.goto("lp_solution")

    def _on_milp_solved(self, solution) -> None:
        sol_view = self.window.page("milp_solution")

        try:
            model_snapshot = self.window.milp_controller.model()
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(model_snapshot)  # type: ignore[attr-defined]
        except Exception:
            pass

        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]

        try:
            log.debug("MILP solution received: status=%s objective=%s",
                    getattr(solution, "status", None),
                    getattr(solution, "objective", None))
        except Exception:
            pass

        self.window.goto("milp_solution")

    def _on_knapsack_solved(self, solution) -> None:
        sol_view = self.window.page("knapsack_solution")

        try:
            model_snapshot = self.window.knapsack_controller.model()
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(model_snapshot)  # type: ignore[attr-defined]
        except Exception:
            pass

        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]

        try:
            log.debug(
                "Knapsack solution received: status=%s objective=%s",
                getattr(solution, "status", None),
                getattr(solution, "objective", None),
            )
        except Exception:
            pass

        self.window.goto("knapsack_solution")
