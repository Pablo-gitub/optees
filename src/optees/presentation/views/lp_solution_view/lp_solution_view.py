# src/optees/presentation/views/lp_solution_view/lp_solution_view.py
from __future__ import annotations
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.views.lp_solution_view.status_card import StatusCard
from optees.presentation.views.lp_solution_view.solution_table import SolutionTable
from optees.presentation.views.lp_solution_view.plot_widget import PlotWidget
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.models.lp.lp_model import LPModel
import logging
log = logging.getLogger(__name__)

class LPSolutionView(QWidget):
    """
    View responsible for displaying the results of an LP solve.

    Components:
      • StatusCard  → shows status, objective value, and metadata
      • SolutionTable → shows variable values
      • PlotWidget   → optional bar plot / placeholder
      • Footer with action buttons (Back / Copy / Export)

    Signals:
      • back_requested → emitted when user clicks the "Back" button
    """

    back_requested = Signal()

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # === Layout: scrollable page ==================================
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop)
        outer.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        # === Section 1: Hero / StatusCard =============================
        self._status = StatusCard()
        root.addWidget(self._status)

        # === Section 2: Table + Plot side by side =====================
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        self._tbl = SolutionTable()
        self._plot = PlotWidget()

        row.addWidget(self._tbl, 1)
        row.addWidget(self._plot, 1)
        root.addLayout(row)

        # === Section 3: Footer actions ================================
        footer = QHBoxLayout()
        self.btn_back = QPushButton(S.t("lp.sol.back"))
        self.btn_copy = QPushButton(S.t("lp.sol.copy_report"))
        self.btn_export_csv = QPushButton(S.t("lp.sol.export_csv"))
        self.btn_export_json = QPushButton(S.t("lp.sol.export_json"))

        self.btn_back.clicked.connect(self.back_requested.emit)

        footer.addWidget(self.btn_back)
        footer.addStretch(1)
        footer.addWidget(self.btn_copy)
        footer.addWidget(self.btn_export_csv)
        footer.addWidget(self.btn_export_json)
        root.addLayout(footer)

        # === Public aliases (for tests and controller) ================
        self.solution_table = self._tbl   # used in tests
        self.status = self._status        # used in tests
        self.plot = self._plot            # used in tests

        # === Connections ==============================================
        theme.theme_changed.connect(self.refresh_theme)
        S.language_changed.connect(self.refresh_strings)

        # === Apply initial styling and texts ==========================
        self.refresh_theme()
        self.refresh_strings()

        # === Connect future actions (stubs for now) ===================
        self.btn_copy.clicked.connect(self._copy_report)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_export_json.clicked.connect(self._export_json)

        # keep last shown result (optional)
        self._result: Optional[Dict[str, Any]] = None
        # problem context (names, objective coefficients, offset)
        self._problem_ctx: Dict[str, Any] = {"names": [], "coefs": [], "offset": 0.0}
    # ------------------------------------------------------------------
    # Inner Helpers
    # ------------------------------------------------------------------

    def _extras_to_dict(self, extras_obj) -> dict:
        """Normalize domain diagnostics to a plain dict."""
        if extras_obj is None:
            return {}
        if isinstance(extras_obj, dict):
            return extras_obj
        # prova to_dict
        to_dict = getattr(extras_obj, "to_dict", None)
        if callable(to_dict):
            return to_dict() or {}
        # dataclass / oggetto semplice
        try:
            return dict(extras_obj)
        except Exception:
            pass
        try:
            return {k: getattr(extras_obj, k) for k in dir(extras_obj)
                    if not k.startswith("_") and not callable(getattr(extras_obj, k))}
        except Exception:
            return {}
        
    def _coefs_to_list(self, coefs_obj, n: int) -> list:
        """Normalize objective/constraint coefficients into a length-n list.
        Accepts tuple/list/dict/None from domain. Pads with None if needed.
        """
        if coefs_obj is None:
            return [None] * n
        if isinstance(coefs_obj, dict):
            return [coefs_obj.get(i) for i in range(n)]
        try:
            seq = list(coefs_obj)
        except Exception:
            return [None] * n
        if len(seq) < n:
            seq += [None] * (n - len(seq))
        return seq[:n]
        
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    
    def set_problem(self, model: LPModel) -> None:
        """Provide problem context (variable names, objective coefficients, offset).
        Called by MainController *before* set_solution(...)."""
        try:
            names = [v.name for v in getattr(model, "variables", [])]
            n = len(names)
            coefs_raw = getattr(getattr(model, "objective", None), "coefs", None)
            coefs = self._coefs_to_list(coefs_raw, n)
            offset = float(getattr(getattr(model, "objective", None), "offset", 0.0) or 0.0)
        except Exception:
            names, coefs, offset = [], [], 0.0

        self._problem_ctx = {"names": names, "coefs": coefs, "offset": offset}

        # Pass the context to the table (next patch will add set_context there)
        if hasattr(self._tbl, "set_context"):
            self._tbl.set_context(self._problem_ctx)

        # If we already have a result on screen, refresh StatusCard to include context
        if self._result is not None:
            merged = {**self._result, **self._problem_ctx}
            self._status.set_result(merged)


    def set_solution(self, sol: LPSolution) -> None:
        """
        Entry point called by MainController after solving.

        It safely maps the domain entity (LPSolution) into
        a canonical dict structure expected by the subwidgets.
        """
        # Defensive access: not all fields may exist depending on domain version
        status = getattr(sol, "status", "NotSolved")
        objective = getattr(sol, "objective", None)
        values = getattr(sol, "values", None) or getattr(sol, "x", None) or {}
        extras = self._extras_to_dict(getattr(sol, "extras", None))

        # Debug-friendly log (safe: no shadowing with 'result')
        log.debug("set_solution: status=%s objective=%s values=%s", status, objective, values)

        self.set_result({
            "status": status,
            "objective": objective,
            "values": values,
            "extras": extras,
        })

    def set_result(self, result: Dict[str, Any]) -> None:
        """
        Lower-level method to populate the view using a dict,
        mainly used internally by `set_solution`.
        """
        self._result = result or {}
        # Merge problem context into status so it can show formula hints
        merged = {**self._result, **(self._problem_ctx or {})}
        self._status.set_result(merged)
        self._tbl.set_result(self._result)
        self._plot.set_result(self._result)

    def refresh_strings(self) -> None:
        """Refreshes all localized texts."""
        self.btn_back.setText(S.t("lp.sol.back"))
        self.btn_copy.setText(S.t("lp.sol.copy_report"))
        self.btn_export_csv.setText(S.t("lp.sol.export_csv"))
        self.btn_export_json.setText(S.t("lp.sol.export_json"))
        self._status.refresh_strings()
        self._tbl.refresh_strings()
        self._plot.refresh_strings()

    def refresh_theme(self) -> None:
        """Propagates theme change to child widgets."""
        self._status.refresh_theme()
        self._tbl.refresh_theme()
        self._plot.refresh_theme()

    # ------------------------------------------------------------------
    # Actions (currently no-op, to be implemented later)
    # ------------------------------------------------------------------
    def _copy_report(self) -> None:
        """Copy textual report of the solution to clipboard (TODO)."""
        pass

    def _export_csv(self) -> None:
        """Export variable values to CSV (TODO)."""
        pass

    def _export_json(self) -> None:
        """Export entire solution to JSON (TODO)."""
        pass
