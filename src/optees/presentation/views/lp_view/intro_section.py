# src/optees/presentation/views/lp_view/intro_section.py
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from .section import Section

class IntroSection(Section):
    """Static intro: description + two buttons (Example, Problem)."""
    example_clicked = Signal()
    problem_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("", parent)

        # description
        self._desc = QLabel()
        self._desc.setWordWrap(True)
        self._desc.setObjectName("IntroDesc")
        self._desc.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._desc)

        # buttons (right-aligned)
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_problem = QPushButton()
        btns.addWidget(self.btn_example)
        btns.addWidget(self.btn_problem)
        self.body.addLayout(btns)

        self.btn_example.clicked.connect(self.example_clicked.emit)
        self.btn_problem.clicked.connect(self.problem_clicked.emit)

        self.refresh_strings()

    def refresh_strings(self) -> None:
        self._desc.setText(S.t("lp.header.description"))
        self.btn_example.setText(S.t("lp.header.buttons.example"))
        self.btn_problem.setText(S.t("lp.header.buttons.problem"))

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._desc.setStyleSheet(theme.secondary_text_css(self))
