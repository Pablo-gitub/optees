# src/optees/presentation/widgets/flow_layout.py
from __future__ import annotations
from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import QLayout

class FlowLayout(QLayout):
    """Simple flow layout: place widgets left→right and wrap to next row."""
    def __init__(self, parent=None, margin: int = 0, hspacing: int = 12, vspacing: int = 12):
        super().__init__(parent)
        self._items = []
        self._h = hspacing
        self._v = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    # --- QLayout protocol ---
    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i): return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return Qt.Orientations(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self._do_layout(QRect(0, 0, width, 0), test_only=True)
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        l, t, r, b = self.getContentsMargins()
        s += QSize(l + r, t + b)
        return s

    # --- core ---
    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        l, t, r, b = self.getContentsMargins()
        x = rect.x() + l
        y = rect.y() + t
        line_h = 0
        max_x = rect.right() - r

        for it in self._items:
            sz = it.sizeHint()
            w, h = sz.width(), sz.height()
            if x + w > max_x + 1 and line_h > 0:  # wrap
                x = rect.x() + l
                y += line_h + self._v
                line_h = 0
            if not test_only:
                it.setGeometry(QRect(QPoint(x, y), sz))
            x += w + self._h
            line_h = max(line_h, h)

        return y + line_h + b
