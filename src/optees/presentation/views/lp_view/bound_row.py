#src/optees/presentation/views/lp_view/bound_row.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)

from PySide6.QtWidgets import QLineEdit, QToolButton

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.core.design import tokens

# ---------------- Row "Xk [name]  🗑︎" ----------------

class BoundRow(QWidget):
    """Row for a single variable: [Xk / label] | [LB] | [UB] | [presets]."""
    lb_changed = Signal(int, object)       # (index, parsed_lb)
    ub_changed = Signal(int, object)       # (index, parsed_ub)
    preset_clicked = Signal(int, str)      # (index, preset)

    def __init__(self, index: int, var_name: str, display_label: str,
                 lb: Optional[float], ub: Optional[float],
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._index = index

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # left label: "Xk" + display label (dimmed)
        self.lbl = QLabel(f"{var_name}")
        self.lbl.setMinimumWidth(48)

        self.sub = QLabel(display_label or "")
        self.sub.setStyleSheet(theme.secondary_text_css(self))

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        left.addWidget(self.lbl)
        left.addWidget(self.sub)

        # LB / UB editors
        self.edit_lb = QLineEdit(self._format_value(lb, is_lb=True))
        self.edit_lb.setPlaceholderText(S.t("lp.bounds.inf.minus"))
        self.edit_lb.setFixedHeight(28)
        self.edit_lb.editingFinished.connect(self._on_lb_commit)

        self.edit_ub = QLineEdit(self._format_value(ub, is_lb=False))
        self.edit_ub.setPlaceholderText(S.t("lp.bounds.inf.plus"))
        self.edit_ub.setFixedHeight(28)
        self.edit_ub.editingFinished.connect(self._on_ub_commit)

        # preset chips
        self.btn_nonneg = QToolButton(); self._setup_chip(self.btn_nonneg, S.t("lp.bounds.presets.nonneg"), "nonneg")
        self.btn_free   = QToolButton(); self._setup_chip(self.btn_free,   S.t("lp.bounds.presets.free"),   "free")
        self.btn_fixed  = QToolButton(); self._setup_chip(self.btn_fixed,  S.t("lp.bounds.presets.fixed"),  "fixed")

        # layout: [label stack] | [LB] | [UB] | [chips...]
        lay.addLayout(left, 1)
        lay.addWidget(self.edit_lb, 0)
        lay.addWidget(self.edit_ub, 0)

        chips = QHBoxLayout()
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(6)
        chips.addWidget(self.btn_nonneg)
        chips.addWidget(self.btn_free)
        chips.addWidget(self.btn_fixed)
        lay.addLayout(chips, 0)

    # --- helpers ---
    def _setup_chip(self, btn: QToolButton, text: str, preset: str) -> None:
        btn.setText(text)
        btn.setAutoRaise(True)
        btn.setFixedHeight(24)
        btn.clicked.connect(lambda: self.preset_clicked.emit(self._index, preset))

    @staticmethod
    def _format_value(val: Optional[float], *, is_lb: bool) -> str:
        """Turn internal value into line-edit text; None means ±∞ depending on side."""
        if val is None:
            return ""  # placeholder shows ±inf
        if val == float("inf") or val == float("-inf"):
            return ""
        # compact formatting without trailing zeros
        s = f"{val:.12g}"
        return s

    def refresh_strings(self) -> None:
        self.edit_lb.setPlaceholderText(S.t("lp.bounds.inf.minus"))
        self.edit_ub.setPlaceholderText(S.t("lp.bounds.inf.plus"))
        self.btn_nonneg.setText(S.t("lp.bounds.presets.nonneg"))
        self.btn_free.setText(S.t("lp.bounds.presets.free"))
        self.btn_fixed.setText(S.t("lp.bounds.presets.fixed"))
        self.sub.setStyleSheet(theme.secondary_text_css(self))

    # --- commit handlers ---
    def _on_lb_commit(self) -> None:
        try:
            parsed = self._parse_text(self.edit_lb.text(), is_lb=True)
        except ValueError as e:
            self.show_error("lb", str(e))
            return
        self.clear_error()
        self.lb_changed.emit(self._index, parsed)

    def _on_ub_commit(self) -> None:
        try:
            parsed = self._parse_text(self.edit_ub.text(), is_lb=False)
        except ValueError as e:
            self.show_error("ub", str(e))
            return
        self.clear_error()
        self.ub_changed.emit(self._index, parsed)


    @staticmethod
    def _parse_text(text: str, *, is_lb: bool) -> Optional[float]:
        """Parse user text for bounds. Empty => None (±inf externally). Accepts fractions and 'inf'."""
        s = (text or "").strip().lower()
        if s == "":
            return None
        s = s.replace(",", ".")
        if s in {"inf", "+inf", "∞"}:
            return None     # meaning +inf; for LB this will be treated as -inf at render-time policy
        if s == "-inf":
            return None     # we keep None as unbounded; rendering will show -inf/+inf by side
        if "/" in s:
            try:
                a, b = s.split("/", 1)
                return float(a) / float(b)
            except Exception:
                raise ValueError(S.t("lp.bounds.errors.invalid"))
        try:
            return float(s)
        except Exception:
            raise ValueError(S.t("lp.bounds.errors.invalid"))

    # --- error UI helpers ---
    def show_error(self, which: str, msg: str) -> None:
        """which in {'lb','ub','order'}."""
        target = self.edit_lb if which == "lb" else self.edit_ub
        target.setStyleSheet(
            f"border: 1px solid {tokens(theme.is_dark()).danger}; border-radius: 4px;"
        )
        target.setToolTip(msg)

    def clear_error(self) -> None:
        self.edit_lb.setStyleSheet("")
        self.edit_lb.setToolTip("")
        self.edit_ub.setStyleSheet("")
        self.edit_ub.setToolTip("")
