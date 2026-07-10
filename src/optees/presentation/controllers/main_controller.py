# src/optees/presentation/controllers/main_controller.py
from __future__ import annotations
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from optees.presentation.main_window import MainWindow

from optees.presentation.views.lp_view.lp_view import LPView
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView
from optees.presentation.views.home_view import HomePage  # usa lo stesso nome che usi nel MainWindow
from optees.core.string_manager import strings as S
from optees.utility.knapsack_json_io import knapsack_problem_from_dict
from optees.utility.lp_json_io import lp_model_from_dict
from optees.utility.milp_json_io import milp_model_from_dict
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

        assistant = self.window.page("assistant")
        if hasattr(assistant, "back_requested"):
            assistant.back_requested.connect(lambda: self.window.goto("home"))
        if hasattr(assistant, "load_lp_requested"):
            assistant.load_lp_requested.connect(self._load_assistant_lp_model)
        if hasattr(assistant, "load_milp_requested"):
            assistant.load_milp_requested.connect(self._load_assistant_milp_model)
        if hasattr(assistant, "load_knapsack_requested"):
            assistant.load_knapsack_requested.connect(self._load_assistant_knapsack_problem)

        self._wire_updates()

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
            knap_page = self.window.page("knapsack")
            if hasattr(knap_page, "current_problem_model"):
                model_snapshot = knap_page.current_problem_model()
            else:
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

    def _load_assistant_lp_model(self, data: object) -> None:
        try:
            model = lp_model_from_dict(dict(data))  # type: ignore[arg-type]
            self.window.lp_controller.load_model(model)
            self.window.goto("lp")
        except Exception as exc:
            self._show_assistant_load_error(exc)

    def _load_assistant_milp_model(self, data: object) -> None:
        try:
            model = milp_model_from_dict(dict(data))  # type: ignore[arg-type]
            self.window.milp_controller.load_model(model)
            self.window.goto("milp")
        except Exception as exc:
            self._show_assistant_load_error(exc)

    def _load_assistant_knapsack_problem(self, data: object) -> None:
        try:
            problem = knapsack_problem_from_dict(dict(data))  # type: ignore[arg-type]
            knap = self.window.page("knapsack")
            if hasattr(knap, "load_json_problem"):
                knap.load_json_problem(problem)  # type: ignore[attr-defined]
            self.window.goto("knapsack")
        except Exception as exc:
            self._show_assistant_load_error(exc)

    def _show_assistant_load_error(self, exc: Exception) -> None:
        QMessageBox.warning(
            self.window,
            S.t("assistant.import_error.title"),
            S.t("assistant.import_error.body", detail=str(exc)),
        )

    def _wire_updates(self) -> None:
        update_controller = getattr(self.window, "update_controller", None)
        if update_controller is None:
            return

        home = self.window.page("home")
        if hasattr(home, "update_requested"):
            home.update_requested.connect(update_controller.download_and_launch_update)

        update_controller.check_completed.connect(self._on_update_check_completed)
        update_controller.check_failed.connect(self._on_update_check_failed)
        update_controller.download_started.connect(self._on_update_download_started)
        update_controller.download_completed.connect(self._on_update_download_completed)
        update_controller.download_failed.connect(self._on_update_download_failed)

    def _on_update_check_completed(self, result) -> None:
        home = self.window.page("home")
        settings = self.window.page("settings")
        if hasattr(settings, "set_update_status"):
            settings.set_update_status(result)
        if getattr(result, "update_available", False):
            if hasattr(home, "set_update_available"):
                home.set_update_available(result)
        elif hasattr(home, "hide_update_banner"):
            home.hide_update_banner()

    def _on_update_check_failed(self, message: str) -> None:
        home = self.window.page("home")
        settings = self.window.page("settings")
        if hasattr(home, "hide_update_banner"):
            home.hide_update_banner()
        if hasattr(settings, "set_update_error"):
            settings.set_update_error(message)

    def _on_update_download_started(self, result) -> None:
        home = self.window.page("home")
        settings = self.window.page("settings")
        if hasattr(home, "set_update_download_in_progress"):
            home.set_update_download_in_progress(result)
        if hasattr(settings, "set_update_downloading"):
            settings.set_update_downloading(getattr(result, "latest_version", None))

    def _on_update_download_failed(self, message: str) -> None:
        home = self.window.page("home")
        settings = self.window.page("settings")
        update_controller = getattr(self.window, "update_controller", None)
        result = update_controller.latest_result() if update_controller is not None else None
        if result is not None and getattr(result, "update_available", False):
            if hasattr(home, "set_update_available"):
                home.set_update_available(result)
        if hasattr(settings, "set_update_error"):
            settings.set_update_error(message)

    def _on_update_download_completed(self, path: str) -> None:
        settings = self.window.page("settings")
        if hasattr(settings, "set_update_launching"):
            settings.set_update_launching(path)

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        if opened:
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(500, app.quit)
        elif hasattr(settings, "set_update_error"):
            settings.set_update_error(f"Could not open update installer: {path}")
