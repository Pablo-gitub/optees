from __future__ import annotations
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from .theme import theme_icon_color

def render_svg_colored(path: str, size: int | QSize, color: QColor | None = None) -> QPixmap:
    """Render an SVG and tint it with a single color (monochrome)."""
    if isinstance(size, int):
        size = QSize(size, size)

    r = QSvgRenderer(path)
    pm = QPixmap(size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    r.render(p)
    p.end()

    # tint
    tint = QPixmap(size)
    tint.fill(color or theme_icon_color())

    p = QPainter(tint)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawPixmap(0, 0, pm)
    p.end()
    return tint
