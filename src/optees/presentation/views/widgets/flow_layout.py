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
        max_x = rect.right() - r

        lines = []
        line = []
        line_h = 0

        for it in self._items:
            sz = it.sizeHint()
            w, h = sz.width(), sz.height()
            if line and (x + w > max_x + 1):
                lines.append((line, line_h))
                line = []
                x = rect.x() + l
                line_h = 0
            line.append((it, x, w))
            x += w + self._h
            line_h = max(line_h, h)

        if line:
            lines.append((line, line_h))

        cur_y = rect.y() + t
        for line_items, line_h in lines:
            for it, it_x, it_w in line_items:
                if not test_only:
                    it.setGeometry(QRect(it_x, cur_y, it_w, line_h))
            cur_y += line_h + self._v

        if lines:
            return cur_y - self._v + b
        return rect.y() + t + b
