# src/optees/presentation/views/home_view.py
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea,
    QHBoxLayout, QSizePolicy
)

from optees.core.assets import asset
from optees.core.string_manager import strings as S
from optees.presentation.views.widgets.card_button import CardButton
from optees.presentation.views.widgets.flow_layout import FlowLayout

CARD_W = 360
CARD_H = 140


class Category(QFrame):
    """Section with a title and a FlowLayout for cards."""
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        # keep a handle to the label so we can retranslate later
        self._title_lbl = QLabel()
        self._title_lbl.setTextFormat(Qt.RichText)
        root.addWidget(self._title_lbl)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: rgba(255,255,255,0.15);")
        root.addWidget(line)

        self.flow = FlowLayout(hspacing=12, vspacing=12)
        root.addLayout(self.flow)

        self.set_title(title)

    def set_title(self, text: str) -> None:
        # simple rich-text style (unchanged for now)
        self._title_lbl.setText(f"<span style='font-size:18px; font-weight:600'>{text}</span>")

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

        # --- Categories ---
        self.cat_lin = Category(S.t("home.category.linear"))
        root.addWidget(self.cat_lin)

        # Future categories (placeholders)
        self.cat_nlp = Category(S.t("home.category.nlp"))
        self.cat_graph = Category(S.t("home.category.graph"))
        self.cat_ml = Category(S.t("home.category.ml"))

        # --- Cards (with initial translated strings) ---
        self.card_lp = CardButton(
            S.t("cards.lp.title"),
            S.t("cards.lp.subtitle"),
            icon_path=str(asset("icons/lp.svg")),
        )
        self.card_milp = CardButton(
            S.t("cards.milp.title"),
            S.t("cards.milp.subtitle"),
            icon_path=str(asset("icons/milp.svg")),
            badge=S.t("badge.intbool"),
        )
        self.card_knap = CardButton(
            S.t("cards.knap.title"),
            S.t("cards.knap.subtitle"),
            icon_path=str(asset("icons/knap.svg")),
        )

        # wire signals
        self.card_lp.clicked.connect(self.go_lp.emit)
        self.card_milp.clicked.connect(self.go_milp.emit)
        self.card_knap.clicked.connect(self.go_knap.emit)

        # add cards to the first category
        for card in (self.card_lp, self.card_milp, self.card_knap):
            self.cat_lin.add_card(card)

        # --- Future sections with "coming soon..." placeholder ---
        self._coming_labels = []  # keep references to update text on language change
        for cat in (self.cat_nlp, self.cat_graph, self.cat_ml):
            ph = QLabel(S.t("home.comingSoon"))
            ph.setStyleSheet("color: rgba(255,255,255,0.5);")
            cat.add_card(ph)
            root.addWidget(cat)
            self._coming_labels.append(ph)

        # Listen for language changes (optional; main_window already calls refresh_strings)
        try:
            from optees.core.string_manager import strings as _S
            _S.language_changed.connect(self.refresh_strings)
        except Exception:
            pass

    # ---------------- public: retranslate all strings ----------------
    def refresh_strings(self) -> None:
        # categories
        self.cat_lin.set_title(S.t("home.category.linear"))
        self.cat_nlp.set_title(S.t("home.category.nlp"))
        self.cat_graph.set_title(S.t("home.category.graph"))
        self.cat_ml.set_title(S.t("home.category.ml"))

        # cards (title/subtitle)
        # CardButton stores QLabel handles as _title (rich) and _sub
        self.card_lp._title.setText(f"<span style='font-weight:700'>{S.t('cards.lp.title')}</span>")
        self.card_lp._sub.setText(S.t("cards.lp.subtitle"))

        self.card_milp._title.setText(f"<span style='font-weight:700'>{S.t('cards.milp.title')}</span>")
        self.card_milp._sub.setText(S.t("cards.milp.subtitle"))
        # update badge via objectName lookup (CardButton sets objectName 'badge')
        from PySide6.QtWidgets import QLabel as _QLabel  # local import to avoid polluting namespace
        milp_badge = self.card_milp.findChild(_QLabel, "badge")
        if milp_badge is not None:
            milp_badge.setText(S.t("badge.intbool"))

        self.card_knap._title.setText(f"<span style='font-weight:700'>{S.t('cards.knap.title')}</span>")
        self.card_knap._sub.setText(S.t("cards.knap.subtitle"))

        # placeholders
        cs = S.t("home.comingSoon")
        for ph in self._coming_labels:
            ph.setText(cs)

    # kept for future: theme-related tweaks
    def refresh_theme(self) -> None:
        pass
