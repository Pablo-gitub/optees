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
        # Detailed formula line (e.g., "z = 2 × 3 + 1 × 2 = 8")
        self._formula_detail = QLabel("")
        self._formula_detail.setWordWrap(True)
        root.addWidget(self._formula_detail)
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
        self._meta.setStyleSheet(f"color: {base_fg};")
        self._formula_detail.setStyleSheet(f"color: {base_fg};")
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
            obj_f = None
        else:
            try:
                obj_f = float(obj)
                obj_text = f"{S.t('lp.sol.objective')}: <span style='font-weight:800;'>{obj_f:.6g}</span>"
            except Exception:
                obj_f = None
                obj_text = f"{S.t('lp.sol.objective')}: <span style='font-weight:800;'>{obj}</span>"
        self._objective.setText(obj_text)

        # --- Formula hint (if possible) -------------------------------
        # Formula hint + consistency check: z ?= Σ (cᵢ·xᵢ) + offset
        values = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        coefs = (self._result or {}).get("coefs", None)  # injected via LPSolutionView.set_result merge
        offset = float((self._result or {}).get("offset", 0.0) or 0.0)

        def _to_float(x):
            try: 
                return float(x)
            except Exception: 
                return None

        # compute Σ cᵢ·xᵢ only if we have coefs + matching names
        names = list(values.keys())
        subtotal_sum = None
        if isinstance(coefs, (list, tuple)) and len(coefs) >= len(names):
            subtotal_sum = 0.0
            for i, name in enumerate(names):
                xi = _to_float(values.get(name))
                ci = _to_float(coefs[i])
                if xi is None or ci is None:
                    subtotal_sum = None
                    break
                subtotal_sum += xi * ci

        # build meta line(s)
        method = extras.get("method", "highs")
        nit = extras.get("nit", None)
        msg = extras.get("message", None)

        bits = [f"{S.t('lp.sol.method')}: {method}"]
        if nit is not None:
            bits.append(f"{S.t('lp.sol.iterations')}: {nit}")
        if msg:
            bits.append(f"{S.t('lp.sol.msg')}: {msg}")

        # Show compact formula hint
        bits.append(S.t("lp.sol.formula_hint"))

        # Consistency check (✓ if objective ≈ Σ cᵢ·xᵢ + offset)
        if subtotal_sum is not None:
            total_calc = subtotal_sum + offset
            if obj_f is not None:
                diff = abs(total_calc - obj_f)
                if diff <= 1e-6:
                    bits.append(f"✓ {S.t('lp.sol.check.ok')}")
                else:
                    # show warning with both numbers for didactic clarity
                    bits.append(f"⚠ {S.t('lp.sol.check.mismatch', calc=f'{total_calc:.6g}', obj=f'{obj_f:.6g}')}")
            else:
                bits.append(f"• {S.t('lp.sol.check.calc', calc=f'{total_calc:.6g}')}")
        self._meta.setText('  •  '.join(bits))

        # Build expanded equation like: z = 2 × 3 + 1 × 2 (+ 0.5) = 8.5
        def _fmt(x):
            try:
                return f"{float(x):.6g}"
            except Exception:
                return "—"

        detail_line = ""
        if subtotal_sum is not None:
            # Recompute detailed terms in the same order (names list)
            detailed_terms = []
            for i, name in enumerate(names):
                xi = _to_float(values.get(name))
                ci = _to_float(coefs[i]) if isinstance(coefs, (list, tuple)) and i < len(coefs) else None
                if xi is None or ci is None:
                    detailed_terms = []
                    break
                detailed_terms.append(f"{_fmt(xi)} × {_fmt(ci)}")

            if detailed_terms:
                total_calc = subtotal_sum + offset
                # Append offset if nonzero (within a small tolerance)
                if abs(offset) > 1e-12:
                    detailed_terms.append(_fmt(offset))
                detail_line = f"z = {' + '.join(detailed_terms)} = {_fmt(total_calc)}"

        # Show / clear the detail label
        self._formula_detail.setText(detail_line)
