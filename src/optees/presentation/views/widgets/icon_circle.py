from __future__ import annotations
from typing import Optional
import os

from PySide6.QtCore import Qt, QEvent, QRect
from PySide6.QtGui import QPainter, QPixmap, QPalette, QImage, QColor, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame


class IconCircle(QFrame):
    """
    Circular chip that renders a tinted SVG.

    - Uses an explicit tint color if provided (set_tint_color).
    - Falls back to palette Text/WindowText if no override is set.
    - Rebuilds pixmap when theme/tint changes.
    - Draws '?' fallback if SVG is missing/invalid.
    """

    def __init__(self, icon_path: Optional[str], size: int = 72, parent=None):
        super().__init__(parent)
        self._size = int(size)
        self._path: Optional[str] = None
        self._svg: Optional[QSvgRenderer] = None
        self._svg_valid = False

        self._pm_tinted: Optional[QPixmap] = None
        self._last_tint_rgba: Optional[int] = None
        self._tint_override: Optional[QColor] = None  # <<— explicit tint override

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self._size, self._size)

        if icon_path:
            self.set_icon_path(icon_path)

    # ---------- public API ----------

    def set_icon_path(self, path_like) -> None:
        path = os.fspath(path_like)
        self._path = path
        self._svg = None
        self._svg_valid = False

        if os.path.isfile(path):
            r = QSvgRenderer(path)
            if r.isValid():
                self._svg = r
                self._svg_valid = True
            else:
                print(f"[IconCircle] QSvgRenderer invalid for: {path}")
        else:
            print(f"[IconCircle] SVG path not found: {path}")

        self._rebuild_pixmap()

    def set_tint_color(self, color: Optional[QColor]) -> None:
        """Force a specific tint (e.g., white for dark theme, near-black for light)."""
        self._tint_override = color
        self._rebuild_pixmap()

    def refresh_theme(self) -> None:
        """Rebuild using current palette / override."""
        self._rebuild_pixmap()

    # ---------- internals ----------

    def _is_dark_theme(self) -> bool:
        """Heuristica: tema scuro se la luminanza dello sfondo è bassa."""
        bg = self.palette().color(QPalette.ColorRole.Window)
        y = 0.2126 * bg.redF() + 0.7152 * bg.greenF() + 0.0722 * bg.blueF()
        return y < 0.5

    def _current_tint_color(self) -> QColor:
        if self._tint_override is not None:
            return self._tint_override
        return QColor(255, 255, 255) if self._is_dark_theme() else QColor(20, 20, 20)

    def _circle_bg_color(self) -> QColor:
        c = self.palette().color(QPalette.ColorRole.Window)
        c.setAlphaF(0.10)
        return c

    def _rebuild_pixmap(self) -> None:
        tint = self._current_tint_color()
        self._last_tint_rgba = tint.rgba()

        if not self._svg_valid:
            self._pm_tinted = None
            self.update()
            return

        dpr = self.devicePixelRatioF() or 1.0
        px = int(self._size * dpr)

        # 1) render SVG to alpha mask
        mask = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
        mask.fill(Qt.transparent)
        p = QPainter(mask)
        p.setRenderHint(QPainter.Antialiasing, True)
        inset = int(self._size * 0.20 * dpr)
        self._svg.render(p, QRect(inset, inset, px - 2 * inset, px - 2 * inset))
        p.end()

        # 2) create solid tint then apply alpha with DestinationIn (robust tint)
        tinted = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
        tinted.fill(tint)  # fill with the tint color
        p = QPainter(tinted)
        p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        p.drawImage(0, 0, mask)  # keep only mask's alpha
        p.end()

        pm = QPixmap.fromImage(tinted)
        pm.setDevicePixelRatio(dpr)
        self._pm_tinted = pm
        self.update()

    # ---------- painting & events ----------

    def paintEvent(self, ev):
        # If tint changed (palette or override), rebuild on the fly
        tint_now = self._current_tint_color().rgba()
        if self._last_tint_rgba != tint_now:
            self._rebuild_pixmap()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # subtle circular background
        p.setBrush(self._circle_bg_color())
        p.setPen(Qt.NoPen)
        r = min(self.width(), self.height())
        p.drawEllipse(0, 0, r, r)

        if self._pm_tinted is None:
            # graceful fallback
            pen = self.palette().color(QPalette.ColorRole.Text)
            if not pen.isValid():
                pen = self.palette().color(QPalette.ColorRole.WindowText)
            p.setPen(pen)
            f = p.font(); f.setBold(True); f.setPointSizeF(self._size * 0.35)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, "?")
            return

        w = h = self._size
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        p.drawPixmap(x, y, w, h, self._pm_tinted)

    def changeEvent(self, ev):
        if ev.type() in (
            QEvent.PaletteChange,
            QEvent.ApplicationPaletteChange,
            QEvent.StyleChange,
            getattr(QEvent, "ThemeChange", QEvent.User),
        ):
            self._rebuild_pixmap()
        super().changeEvent(ev)
