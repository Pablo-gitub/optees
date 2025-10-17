# src/optees/presentation/controllers/main_controller.py
from __future__ import annotations
from PySide6.QtCore import QObject
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from optees.presentation.main_window import MainWindow

from optees.presentation.views.lp_view.lp_view import LPView
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
