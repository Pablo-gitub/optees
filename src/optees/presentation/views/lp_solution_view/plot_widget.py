# src/optees/presentation/views/lp_solution_view/plot_widget.py
from __future__ import annotations
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # type: ignore
from matplotlib.figure import Figure  # type: ignore

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.core import charts



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
        self._ctx_names = []
        self._ctx_labels = []

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

    def set_context(self, ctx: Dict[str, Any]) -> None:
        """Receive names/labels to label the bars correctly."""
        self._ctx_names = ctx.get("names", []) or []
        self._ctx_labels = ctx.get("labels", []) or []
    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------
    def _repaint(self) -> None:
        """(Re)draw the chart or update the placeholder."""
        status = (self._result or {}).get("status", "NotSolved")

        # If matplotlib is not available, keep the placeholder visible
        if not self._matplotlib_ok or self._ax is None or self._fig is None:
            if self._placeholder:
                self._placeholder.setVisible(True)
            return

        # Build values map and choose order from context if available
        vals_map = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        names = list(self._ctx_names) if self._ctx_names else list(vals_map.keys())

        # Early exit: not solved or no variables
        if status == "NotSolved" or not names:
            if self._canvas:
                self._canvas.setVisible(False)
            if self._placeholder:
                self._placeholder.setVisible(True)
            return

        # Extract numeric values in the chosen order (fallback to 0.0)
        vals = []
        for n in names:
            v = vals_map.get(n, 0.0)
            try:
                vals.append(float(v))
            except Exception:
                vals.append(0.0)

        # Human-facing X labels (prefer context labels)
        x_labels = list(self._ctx_labels) if (self._ctx_labels and len(self._ctx_labels) == len(names)) else names

        # Draw
        t = charts.current()
        self._ax.clear()
        xs = list(range(len(names)))
        self._ax.bar(xs, vals, color=charts.to_mpl(t.accent))
        self._ax.set_xticks(xs)
        self._ax.set_xticklabels(x_labels)
        self._ax.set_xlabel(S.t("lp.sol.plot.x_label"))
        self._ax.set_ylabel(S.t("lp.sol.plot.y_label"))
        self._ax.tick_params(axis='x', rotation=0)
        charts.style_axes(self._fig, self._ax)

        # Optional: keep Y axis starting at 0 for readability
        try:
            ymin, ymax = self._ax.get_ylim()
            self._ax.set_ylim(bottom=0, top=max(ymax, 1.0))
        except Exception:
            pass

        self._fig.tight_layout()

        if self._canvas:
            self._canvas.draw()
            self._canvas.setVisible(True)
        if self._placeholder:
            self._placeholder.setVisible(False)
