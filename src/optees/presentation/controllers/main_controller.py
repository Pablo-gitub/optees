# src/optees/presentation/controllers/main_controller.py
from __future__ import annotations
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from optees.presentation.main_window import MainWindow

from optees.presentation.views.lp_view.lp_view import LPView
from optees.presentation.error_feedback import localized_error_detail
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView
from optees.presentation.views.nlp_view import NLPView
from optees.presentation.views.graph_view import GraphView
from optees.presentation.views.packing_view import PackingView
from optees.presentation.views.regression_view import RegressionView
from optees.presentation.views.classification_view import ClassificationView
from optees.presentation.views.home_view import HomePage  # usa lo stesso nome che usi nel MainWindow
from optees.core.string_manager import strings as S
from optees.domain.entities.update import UpdateExecutionState
from optees.utility.knapsack_json_io import knapsack_problem_from_dict
from optees.utility.lp_json_io import lp_model_from_dict
from optees.utility.milp_json_io import milp_model_from_dict
from optees.utility.regression_json_io import regression_model_from_dict
from optees.utility.classification_json_io import classification_model_from_dict
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
        if hasattr(home, "go_nlp"):
            home.go_nlp.connect(lambda: self.window.goto("nlp"))
        if hasattr(home, "go_graph"):
            home.go_graph.connect(lambda: self.window.goto("graph"))
        if hasattr(home, "go_packing"):
            home.go_packing.connect(lambda: self.window.goto("packing"))
        if hasattr(home, "go_regression"):
            home.go_regression.connect(lambda: self.window.goto("regression"))
        if hasattr(home, "go_classification"):
            home.go_classification.connect(lambda: self.window.goto("classification"))
        if hasattr(home, "go_forecasting"):
            home.go_forecasting.connect(lambda: self.window.goto("forecasting"))

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

        # NLP -> local numerical result
        nlp: NLPView = self.window.page("nlp")  # type: ignore[assignment]
        nlp.solve_completed.connect(self._on_nlp_solved)
        nlp.example_requested.connect(lambda: self.window.goto("nlp_example"))
        nlp.problem_description_requested.connect(lambda: self.window.goto("nlp_problem"))
        for name in ("nlp_example", "nlp_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("nlp"))
        nlp_solution = self.window.page("nlp_solution")
        if hasattr(nlp_solution, "back_requested"):
            nlp_solution.back_requested.connect(lambda: self.window.goto("nlp"))

        # Graph Theory -> Dijkstra result
        graph: GraphView = self.window.page("graph")  # type: ignore[assignment]
        graph.solve_completed.connect(self._on_graph_solved)
        graph.example_requested.connect(lambda: self.window.goto("graph_example"))
        graph.problem_description_requested.connect(lambda: self.window.goto("graph_problem"))
        for name in ("graph_example", "graph_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("graph"))
        graph_solution = self.window.page("graph_solution")
        if hasattr(graph_solution, "back_requested"):
            graph_solution.back_requested.connect(lambda: self.window.goto("graph"))

        # Packing & Loading -> exact orthogonal 3D result
        packing: PackingView = self.window.page("packing")  # type: ignore[assignment]
        packing.solve_completed.connect(self._on_packing_solved)
        packing.example_requested.connect(lambda: self.window.goto("packing_example"))
        packing.problem_description_requested.connect(lambda: self.window.goto("packing_problem"))
        for name in ("packing_example", "packing_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("packing"))
        packing_solution = self.window.page("packing_solution")
        if hasattr(packing_solution, "back_requested"):
            packing_solution.back_requested.connect(lambda: self.window.goto("packing"))

        # AI & Machine Learning -> regression result
        regression: RegressionView = self.window.page("regression")  # type: ignore[assignment]
        regression.solve_completed.connect(self._on_regression_trained)
        regression.example_requested.connect(lambda: self.window.goto("regression_example"))
        regression.problem_description_requested.connect(lambda: self.window.goto("regression_problem"))
        for name in ("regression_example", "regression_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("regression"))
        regression_solution = self.window.page("regression_solution")
        if hasattr(regression_solution, "back_requested"):
            regression_solution.back_requested.connect(lambda: self.window.goto("regression"))

        classification: ClassificationView = self.window.page("classification")  # type: ignore[assignment]
        classification.solve_completed.connect(self._on_classification_trained)
        classification.example_requested.connect(lambda: self.window.goto("classification_example"))
        classification.problem_description_requested.connect(lambda: self.window.goto("classification_problem"))
        for name in ("classification_example", "classification_problem"):
            info_view = self.window.page(name)
            if hasattr(info_view, "back_requested"):
                info_view.back_requested.connect(lambda _=False: self.window.goto("classification"))
        classification_solution = self.window.page("classification_solution")
        if hasattr(classification_solution, "back_requested"):
            classification_solution.back_requested.connect(lambda: self.window.goto("classification"))

        forecasting = self.window.page("forecasting")
        if hasattr(forecasting, "solve_completed"):
            forecasting.solve_completed.connect(self._on_forecasting_completed)
        forecasting_solution = self.window.page("forecasting_solution")
        if hasattr(forecasting_solution, "back_requested"):
            forecasting_solution.back_requested.connect(
                lambda: self.window.goto("forecasting")
            )

        assistant = self.window.page("assistant")
        if hasattr(assistant, "back_requested"):
            assistant.back_requested.connect(lambda: self.window.goto("home"))
        if hasattr(assistant, "load_lp_requested"):
            assistant.load_lp_requested.connect(self._load_assistant_lp_model)
        if hasattr(assistant, "load_milp_requested"):
            assistant.load_milp_requested.connect(self._load_assistant_milp_model)
        if hasattr(assistant, "load_knapsack_requested"):
            assistant.load_knapsack_requested.connect(self._load_assistant_knapsack_problem)
        if hasattr(assistant, "load_regression_requested"):
            assistant.load_regression_requested.connect(self._load_assistant_regression_model)
        if hasattr(assistant, "load_classification_requested"):
            assistant.load_classification_requested.connect(self._load_assistant_classification_model)

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

    def _on_nlp_solved(self, solution) -> None:
        sol_view = self.window.page("nlp_solution")
        try:
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(self.window.nlp_page.current_model())  # type: ignore[attr-defined]
        except Exception:
            pass
        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]
        try:
            log.debug(
                "NLP result received: status=%s objective=%s",
                getattr(solution, "status", None),
                getattr(solution, "objective", None),
            )
        except Exception:
            pass
        self.window.goto("nlp_solution")

    def _on_graph_solved(self, solution) -> None:
        sol_view = self.window.page("graph_solution")
        try:
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(self.window.graph_page.current_model())  # type: ignore[attr-defined]
        except Exception:
            pass
        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]
        self.window.goto("graph_solution")

    def _on_packing_solved(self, solution) -> None:
        sol_view = self.window.page("packing_solution")
        try:
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(self.window.packing_page.current_model())  # type: ignore[attr-defined]
        except Exception:
            pass
        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]
        self.window.goto("packing_solution")

    def _on_regression_trained(self, solution) -> None:
        sol_view = self.window.page("regression_solution")
        try:
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(self.window.regression_page.current_model())  # type: ignore[attr-defined]
        except Exception:
            pass
        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]
        self.window.goto("regression_solution")

    def _on_classification_trained(self, solution) -> None:
        sol_view = self.window.page("classification_solution")
        try:
            if hasattr(sol_view, "set_problem"):
                sol_view.set_problem(self.window.classification_page.current_model())  # type: ignore[attr-defined]
        except Exception:
            pass
        if hasattr(sol_view, "set_solution"):
            sol_view.set_solution(solution)  # type: ignore[attr-defined]
        self.window.goto("classification_solution")

    def _on_forecasting_completed(self, solution) -> None:
        solution_view = self.window.page("forecasting_solution")
        try:
            if hasattr(solution_view, "set_problem"):
                solution_view.set_problem(
                    self.window.forecasting_page.current_model()
                )
        except Exception:
            pass
        if hasattr(solution_view, "set_solution"):
            solution_view.set_solution(solution)
        self.window.goto("forecasting_solution")

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

    def _load_assistant_regression_model(self, data: object) -> None:
        try:
            model = regression_model_from_dict(dict(data))  # type: ignore[arg-type]
            self.window.regression_page.set_model(model)
            self.window.goto("regression")
        except Exception as exc:
            self._show_assistant_load_error(exc)

    def _load_assistant_classification_model(self, data: object) -> None:
        try:
            model = classification_model_from_dict(dict(data))  # type: ignore[arg-type]
            self.window.classification_page.set_model(model)
            self.window.goto("classification")
        except Exception as exc:
            self._show_assistant_load_error(exc)

    def _show_assistant_load_error(self, exc: Exception) -> None:
        QMessageBox.warning(
            self.window,
            S.t("assistant.import_error.title"),
            S.t("assistant.import_error.body", detail=localized_error_detail("assistant_import", exc)),
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
        update_controller.execution_state_changed.connect(self._on_update_execution_state)
        update_controller.download_progress.connect(self._on_update_download_progress)
        update_controller.handoff_completed.connect(self._on_update_handoff_completed)
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

    def _on_update_execution_state(self, snapshot) -> None:
        settings = self.window.page("settings")
        state = getattr(snapshot, "state", None)
        if state is UpdateExecutionState.DOWNLOADED and hasattr(
            settings, "set_update_downloaded"
        ):
            settings.set_update_downloaded(getattr(snapshot, "local_path", ""))
        elif state is UpdateExecutionState.VERIFICATION_FAILED and hasattr(
            settings, "set_update_verification_failed"
        ):
            settings.set_update_verification_failed(getattr(snapshot, "message", ""))
        elif state is UpdateExecutionState.MANUAL_ACTION_REQUIRED and hasattr(
            settings, "set_update_manual_action_required"
        ):
            settings.set_update_manual_action_required(
                getattr(snapshot, "local_path", "")
            )

    def _on_update_download_progress(self, downloaded: int, total: int) -> None:
        home = self.window.page("home")
        settings = self.window.page("settings")
        if hasattr(home, "set_update_download_progress"):
            home.set_update_download_progress(downloaded, total)
        if hasattr(settings, "set_update_download_progress"):
            settings.set_update_download_progress(downloaded, total)

    def _on_update_handoff_completed(self, outcome) -> None:
        settings = self.window.page("settings")
        state = getattr(outcome, "state", None)
        if state is UpdateExecutionState.MANUAL_ACTION_REQUIRED and hasattr(
            settings, "set_update_manual_action_required"
        ):
            settings.set_update_manual_action_required(
                getattr(outcome, "local_path", "")
            )
        elif hasattr(settings, "set_update_launching"):
            settings.set_update_launching(getattr(outcome, "local_path", ""))

        if getattr(outcome, "started", False):
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(500, app.quit)
