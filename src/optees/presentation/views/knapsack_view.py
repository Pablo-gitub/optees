from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class KnapsackView(QWidget):
    """Placeholder for 0/1 Knapsack page."""
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        title = QLabel("0/1 Knapsack")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        lay.addWidget(title)
        hint = QLabel("Editor coming soon: items table (value, weight), capacity, solve.")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addStretch(1)
