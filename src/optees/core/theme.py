# src/optees/core/theme.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import QObject, QEvent, Signal, Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QWidget


def _luminance(c: QColor) -> float:
    return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()


class ThemeManager(QObject):
    theme_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._installed = False
        self._last_is_dark: Optional[bool] = None  # cache

    # ---------- query ----------
    def is_dark(self) -> bool:
        app = QApplication.instance()
        if app is None:
            # fallback to last known value or light
            return self._last_is_dark if self._last_is_dark is not None else False

        # Qt 6.5+: ask the colorScheme when available
        try:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                self._last_is_dark = True
                return True
            if scheme == Qt.ColorScheme.Light:
                self._last_is_dark = False
                return False
        except Exception:
            pass

        # Robust fallback: luminance on window background
        try:
            pal = app.palette()
            bg = pal.color(QPalette.ColorRole.Window)
            val = _luminance(bg) < 0.5
            self._last_is_dark = val
            return val
        except Exception:
            # last known or default
            return self._last_is_dark if self._last_is_dark is not None else False

    def fg_color(self, widget: Optional[QWidget] = None) -> QColor:
        app = QApplication.instance()
        pal = None
        try:
            if widget is not None:
                pal = widget.palette()
            elif app is not None:
                pal = app.palette()
        except Exception:
            pal = None

        if pal is None:
            # conservative fallback based on last known is_dark
            return QColor(255, 255, 255) if (self._last_is_dark or False) else QColor(20, 20, 20)

        col = pal.color(QPalette.ColorRole.Text)
        if not col.isValid():
            col = pal.color(QPalette.ColorRole.WindowText)
        return col

    def tint_for_icons(self, widget: Optional[QWidget] = None) -> QColor:
        return QColor(255, 255, 255) if self.is_dark() else QColor(20, 20, 20)

    def secondary_text_css(self, widget: Optional[QWidget] = None) -> str:
        return "color: rgba(255,255,255,0.75);" if self.is_dark() else "color: rgba(0,0,0,0.70);"

    # ---------- lifecycle ----------
    def install_app_watcher(self) -> None:
        if self._installed:
            return
        app = QApplication.instance()
        if app is None:
            return
        app.installEventFilter(self)
        self._installed = True

    # ---------- Qt hook ----------
    def eventFilter(self, obj, ev):
        if ev.type() in (
            QEvent.ApplicationPaletteChange,
            QEvent.PaletteChange,
            QEvent.StyleChange,
            getattr(QEvent, "ThemeChange", QEvent.User),
        ):
            # notify listeners
            self.theme_changed.emit()
        # Don't call super() here; return False to let Qt continue default handling
        return False


# Singleton
theme = ThemeManager()

# ---- Back-compat API (if something else imports these) ----
def is_dark_mode() -> bool:
    return theme.is_dark()

def theme_icon_color() -> QColor:
    return theme.fg_color()
