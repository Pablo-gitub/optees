from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import QApplication, QPushButton, QWidget


class FloatingAssistantButton(QPushButton):
    """Small draggable assistant bubble shown above the current page."""

    clicked_without_drag = Signal()

    def __init__(self, icon_path: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drag_origin: QPoint | None = None
        self._button_origin: QPoint | None = None
        self._was_dragged = False
        self._manually_positioned = False

        self.setObjectName("floatingAssistantButton")
        self.setFixedSize(72, 72)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(QIcon(str(icon_path)))
        self.setIconSize(QSize(58, 58))
        self.setText("")
        self.setStyleSheet(
            """
            QPushButton#floatingAssistantButton {
                border: 1px solid rgba(125, 160, 190, 0.55);
                border-radius: 36px;
                background: rgba(12, 24, 38, 0.92);
                padding: 5px;
            }
            QPushButton#floatingAssistantButton:hover {
                border: 1px solid rgba(116, 233, 255, 0.9);
                background: rgba(18, 36, 56, 0.98);
            }
            """
        )

    def anchor_bottom_right(self, *, margin: int = 22) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.move(
            max(margin, parent.width() - self.width() - margin),
            max(margin, parent.height() - self.height() - margin),
        )
        self.raise_()

    def keep_inside_parent(self, *, margin: int = 12) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        bounds = QRect(
            margin,
            margin,
            max(1, parent.width() - self.width() - margin * 2),
            max(1, parent.height() - self.height() - margin * 2),
        )
        x = min(max(self.x(), bounds.left()), bounds.right())
        y = min(max(self.y(), bounds.top()), bounds.bottom())
        self.move(x, y)
        self.raise_()

    def was_manually_positioned(self) -> bool:
        return self._manually_positioned

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._button_origin = self.pos()
            self._was_dragged = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is None or self._button_origin is None:
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._drag_origin
        if delta.manhattanLength() >= QApplication.startDragDistance():
            self._was_dragged = True
            self._manually_positioned = True
        if self._was_dragged:
            self.move(self._button_origin + delta)
            self.keep_inside_parent()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._drag_origin is not None:
            clicked = not self._was_dragged and self.rect().contains(event.position().toPoint())
            self._drag_origin = None
            self._button_origin = None
            self._was_dragged = False
            if clicked:
                self.clicked_without_drag.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
