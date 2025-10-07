from __future__ import annotations
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QToolBar, QToolButton, QMenu, QStatusBar
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from optees.presentation.views.home_view import HomePage
from optees.presentation.views.lp_view import LPView
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Optees")
        self.resize(1100, 720)

        # --- pages ---
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home_page = HomePage()
        self.lp_page = LPView()
        self.milp_page = MILPView()
        self.knap_page = KnapsackView()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.lp_page)
        self.stack.addWidget(self.milp_page)
        self.stack.addWidget(self.knap_page)
        self.stack.setCurrentWidget(self.home_page)

        # wire cards -> pages
        self.home_page.go_lp.connect(lambda: self.stack.setCurrentWidget(self.lp_page))
        self.home_page.go_milp.connect(lambda: self.stack.setCurrentWidget(self.milp_page))
        self.home_page.go_knap.connect(lambda: self.stack.setCurrentWidget(self.knap_page))

        self._build_toolbar()
        self.setStatusBar(QStatusBar(self))

    # ---------------- toolbar with dropdown ----------------
    def _build_toolbar(self) -> None:
        tb = QToolBar("Navigation", self)
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize())  # keep default
        self.addToolBar(Qt.TopToolBarArea, tb)

        # Home action
        act_home = QAction("Home", self)
        act_home.triggered.connect(lambda: self.stack.setCurrentWidget(self.home_page))
        tb.addAction(act_home)

        # Dropdown: Linear Optimization
        drop = QToolButton(self)
        drop.setText("Linear Optimization")
        drop.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(drop)
        act_lp = QAction("Linear Programming (LP)", self)
        act_lp.triggered.connect(lambda: self.stack.setCurrentWidget(self.lp_page))
        menu.addAction(act_lp)

        act_milp = QAction("Mixed-Integer (MILP)", self)
        act_milp.triggered.connect(lambda: self.stack.setCurrentWidget(self.milp_page))
        menu.addAction(act_milp)

        act_knap = QAction("0/1 Knapsack", self)
        act_knap.triggered.connect(lambda: self.stack.setCurrentWidget(self.knap_page))
        menu.addAction(act_knap)

        drop.setMenu(menu)
        tb.addWidget(drop)
