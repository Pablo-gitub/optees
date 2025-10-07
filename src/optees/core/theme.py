from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

def is_dark_mode() -> bool:
    # Qt 6.5+
    try:
        return QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        pass
    # fallback: luminanza del colore di sfondo
    pal = QApplication.palette()
    bg = pal.color(QPalette.Window)
    y = 0.2126*bg.redF() + 0.7152*bg.greenF() + 0.0722*bg.blueF()
    return y < 0.5

def theme_icon_color() -> QColor:
    # usa il colore del testo della finestra: è bianco su dark, nero su light
    pal = QApplication.palette()
    return pal.color(QPalette.WindowText)