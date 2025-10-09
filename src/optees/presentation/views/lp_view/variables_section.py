from __future__ import annotations
from typing import List
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.controllers.lp_controller import LPVariable
from .section import Section
from .var_row import VarRow

def _clear_layout(lay: QVBoxLayout) -> None:
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w:
            w.deleteLater()

class VariablesSection(Section):
    """Manages the 'Variables legend' card with dynamic VarRow list."""
    add_clicked = Signal()
    remove_clicked = Signal(int)
    label_changed = Signal(int, str)

    def __init__(self, max_width: int | None = None, parent: QWidget | None = None):
        super().__init__("", parent)
        if max_width:
            self.setFixedWidth(max_width)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # hint
        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)

        # rows container
        self._rows_lay = QVBoxLayout()
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(8)
        self.body.addLayout(self._rows_lay)

        # footer with "Add variable"
        f = QHBoxLayout()
        f.addStretch(1)
        self.btn_add = QPushButton()
        f.addWidget(self.btn_add)
        self.body.addLayout(f)

        self.btn_add.clicked.connect(self.add_clicked.emit)
        self.refresh_strings()

    def refresh_strings(self) -> None:
        self.set_title(S.t("lp.vars.section"))
        self._hint.setText(S.t("lp.vars.hint"))
        self.btn_add.setText(S.t("lp.vars.add"))

        # propagate to row placeholders (placeholder/tooltips)
        for row in self.findChildren(VarRow):
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))

    # ---- data binding ----
    def set_variables(self, vars_list: List[LPVariable]) -> None:
        _clear_layout(self._rows_lay)
        for i, v in enumerate(vars_list):
            row = VarRow(index=i, name=v.name, description=v.label)
            row.refresh_strings()
            row.remove_requested.connect(self.remove_clicked.emit)
            row.desc_changed.connect(self.label_changed.emit)
            self._rows_lay.addWidget(row)

    def update_label(self, index: int, text: str) -> None:
        rows = self.findChildren(VarRow)
        if 0 <= index < len(rows):
            rows[index].txt.setText(text or "")
