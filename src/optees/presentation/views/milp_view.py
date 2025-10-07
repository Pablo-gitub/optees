from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class MILPView(QWidget):
    """Placeholder for Mixed-Integer LP editor page."""
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        title = QLabel("Mixed-Integer Linear Programming (MILP)")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        lay.addWidget(title)
        hint = QLabel("Editor coming soon: integrality, bounds, constraints, objective…")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addStretch(1)
