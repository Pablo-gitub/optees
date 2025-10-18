# src/optees/presentation/views/widgets/stretch_flow_layout.py
from __future__ import annotations
from typing import List, Tuple
from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import QLayout, QLayoutItem

class StretchFlowLayout(QLayout):
    """
    Flow layout that wraps items to next line and *stretches* items in each row
    to share the remaining width evenly. Useful for responsive 2-up → 1-up layouts.
    """
    def __init__(self, parent=None, margin: int = 0, hspacing: int = 16, vspacing: int = 16):
        super().__init__(parent)
        self._items: List[QLayoutItem] = []
        self._h = hspacing
        self._v = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    # --- QLayout protocol ---
    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i: int):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i: int):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        # allow expansion both horizontally and vertically
        return Qt.Orientations(Qt.Horizontal | Qt.Vertical)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        l, t, r, b = self.getContentsMargins()
        s += QSize(l + r, t + b)
        return s

    # --- core ---
    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        l, t, r, b = self.getContentsMargins()
        x0 = rect.x() + l
        y = rect.y() + t
        max_x = rect.right() - r

        # Collect lines: each line is a list of (item, sizeHint)
        lines: List[List[Tuple[QLayoutItem, QSize]]] = []
        line: List[Tuple[QLayoutItem, QSize]] = []
        line_width = 0
        line_h = 0

        def commit_line():
            nonlocal line, line_width, line_h
            if line:
                lines.append(line[:])
                line = []
                line_width = 0
                line_h = 0

        for it in self._items:
            sz = it.sizeHint()
            w, h = sz.width(), sz.height()
            # wrap if needed (but avoid wrapping as first element)
            if line and (rect.x() + l + line_width + (self._h if line else 0) + w > max_x + 1):
                commit_line()
            # add to current line
            if line:
                line_width += self._h
            line.append((it, sz))
            line_width += w
            line_h = max(line_h, h)

        commit_line()

        # Place lines with stretching
        for items in lines:
            if not items:
                continue
            # compute line width with spacings
            total_w = sum(sz.width() for _, sz in items)
            gaps = self._h * (len(items) - 1) if len(items) > 1 else 0
            avail_w = max_x - x0
            extra = max(0, avail_w - total_w - gaps)

            x = x0
            line_h = max(sz.height() for _, sz in items)

            # distribute remaining width evenly
            extra_per_item = extra // len(items) if items else 0

            for idx, (it, sz) in enumerate(items):
                w = sz.width() + extra_per_item
                # give any leftover pixels to the last item to avoid gaps
                if idx == len(items) - 1:
                    used = (sz.width() + extra_per_item) * (len(items) - 1)
                    w = avail_w - gaps - used
                if not test_only:
                    it.setGeometry(QRect(QPoint(x, y), QSize(max(0, w), line_h)))
                x += w + self._h

            y += line_h + self._v

        return y + b