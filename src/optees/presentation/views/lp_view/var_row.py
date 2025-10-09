# src/optees/presentation/views/lp_view/var_row.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSizePolicy,
)
from PySide6.QtGui import QRegularExpressionValidator, QIcon
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QLineEdit, QToolButton

from optees.core.string_manager import strings as S

class VarRow(QWidget):
    remove_requested = Signal(int)      # variable index
    desc_changed = Signal(int, str)     # (index, text)

    def __init__(self, index: int, name: str, description: str,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # left label "Xk"
        self.lbl = QLabel(name)
        self.lbl.setMinimumWidth(40)

        # single-line input for short variable name
        self.txt = QLineEdit(description)
        self.txt.setPlaceholderText(S.t("lp.vars.name_placeholder"))
        self.txt.setClearButtonEnabled(True)
        self.txt.setFixedHeight(28)                   # single-line height
        self.txt.setMinimumWidth(160)
        self.txt.setMaximumWidth(400)
        self.txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.setStretchFactor(self.txt, 1)

        # light validation: letters/numbers/space/-/_ up to 24 chars
        rx = QRegularExpression(r"^[\w\s\-]{0,100}$")
        self.txt.setValidator(QRegularExpressionValidator(rx, self))

        # emit only on user edits (prevents programmatic setText loops)
        self.txt.textEdited.connect(self._on_text_edited)

        # delete button: toolbutton, icon-only, compact
        self.btn_remove = QToolButton()
        icon = QIcon.fromTheme("edit-delete")
        if not icon.isNull():
            self.btn_remove.setIcon(icon)
        else:
            self.btn_remove.setText("🗑︎")
        self.btn_remove.setToolTip(S.t("lp.vars.remove"))
        self.btn_remove.setAutoRaise(True)      # flat look
        self.btn_remove.setFixedSize(28, 28)    # compact square
        self.btn_remove.clicked.connect(self._on_remove)

        layout.addWidget(self.lbl)
        layout.addWidget(self.txt)                 # no stretch; stays compact
        layout.addWidget(self.btn_remove)

    def set_index_and_name(self, index: int, name: str) -> None:
        self._index = index
        self.lbl.setText(name)

    def _on_remove(self) -> None:
        self.remove_requested.emit(self._index)

    def _on_text_edited(self, text: str) -> None:
        # emit trimmed value to controller
        self.desc_changed.emit(self._index, text.strip())

    def refresh_strings(self) -> None:
        """Refresh i18n-dependent strings (placeholder, tooltips)."""
        self.txt.setPlaceholderText(S.t("lp.vars.name_placeholder"))
        self.btn_remove.setToolTip(S.t("lp.vars.remove"))