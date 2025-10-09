# src/optees/presentation/main_window.py
from __future__ import annotations
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QToolBar, QToolButton, QMenu,
    QStatusBar, QWidget, QSizePolicy
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSize

from optees.core.theme import theme
from optees.core.assets import asset
from optees.core.string_manager import strings as S

from optees.presentation.views.home_view import HomePage
from optees.presentation.views.lp_view.lp_view import LPView
from optees.presentation.views.milp_view import MILPView
from optees.presentation.views.knapsack_view import KnapsackView
from optees.presentation.views.settings_view import SettingsView
from optees.presentation.controllers.lp_controller import LPController


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Optees")
        self.resize(1100, 720)

        # --- central stack & pages ---
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home_page = HomePage()
        self.lp_page = LPView()
        self.lp_controller = LPController()
        self.lp_page.set_controller(self.lp_controller)
        self.milp_page = MILPView()
        self.knap_page = KnapsackView()
        self.settings_page = SettingsView()

        for w in (self.home_page, self.lp_page, self.milp_page, self.knap_page, self.settings_page):
            self.stack.addWidget(w)
        self.stack.setCurrentWidget(self.home_page)

        # wire cards -> pages
        self.home_page.go_lp.connect(lambda: self.stack.setCurrentWidget(self.lp_page))
        self.home_page.go_milp.connect(lambda: self.stack.setCurrentWidget(self.milp_page))
        self.home_page.go_knap.connect(lambda: self.stack.setCurrentWidget(self.knap_page))

        self._build_toolbar()
        self.setStatusBar(QStatusBar(self))

        # set window icon according to theme
        self._apply_window_icon()

        # global signals
        theme.theme_changed.connect(self._on_theme_changed)
        S.language_changed.connect(self._retranslate_toolbar)

    # ---------------- toolbar with dropdown + settings button (right) -------------
    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(S.t("nav.toolbar.title"))
        self.toolbar.setMovable(False)
        # opzionale: rendi le icone un filo più grandi
        self.toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # Home
        self.act_home = QAction(S.t("nav.home"), self)
        self.act_home.triggered.connect(lambda: self.stack.setCurrentWidget(self.home_page))
        self.toolbar.addAction(self.act_home)

        # Dropdown: Linear Optimization
        self.drop = QToolButton(self)
        self.drop.setText(S.t("nav.linear_optimization"))
        self.drop.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(self.drop)
        self.act_lp = QAction(S.t("alg.lp"), self)
        self.act_lp.triggered.connect(lambda: self.stack.setCurrentWidget(self.lp_page))
        menu.addAction(self.act_lp)

        self.act_milp = QAction(S.t("alg.milp"), self)
        self.act_milp.triggered.connect(lambda: self.stack.setCurrentWidget(self.milp_page))
        menu.addAction(self.act_milp)

        self.act_knap = QAction(S.t("alg.knap"), self)
        self.act_knap.triggered.connect(lambda: self.stack.setCurrentWidget(self.knap_page))
        menu.addAction(self.act_knap)

        self.drop.setMenu(menu)
        self.toolbar.addWidget(self.drop)

        # spacer -> spinge tutto ciò che segue a destra
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        # Settings come QAction (più coerente con la toolbar)
        self.act_settings = QAction(S.t("nav.settings"), self)
        self.act_settings.setToolTip(S.t("nav.settings"))
        self.act_settings.setIcon(QIcon())
        self.act_settings.triggered.connect(
            lambda: self.stack.setCurrentWidget(self.settings_page)
        )
        self.toolbar.addAction(self.act_settings)


    # ---------------- theming helpers ----------------

    def _apply_window_icon(self) -> None:
        try:
            sub = "dark" if theme.is_dark() else "light"
            self.setWindowIcon(QIcon(str(asset(f"logo/{sub}/appicon_256.png"))))
        except Exception:
            pass

    def _on_theme_changed(self) -> None:
        self._apply_window_icon()
        for page in (self.home_page, self.lp_page, self.milp_page, self.knap_page, self.settings_page):
            if hasattr(page, "refresh_theme"):
                try:
                    page.refresh_theme()
                except Exception:
                    pass

    def _retranslate_toolbar(self) -> None:
        # niente findChild: abbiamo self.toolbar
        self.toolbar.setWindowTitle(S.t("nav.toolbar.title"))
        self.act_home.setText(S.t("nav.home"))
        self.drop.setText(S.t("nav.linear_optimization"))
        self.act_lp.setText(S.t("alg.lp"))
        self.act_milp.setText(S.t("alg.milp"))
        self.act_knap.setText(S.t("alg.knap"))
        self.act_settings.setText(S.t("nav.settings"))
        self.act_settings.setToolTip(S.t("nav.settings"))

        # retranslate pages
        for page in (self.home_page, self.lp_page, self.milp_page, self.knap_page, self.settings_page):
            if hasattr(page, "refresh_strings"):
                try:
                    page.refresh_strings()
                except Exception:
                    pass
