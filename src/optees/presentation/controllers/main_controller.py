from __future__ import annotations
from PySide6.QtCore import QObject
from optees.presentation.main_window import MainWindow
from optees.presentation.views.home_view import HomeView

class MainController(QObject):
    """
    Wires view signals to navigation/actions.
    Keep business logic out of here: this is presentation/controller only.
    """

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.window = window

        # Home signals → navigation
        home: HomeView = self.window.page("home")  # type: ignore[assignment]
        home.open_lp.connect(lambda: self.window.goto("lp"))
        home.open_milp.connect(lambda: self.window.goto("milp"))
        home.open_knapsack.connect(lambda: self.window.goto("knapsack"))
