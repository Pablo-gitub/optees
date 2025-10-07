from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea,
    QHBoxLayout, QSizePolicy
)
from optees.core.assets import asset
from optees.presentation.views.widgets.card_button import CardButton
from optees.presentation.views.widgets.flow_layout import FlowLayout

CARD_W = 360
CARD_H = 140

class Category(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        h = QLabel(f"<span style='font-size:18px; font-weight:600'>{title}</span>")
        h.setTextFormat(Qt.RichText)
        root.addWidget(h)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: rgba(255,255,255,0.15);")
        root.addWidget(line)

        self.flow = FlowLayout(hspacing=12, vspacing=12)
        root.addLayout(self.flow)

    def add_card(self, card: QWidget) -> None:
        self.flow.addWidget(card)


class HomePage(QWidget):
    go_lp = Signal()
    go_milp = Signal()
    go_knap = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        outer.addWidget(sc)

        container = QWidget()
        sc.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(24)

        # --- Linear Programming section ---
        cat_lin = Category("Linear Programming")
        root.addWidget(cat_lin)

        lp = CardButton(
            "Linear Programming (LP)",
            "Solve continuous linear programs with HiGHS (SciPy).",
            icon_path=str(asset("icons/lp.svg")),
        )
        milp = CardButton(
            "Mixed-Integer Linear Programming (MILP)",
            "Integer/binary models via OR-Tools (CP-SAT / CBC).",
            icon_path=str(asset("icons/milp.svg")), badge="int/bool"
        )
        knap = CardButton(
            "0/1 Knapsack",
            "Exact DP solver; predictable and deterministic.",
            icon_path=str(asset("icons/knap.svg")),
        )

        lp.clicked.connect(self.go_lp.emit)
        milp.clicked.connect(self.go_milp.emit)
        knap.clicked.connect(self.go_knap.emit)

        for card in (lp, milp, knap):
            cat_lin.add_card(card)

        # --- Future categories ---
        for t in ("Nonlinear Programming", "Graph Theory", "AI & Machine Learning"):
            cat = Category(t)
            ph = QLabel("Coming soon…")
            ph.setStyleSheet("color: rgba(255,255,255,0.5);")
            cat.add_card(ph)
            root.addWidget(cat)
