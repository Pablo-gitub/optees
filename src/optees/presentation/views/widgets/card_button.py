from __future__ import annotations
from typing import Optional
import os

from PySide6.QtCore import Qt, QEvent, QSize, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy

from optees.presentation.views.widgets.icon_circle import IconCircle
from optees.core.assets import asset as asset_path
from optees.core.design import tokens
from optees.core.theme import theme

CARD_W = 360
CARD_H = 140


def _abs_icon_path(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    p = os.fspath(p)
    return p if os.path.isabs(p) else os.fspath(asset_path(p))


class CardButton(QFrame):
    clicked = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        *,
        icon_path: Optional[str] = None,
        badge: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._constructed = False

        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        # Fixed width for a tidy grid, but the height grows with the content so
        # long descriptions are never clipped.
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.setFixedWidth(CARD_W)
        self.setMinimumHeight(CARD_H)
        # Surface/border/hover come from the global stylesheet (QFrame#Card).

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # icon
        icon_abs = _abs_icon_path(icon_path)
        self._icon = IconCircle(icon_abs, size=72, parent=self)
        root.addWidget(self._icon, 0, Qt.AlignTop)

        # text column
        self._title = QLabel(f"<span style='font-weight:700'>{title}</span>")
        self._title.setTextFormat(Qt.RichText)
        self._title.setWordWrap(True)
        self._title.setStyleSheet("color: rgba(255,255,255,0.95);")

        self._sub = QLabel(subtitle)
        self._sub.setWordWrap(True)
        self._sub.setStyleSheet("color: rgba(255,255,255,0.75);")

        title_row = QHBoxLayout()
        title_row.addWidget(self._title, 1)

        if badge:
            b = QLabel(badge)
            b.setObjectName("badge")
            # Styled globally via QLabel#badge.
            title_row.addWidget(b, 0, Qt.AlignRight)

        text_col = QVBoxLayout()
        text_col.addLayout(title_row)
        text_col.addWidget(self._sub, 1)
        root.addLayout(text_col, 1)

        self._constructed = True
        self._apply_theme()

    # The width is fixed, so derive the height from the wrapped content instead
    # of a fixed value: this is what stops long descriptions from being clipped.
    def sizeHint(self) -> QSize:
        layout = self.layout()
        if layout is not None and layout.hasHeightForWidth():
            height = layout.heightForWidth(CARD_W)
        else:
            height = super().sizeHint().height()
        return QSize(CARD_W, max(CARD_H, height))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    # ---- theming ----
    def _is_dark(self) -> bool:
        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Window)
        fg = pal.color(QPalette.ColorRole.Text)
        # luminance check
        def lum(c: QColor) -> float:
            return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()
        return lum(fg) > lum(bg)

    def _apply_theme(self) -> None:
        if not self._constructed:
            return
        # Text colors come from the central tokens so cards read correctly in
        # both light and dark themes.
        t = tokens(theme.is_dark())
        self._title.setStyleSheet(f"color: {t.text};")
        self._sub.setStyleSheet(f"color: {t.text_muted};")
        self._icon.refresh_theme()

    def changeEvent(self, ev):
        if ev.type() in (
            QEvent.PaletteChange,
            QEvent.ApplicationPaletteChange,
            QEvent.StyleChange,
            getattr(QEvent, "ThemeChange", QEvent.User),
        ):
            self._apply_theme()
        super().changeEvent(ev)
