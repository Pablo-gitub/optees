# src/optees/presentation/views/lp_solution_view/status_card.py
from __future__ import annotations
from typing import Optional, Dict, Any

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from optees.core.string_manager import strings as S
from optees.core.theme import theme

# ----------------------------------------------------------------------
# Color presets for the status badge
# ----------------------------------------------------------------------
_STATUS_COLORS = {
    "Optimal":    {"bg": "rgba(46, 160, 67, 0.12)", "fg": "rgba(46,160,67,0.95)"},   # green
    "Infeasible": {"bg": "rgba(255, 0, 0, 0.10)",   "fg": "rgba(220, 53, 69, 0.95)"}, # red
    "Unbounded":  {"bg": "rgba(255, 165, 0, 0.12)", "fg": "rgba(255,140,0,0.95)"},   # orange
    "NotSolved":  {"bg": "rgba(128,128,128,0.10)",  "fg": "rgba(108,117,125,0.95)"}, # gray
}


class StatusCard(QWidget):
    """
    Compact visual component that shows:
      • LP status badge (Optimal / Infeasible / etc.)
      • Objective value (z = ...)
      • Optional metadata (method, iterations, message)

    Public API:
      - set_result(result_dict): populate with a dict
        {status, objective, values, extras}
      - refresh_strings(), refresh_theme(): update text/theme
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._result: Optional[Dict[str, Any]] = None

        # ------------------------------------------------------------------
        # Layout structure
        # ------------------------------------------------------------------
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(6)

        # === Top row: status badge + objective value =====================
        top = QHBoxLayout()
        top.setSpacing(8)

        # Status badge (colored chip)
        self._status_badge = QLabel("—")
        self._status_badge.setObjectName("statusBadge")  # required by tests
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setFixedHeight(28)
        self._status_badge.setStyleSheet("border-radius: 14px; padding: 4px 10px;")

        # Objective value label
        self._objective = QLabel("z = —")
        self._objective.setTextFormat(Qt.RichText)
        self._objective.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        top.addWidget(self._status_badge)
        top.addWidget(self._objective, 1)
        root.addLayout(top)

        # === Metadata line (method, iterations, message) ================
        self._meta = QLabel("")
        self._meta.setObjectName("solverMsg")  # required by tests
        self._meta.setWordWrap(True)
        root.addWidget(self._meta)

        # Initialize look and language
        self.refresh_theme()
        self.refresh_strings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_result(self, result: Dict[str, Any]) -> None:
        """Populate the widget using the given result dictionary."""
        self._result = result or {}
        self._repaint()

    def refresh_strings(self) -> None:
        """Rebuild the textual content using translated labels."""
        self._repaint()

    def refresh_theme(self) -> None:
        """Adjust text and background colors based on current theme."""
        base_fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        self._objective.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {base_fg};")
        self._meta.setStyleSheet(theme.secondary_text_css(self))
        self._repaint()

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------
    def _repaint(self) -> None:
        """
        Internal helper: refresh displayed values according to _result.
        Safe to call multiple times.
        """
        st = (self._result or {}).get("status", "NotSolved")
        obj = (self._result or {}).get("objective", None)
        extras = (self._result or {}).get("extras", {}) or {}

        # --- Ensure extras is a dict --------------------------------------
        if not isinstance(extras, dict):
            try:
                to_dict = getattr(extras, "to_dict", None)
                extras = to_dict() if callable(to_dict) else dict(extras)
            except Exception:
                try:
                    extras = {k: getattr(extras, k) for k in dir(extras)
                            if not k.startswith("_") and not callable(getattr(extras, k))}
                except Exception:
                    extras = {}
        else:
            extras = extras

        # --- Status badge text (localized) ------------------------------
        badge_text = {
            "Optimal": S.t("lp.sol.status.optimal"),
            "Infeasible": S.t("lp.sol.status.infeasible"),
            "Unbounded": S.t("lp.sol.status.unbounded"),
            "NotSolved": S.t("lp.sol.status.notsolved"),
        }.get(st, st)

        # --- Status badge color ----------------------------------------
        colors = _STATUS_COLORS.get(st, _STATUS_COLORS["NotSolved"])
        self._status_badge.setText(badge_text)
        self._status_badge.setStyleSheet(
            f"border-radius: 14px; padding: 4px 10px; "
            f"background: {colors['bg']}; color: {colors['fg']}; font-weight: 600;"
        )

        # --- Objective value -------------------------------------------
        if obj is None:
            obj_text = f"{S.t('lp.sol.objective')}: —"
        else:
            obj_text = f"{S.t('lp.sol.objective')}: <span style='font-weight:800;'>{obj:.6g}</span>"
        self._objective.setText(obj_text)

        # --- Metadata / extras -----------------------------------------
        method = extras.get("method", "highs")
        nit = extras.get("nit", None)
        msg = extras.get("message", None)

        bits = [f"{S.t('lp.sol.method')}: {method}"]
        if nit is not None:
            bits.append(f"{S.t('lp.sol.iterations')}: {nit}")
        if msg:
            bits.append(f"{S.t('lp.sol.msg')}: {msg}")
        self._meta.setText("  •  ".join(bits))
