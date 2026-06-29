# src/optees/presentation/views/lp_solution_view/status_card.py
from __future__ import annotations
from typing import Optional, Dict, Any
import math

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from optees.core.string_manager import strings as S
from optees.core.theme import theme

# ----------------------------------------------------------------------
# Color presets for the status badge
# ----------------------------------------------------------------------
_STATUS_COLORS = {
    "Optimal":    {"bg": "rgba(46, 160, 67, 0.12)", "fg": "rgba(46,160,67,0.95)"},   # green
    "Feasible":   {"bg": "rgba(46, 160, 67, 0.10)", "fg": "rgba(46,160,67,0.95)"},   # green
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
        # --- Optimality multiplicity note (unique vs multiple optima) ---
        self._opt_note = QLabel("")            # NEW: short sentence about uniqueness / multiple optima
        self._opt_note.setObjectName("optNote")
        self._opt_note.setWordWrap(True)
        root.addWidget(self._opt_note)
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
        self._meta.setTextFormat(Qt.RichText)
        self._formula_detail.setTextFormat(Qt.RichText)
        self._meta.setStyleSheet(
            f"color: {base_fg}; margin-top: 8px; margin-bottom: 8px; line-height: 160%;"
        )
        self._formula_detail.setStyleSheet(
            f"color: {base_fg}; margin-top: 6px; margin-bottom: 8px; line-height: 160%;"
        )
        self._opt_note.setStyleSheet(
            f"color: {base_fg}; font-weight: 600; margin-top: 8px; line-height: 160%;"
        )
        self._repaint()

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------
    def _repaint(self) -> None:
        """
        Internal helper: refresh displayed values according to _result.
        Safe to call multiple times.
        """
        st_obj = (self._result or {}).get("status", "NotSolved")
        st = getattr(st_obj, "value", st_obj)
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
            "Feasible": S.t("lp.sol.status.feasible"),
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

        # --- Multiplicity of the optimal solution (unique vs multiple) ---
        # extras["alt_opt"]["ranges"] contains the mathematically meaningful
        # result: for each variable x_i, min/max values over the optimal face
        # F* = {x feasible | c^T x = z*}.  Positive width means x_i can move
        # while preserving the same optimal objective value.
        def _fmt_point_from_mapping(m: Dict[str, Any]) -> str:
            """
            Render a compact [x1, x2, ...] using the variable order from extras['var_names']
            if available. Falls back to the mapping's iteration order.
            """
            var_order = extras.get("var_names")
            try:
                if isinstance(var_order, (list, tuple)):
                    vals = []
                    for name in var_order:
                        if name in m:
                            vals.append(float(m[name]))
                        else:
                            # missing -> show as placeholder
                            vals.append(float("nan"))
                    s = "[" + ", ".join(f"{v:.6g}" for v in vals) + "]"
                else:
                    vals = [float(v) for v in m.values()]
                    s = "[" + ", ".join(f"{v:.6g}" for v in vals) + "]"
                # Compact if too long (e.g., high dimension)
                if len(vals) > 6:
                    s = "[" + ", ".join(f"{vals[i]:.6g}" for i in range(3)) + ", …, " + \
                        ", ".join(f"{vals[-2+i]:.6g}" for i in range(2)) + "]"
                return s
            except Exception:
                parts = []
                order_items = ((k, m[k]) for k in var_order if k in m) if isinstance(var_order, (list, tuple)) else m.items()
                for k, v in order_items:
                    try:
                        parts.append(f"{k}:{float(v):.6g}")
                    except Exception:
                        parts.append(f"{k}:{v}")
                return "{ " + ", ".join(parts) + " }"

        def _fmt_range_value(v: Any) -> str:
            try:
                vf = float(v)
            except Exception:
                return "?"
            if math.isinf(vf):
                return "inf" if vf > 0 else "-inf"
            return f"{vf:.6g}"

        def _fmt_ranges(ranges: Dict[str, Any]) -> str:
            if not isinstance(ranges, dict) or not ranges:
                return ""
            var_order = extras.get("var_names")
            names_for_ranges = list(var_order) if isinstance(var_order, (list, tuple)) else list(ranges.keys())
            parts = []
            for name in names_for_ranges:
                info = ranges.get(name)
                if not isinstance(info, dict):
                    continue
                lo = info.get("min")
                hi = info.get("max")
                if lo is None or hi is None:
                    continue
                parts.append(f"{name} in [{_fmt_range_value(lo)}, {_fmt_range_value(hi)}]")
                if len(parts) >= 4:
                    break
            if not parts:
                return ""
            remaining = max(0, len(ranges) - len(parts))
            suffix = "" if remaining == 0 else f", +{remaining}"
            return "; ".join(parts) + suffix


        alt = extras.get("alt_opt") or {}
        has_alt = bool(alt.get("has_alternate_optimum", False))
        ranges_text = _fmt_ranges(alt.get("ranges") or {})
        A_map = (alt.get("extreme_points") or {}).get("A")
        B_map = (alt.get("extreme_points") or {}).get("B")

        # Only show this note for Optimal problems
        if st == "Optimal":
            if alt.get("range_skipped"):
                self._opt_note.setText(S.t("lp.sol.opt.not_computed"))
            elif has_alt:
                if ranges_text:
                    self._opt_note.setText(S.t("lp.sol.opt.range", ranges=ranges_text))
                elif isinstance(A_map, dict) and isinstance(B_map, dict):
                    A_str = _fmt_point_from_mapping(A_map)
                    B_str = _fmt_point_from_mapping(B_map)
                    self._opt_note.setText(S.t('lp.sol.opt.segment', A=A_str, B=B_str))
                else:
                    self._opt_note.setText(S.t('lp.sol.opt.multiple'))
            else:
                self._opt_note.setText(S.t('lp.sol.opt.unique'))
        else:
            # For non-optimal statuses, hide/clear the note
            self._opt_note.setText("")


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

        bits = [f"{S.t('lp.sol.method')}: {method}"]
        if nit is not None:
            bits.append(f"{S.t('lp.sol.iterations')}: {nit}")
        
        # Optional: add a short meta chip for multiple optima
        if st == "Optimal" and has_alt:
            varying = alt.get("varying_variables") or alt.get("zero_reduced_cost_vars") or []
            if varying:
                vars_str = ", ".join(map(str, varying[:4]))
                tail = "" if len(varying) <= 4 else "…"
                bits.append(S.t("lp.sol.opt.varying", vars=f"{vars_str}{tail}"))

        # Show compact formula hint
        bits.append(S.t("lp.sol.formula_hint"))
        # render meta on multiple lines
        self._meta.setText("<br/>".join(bits))
        # Build expanded equation like: z = 2 × 3 + 1 × 2 (+ 0.5) = 8.5
        def _fmt(x):
            try:
                return f"{float(x):.6g}"
            except Exception:
                return "—"

        detail_line = ""
        coherence_line = ""  # appended below the numeric formula if we can check it

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
                if abs(offset) > 1e-12:
                    detailed_terms.append(_fmt(offset))
                detail_line = f"z = {' + '.join(detailed_terms)} = {_fmt(total_calc)}"

                # Consistency check shown right under the numeric formula
                if obj_f is not None:
                    diff = abs(total_calc - obj_f)
                    if diff <= 1e-6:
                        coherence_line = f"<br/>✓ {S.t('lp.sol.check.ok')}"
                    else:
                        coherence_line = f"<br/>⚠ {S.t('lp.sol.check.mismatch', calc=f'{total_calc:.6g}', obj=f'{obj_f:.6g}')}"

        # Render numeric formula (+ optional coherence line)
        self._formula_detail.setText(detail_line + coherence_line)
