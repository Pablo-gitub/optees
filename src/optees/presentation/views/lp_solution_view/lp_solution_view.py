# src/optees/presentation/views/lp_solution_view/lp_solution_view.py
from __future__ import annotations
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton,
    QStyle, QSizePolicy, QLayout, QFileDialog,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.views.lp_solution_view.status_card import StatusCard
from optees.presentation.views.lp_solution_view.solution_table import SolutionTable
from optees.presentation.views.lp_solution_view.plot_widget import PlotWidget
from optees.presentation.views.widgets.stretch_flow_layout import StretchFlowLayout
from optees.presentation.views.lp_solution_view.feasible_region_widget import FeasibleRegionWidget
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

        # Make the scrolled page prefer its minimum size so vertical scrollbars appear
        page.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # Let the layout advertise its minimum size to the scroll area
        root.setSizeConstraint(QLayout.SetMinimumSize)

        # === Header: Back button ======================================
        # Header row with a Back button (icon + text)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(8)

        self.btn_back = QPushButton()
        self.btn_back.setObjectName("btnBack")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setFlat(True)  # looks like a toolbar button
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)

        hdr.addWidget(self.btn_back)
        hdr.addStretch(1)
        root.addLayout(hdr)

        # === Section 1: Hero / StatusCard =============================
        self._status = StatusCard()
        root.addWidget(self._status)

        # === Section 2: Table + Plot side by side =====================
        wrap = StretchFlowLayout(hspacing=16, vspacing=16)

        self._tbl = SolutionTable()
        self._plot = PlotWidget()

        # size policies: allow both to expand when there is room
        self._tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # width minima: comode per il wrapping 2-up → 1-up
        self._tbl.setMinimumWidth(380)
        self._plot.setMinimumWidth(380)

        # height minima: più alte per leggibilità (soprattutto la tabella)
        self._tbl.setMinimumHeight(340)
        self._plot.setMinimumHeight(260)

        wrap.addWidget(self._tbl)
        wrap.addWidget(self._plot)
        root.addLayout(wrap)

        # === Section 2.5: Feasible Region Plot ==========================
        # Feasible region (only shown meaningfully for 2 variables)
        self._feasible = FeasibleRegionWidget()
        root.addWidget(self._feasible)

        # === Section 3: Footer actions ================================
        footer = QHBoxLayout()
        self.btn_copy = QPushButton(S.t("lp.sol.copy_report"))
        self.btn_export_csv = QPushButton(S.t("lp.sol.export_csv"))
        self.btn_export_json = QPushButton(S.t("lp.sol.export_json"))

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
        # raw domain model — used for JSON export
        self._lp_model: Optional[LPModel] = None
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
        self._lp_model = model
        """Provide full problem context to children (names, *display* labels, coefs, offset, bounds, constraints)."""
        try:
            vars_ = list(getattr(model, "variables", []))

            # Internal names (keys used in solution map) and display labels (what user typed).
            names = [getattr(v, "name", f"X{i+1}") for i, v in enumerate(vars_)]
            labels = [getattr(v, "label", None) or getattr(v, "name", f"X{i+1}") for i, v in enumerate(vars_)]
            n = len(names)

            # Objective coefs + offset
            coefs_raw = getattr(getattr(model, "objective", None), "coefs", None)
            coefs = self._coefs_to_list(coefs_raw, n)
            offset = float(getattr(getattr(model, "objective", None), "offset", 0.0) or 0.0)

            # Bounds as (lb, ub)
            bounds = []
            for v in vars_:
                b = getattr(v, "bounds", None)
                bounds.append((getattr(b, "lb", None), getattr(b, "ub", None)))

            # Constraints as ([a_i], rel_str, rhs)
            constraints = []
            for c in getattr(model, "constraints", []) or []:
                a_list = self._coefs_to_list(getattr(c, "coefs", None), n)
                rel = getattr(getattr(c, "relation", None), "symbol", lambda: None)() or "<="
                rhs = getattr(c, "rhs", None)
                constraints.append((a_list, rel, rhs))

            # Sense
            sense = getattr(getattr(model, "objective", None), "sense", None)
            sense_name = (getattr(sense, "name", None) or str(sense or "max")).lower()
            if sense_name not in ("min", "max"):
                sense_name = "max"

        except Exception:
            names, labels, coefs, offset, bounds, constraints, sense_name = [], [], [], 0.0, [], [], "max"

        # Save and broadcast context (now includes 'labels')
        self._problem_ctx = {
            "names": names,          # internal keys
            "labels": labels,        # user-facing labels
            "coefs": coefs,
            "offset": offset,
            "bounds": bounds,
            "constraints": constraints,
            "sense": sense_name,
        }

        if hasattr(self._tbl, "set_context"):
            self._tbl.set_context(self._problem_ctx)
        if hasattr(self._plot, "set_context"):
            self._plot.set_context(self._problem_ctx)
        if hasattr(self, "_feasible") and hasattr(self._feasible, "set_context"):
            self._feasible.set_context(self._problem_ctx)

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
        status_obj = getattr(sol, "status", "NotSolved")
        status = getattr(status_obj, "value", status_obj)
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
        # Feasible region widget also needs the solution (to mark the optimal point)
        if hasattr(self, "_feasible") and hasattr(self._feasible, "set_solution"):
            self._feasible.set_solution(self._result)

    def refresh_strings(self) -> None:
        """Refreshes all localized texts."""
        self.btn_back.setText(S.t("lp.sol.back"))
        self.btn_copy.setText(S.t("lp.sol.copy_report"))
        self.btn_export_csv.setText(S.t("lp.sol.export_csv"))
        self.btn_export_json.setText(S.t("lp.sol.export_json"))
        self._status.refresh_strings()
        self._tbl.refresh_strings()
        self._plot.refresh_strings()
        self._feasible.refresh_strings()

    def refresh_theme(self) -> None:
        """Propagates theme change to child widgets."""
        self._status.refresh_theme()
        self._tbl.refresh_theme()
        self._plot.refresh_theme()
        self._feasible.refresh_theme()

    # ------------------------------------------------------------------
    # Actions (currently no-op, to be implemented later)
    # ------------------------------------------------------------------
    def _copy_report(self) -> None:
        """Copy a plain-text summary of the solution to the clipboard."""
        if not self._result or not self._problem_ctx:
            return
        lines: list[str] = []
        sense = self._problem_ctx.get("sense", "max").upper()
        lines.append(f"Status:    {self._result.get('status', '')}")
        lines.append(f"Objective: {sense}  z = {self._result.get('objective', '')}")
        lines.append("")
        names  = self._problem_ctx.get("names", [])
        values = self._result.get("values", {})
        coefs  = self._problem_ctx.get("coefs", [])
        for i, name in enumerate(names):
            val  = values.get(name, "")
            coef = coefs[i] if i < len(coefs) else ""
            lines.append(f"  {name}: {val}  (coef: {coef})")
        offset = self._problem_ctx.get("offset", 0.0)
        if offset:
            lines.append(f"  offset: {offset}")
        QGuiApplication.clipboard().setText("\n".join(lines))

    def _export_csv(self) -> None:
        """Export variable values to CSV."""
        if not self._result or not self._problem_ctx:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, S.t("lp.sol.export_csv"), "solution.csv",
            "CSV (*.csv);;All files (*)",
        )
        if not path:
            return
        import csv, io
        names  = self._problem_ctx.get("names", [])
        labels = self._problem_ctx.get("labels", names)
        coefs  = self._problem_ctx.get("coefs", [])
        values = self._result.get("values", {})
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["variable", "label", "coefficient", "value"])
        for i, name in enumerate(names):
            writer.writerow([
                name,
                labels[i] if i < len(labels) else "",
                coefs[i]  if i < len(coefs)  else "",
                values.get(name, ""),
            ])
        from pathlib import Path
        Path(path).write_text(buf.getvalue(), encoding="utf-8")

    def _export_json(self) -> None:
        """Export the problem (importable schema v1) + solution to JSON."""
        if self._lp_model is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, S.t("lp.sol.export_json"), "problem.json",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        if _looks_like_milp_model(self._lp_model):
            from optees.utility.milp_json_io import milp_model_to_file

            milp_model_to_file(self._lp_model, path)
        else:
            from optees.utility.lp_json_io import lp_model_to_file

            lp_model_to_file(self._lp_model, path)


def _looks_like_milp_model(model: object) -> bool:
    variables = getattr(model, "variables", None) or []
    return any(hasattr(v, "integrality") for v in variables)
