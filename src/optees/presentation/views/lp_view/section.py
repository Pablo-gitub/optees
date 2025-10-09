from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy, QWidget
from optees.core.theme import theme

class Section(QFrame):
    """Generic card with a title and a vertical body layout."""
    def __init__(self, title_text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("Section")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 10, 14, 10)
        self._root.setSpacing(8)

        self._title = QLabel(title_text, self)
        self._title.setObjectName("SectionTitle")
        self._title.setTextFormat(Qt.RichText)
        self._root.addWidget(self._title)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        self._root.addLayout(self.body)

    def set_title(self, text: str) -> None:
        self._title.setText(f"<span style='font-size:16px; font-weight:600'>{text}</span>")

    def refresh_theme(self) -> None:
        if theme.is_dark():
            self.setStyleSheet("""
                QFrame#Section { border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }
                QLabel#SectionTitle { color: rgba(255,255,255,0.92); }
            """)
        else:
            self.setStyleSheet("""
                QFrame#Section { border: 1px solid rgba(0,0,0,0.10); border-radius: 10px; }
                QLabel#SectionTitle { color: rgba(0,0,0,0.85); }
            """)
