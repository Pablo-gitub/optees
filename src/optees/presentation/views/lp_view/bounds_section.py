from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.controllers.lp_controller import LPVariable
from .section import Section
from .bound_row import BoundRow

def _clear_layout(lay: QVBoxLayout) -> None:
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w:
            w.deleteLater()

class BoundsSection(Section):
    """Manages per-variable bounds rows and header."""
    lb_changed = Signal(int, object)     # (index, lb)
    ub_changed = Signal(int, object)     # (index, ub)
    preset_clicked = Signal(int, str)    # (index, preset)

    def __init__(self, max_width: int | None = None, parent: QWidget | None = None):
        super().__init__("", parent)
        if max_width:
            self.setFixedWidth(max_width)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # header (keep label refs, no magic indices)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(8)
        self.col_var = QLabel()
        self.col_lb  = QLabel()
        self.col_ub  = QLabel()
        self.col_pre = QLabel()
        hdr.addWidget(self.col_var, 1)
        hdr.addWidget(self.col_lb, 0)
        hdr.addWidget(self.col_ub, 0)
        hdr.addWidget(self.col_pre, 0)
        self.body.addLayout(hdr)

        # hint
        self._hint = QLabel()
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)

        # rows container
        self._rows_lay = QVBoxLayout()
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(8)
        self.body.addLayout(self._rows_lay)

        self.refresh_strings()

    def refresh_strings(self) -> None:
        self.set_title(S.t("lp.bounds.section"))
        self.col_var.setText(S.t("lp.bounds.columns.var"))
        self.col_lb.setText(S.t("lp.bounds.columns.lb"))
        self.col_ub.setText(S.t("lp.bounds.columns.ub"))
        self.col_pre.setText(S.t("lp.bounds.columns.preset"))
        self._hint.setText(S.t("lp.bounds.hint"))

        for row in self.findChildren(BoundRow):
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))

    # ---- data binding ----
    def set_variables(self, vars_list: List[LPVariable]) -> None:
        _clear_layout(self._rows_lay)
        for i, v in enumerate(vars_list):
            row = BoundRow(index=i, var_name=v.name, display_label=v.label, lb=v.lb, ub=v.ub)
            row.refresh_strings()
            row.lb_changed.connect(self.lb_changed.emit)
            row.ub_changed.connect(self.ub_changed.emit)
            row.preset_clicked.connect(self.preset_clicked.emit)
            self._rows_lay.addWidget(row)

    def update_bound(self, index: int, lb: Optional[float], ub: Optional[float]) -> None:
        rows = self.findChildren(BoundRow)
        if 0 <= index < len(rows):
            if lb is not None:
                rows[index].edit_lb.setText(BoundRow._format_value(lb, is_lb=True))
            if ub is not None:
                rows[index].edit_ub.setText(BoundRow._format_value(ub, is_lb=False))
            rows[index].clear_error()
