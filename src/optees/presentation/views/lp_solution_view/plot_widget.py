# src/optees/presentation/views/lp_solution_view/plot_widget.py
from __future__ import annotations
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # type: ignore
from matplotlib.figure import Figure  # type: ignore

from optees.core.string_manager import strings as S
from optees.core.theme import theme



class PlotWidget(QWidget):
    """
    A small panel that renders a bar chart of variable values if matplotlib is
    available; otherwise it shows a friendly placeholder.

    Expected input dictionary via `set_result(...)`:
      {
        "status": str,
        "objective": float | None,
        "values": { var_name: value, ... },   # preferred
        "x": { var_name: value, ... },        # legacy fallback
        "extras": { ... }
      }
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._result: Optional[Dict[str, Any]] = None

        # ---- Layout skeleton -------------------------------------------------
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(6)

        # Title
        self._title = QLabel(S.t("lp.sol.plot.title"))
        self._title.setStyleSheet("font-weight: 700;")
        self._root.addWidget(self._title)

        # Placeholder by default; swapped out if matplotlib is available
        self._placeholder = QLabel(S.t("lp.sol.plot.placeholder"))
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setMinimumHeight(180)
        self._placeholder.setObjectName("plotPlaceholder")  # <-- used by tests
        self._root.addWidget(self._placeholder, 1)

        # ---- Try to attach a Matplotlib canvas -------------------------------
        self._matplotlib_ok = False
        self._canvas = None
        self._fig = None
        self._ax = None

        try:
            self._fig = Figure(figsize=(4, 2.2))
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvasQTAgg(self._fig)
            self._canvas.setObjectName("plotCanvas")

            # Add canvas but don't replace placeholder 
            self._root.addWidget(self._canvas, 1)
            self._canvas.setVisible(False)
            self._matplotlib_ok = True

        except Exception:
            # No matplotlib: keep placeholder in place
            self._matplotlib_ok = False

        # Apply theme now to avoid flicker on first paint
        self.refresh_theme()

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def set_result(self, result: Dict[str, Any]) -> None:
        """Accept a solution result dict and repaint the chart/placeholder."""
        self._result = result or {}
        self._repaint()

    def refresh_strings(self) -> None:
        """Refresh localized strings after language change."""
        self._title.setText(S.t("lp.sol.plot.title"))
        if not self._matplotlib_ok and self._placeholder:
            self._placeholder.setText(S.t("lp.sol.plot.placeholder"))

    def refresh_theme(self) -> None:
        """Apply theme styles (text color, etc.)."""
        fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        self._title.setStyleSheet(f"font-weight:700; color:{fg};")
        self._repaint()

    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------
    def _repaint(self) -> None:
        """(Re)draw the chart or update the placeholder."""
        status = (self._result or {}).get("status", "NotSolved")

        if not self._matplotlib_ok or self._ax is None or self._fig is None:
            if self._placeholder:
                self._placeholder.setVisible(True)
            return

        vals_map = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        names = list(vals_map.keys())
        try:
            vals = [float(v) for v in vals_map.values()]
        except Exception:
            names, vals = [], []

        #  If not solved or no data, show placeholder
        if status == "NotSolved" or not names:
            if self._canvas:
                self._canvas.setVisible(False)
            if self._placeholder:
                self._placeholder.setVisible(True)
            if names and self._matplotlib_ok:
                pass
            return

        self._ax.clear()

        if names:
            self._ax.bar(names, vals)
            self._ax.set_xlabel(S.t("lp.sol.plot.x_label"))
            self._ax.set_ylabel(S.t("lp.sol.plot.y_label"))
            self._ax.tick_params(axis='x', rotation=0)
        else:
            self._ax.text(
                0.5, 0.5, S.t("lp.sol.plot.no_data"),
                ha='center', va='center', transform=self._ax.transAxes
            )

        self._fig.tight_layout()

        if self._canvas:
            self._canvas.draw()
            self._canvas.setVisible(True)
        if self._placeholder:
            self._placeholder.setVisible(False)
