# src/optees/presentation/views/home_view.py
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea,
    QHBoxLayout, QSizePolicy, QPushButton
)

from optees.core.assets import asset
from optees.core.string_manager import strings as S
from optees.core.design import tokens
from optees.core.theme import theme
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
        self._line = line
        root.addWidget(line)
        self.apply_theme()

        self.flow = FlowLayout(hspacing=12, vspacing=12)
        root.addLayout(self.flow)

        self.set_title(title)

    def apply_theme(self) -> None:
        self._line.setStyleSheet(f"color: {tokens(theme.is_dark()).border_strong};")

    def set_title(self, text: str) -> None:
        # simple rich-text style (unchanged for now)
        self._title_lbl.setText(f"<span style='font-size:18px; font-weight:600'>{text}</span>")

    def add_card(self, card: QWidget) -> None:
        self.flow.addWidget(card)


class HomePage(QWidget):
    go_lp = Signal()
    go_milp = Signal()
    go_knap = Signal()
    go_nlp = Signal()
    go_qp = Signal()
    go_graph = Signal()
    go_packing = Signal()
    go_regression = Signal()
    go_classification = Signal()
    go_forecasting = Signal()
    update_requested = Signal()

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

        self._update_result = None
        self._update_downloading = False
        self._update_progress: tuple[int, int] | None = None
        self.update_banner = QPushButton()
        self.update_banner.setObjectName("updateBannerButton")
        self.update_banner.setCursor(Qt.PointingHandCursor)
        self.update_banner.setVisible(False)
        # Styled globally via QPushButton#updateBannerButton.
        self.update_banner.clicked.connect(self.update_requested.emit)
        root.addWidget(self.update_banner)

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
        self.card_nlp = CardButton(
            S.t("cards.nlp.title"),
            S.t("cards.nlp.subtitle"),
            icon_path=str(asset("icons/nlp.svg")),
        )
        self.card_qp = CardButton(
            S.t("cards.qp.title"),
            S.t("cards.qp.subtitle"),
            icon_path=str(asset("icons/qp.svg")),
        )
        self.card_graph = CardButton(
            S.t("cards.graph.title"),
            S.t("cards.graph.subtitle"),
            icon_path=str(asset("icons/graph.svg")),
        )
        self.card_packing = CardButton(
            S.t("cards.packing.title"),
            S.t("cards.packing.subtitle"),
            icon_path=str(asset("icons/packing.svg")),
        )
        self.card_regression = CardButton(
            S.t("cards.regression.title"),
            S.t("cards.regression.subtitle"),
            icon_path=str(asset("icons/regression.svg")),
        )
        self.card_classification = CardButton(
            S.t("cards.classification.title"),
            S.t("cards.classification.subtitle"),
            icon_path=str(asset("icons/classification.svg")),
        )
        self.card_forecasting = CardButton(
            S.t("cards.forecasting.title"),
            S.t("cards.forecasting.subtitle"),
            icon_path=str(asset("icons/forecasting.svg")),
        )

        # wire signals
        self.card_lp.clicked.connect(self.go_lp.emit)
        self.card_milp.clicked.connect(self.go_milp.emit)
        self.card_knap.clicked.connect(self.go_knap.emit)
        self.card_nlp.clicked.connect(self.go_nlp.emit)
        self.card_qp.clicked.connect(self.go_qp.emit)
        self.card_graph.clicked.connect(self.go_graph.emit)
        self.card_packing.clicked.connect(self.go_packing.emit)
        self.card_regression.clicked.connect(self.go_regression.emit)
        self.card_classification.clicked.connect(self.go_classification.emit)
        self.card_forecasting.clicked.connect(self.go_forecasting.emit)

        # add cards to the first optimization category
        for card in (self.card_lp, self.card_milp, self.card_knap, self.card_packing):
            self.cat_lin.add_card(card)

        self.cat_nlp.add_card(self.card_nlp)
        self.cat_nlp.add_card(self.card_qp)
        root.addWidget(self.cat_nlp)

        self.cat_graph.add_card(self.card_graph)
        root.addWidget(self.cat_graph)

        self.cat_ml.add_card(self.card_regression)
        self.cat_ml.add_card(self.card_classification)
        self.cat_ml.add_card(self.card_forecasting)
        root.addWidget(self.cat_ml)
        self._coming_labels = []

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

        self.card_nlp._title.setText(f"<span style='font-weight:700'>{S.t('cards.nlp.title')}</span>")
        self.card_nlp._sub.setText(S.t("cards.nlp.subtitle"))

        self.card_qp._title.setText(f"<span style='font-weight:700'>{S.t('cards.qp.title')}</span>")
        self.card_qp._sub.setText(S.t("cards.qp.subtitle"))

        self.card_graph._title.setText(f"<span style='font-weight:700'>{S.t('cards.graph.title')}</span>")
        self.card_graph._sub.setText(S.t("cards.graph.subtitle"))

        self.card_packing._title.setText(
            f"<span style='font-weight:700'>{S.t('cards.packing.title')}</span>"
        )
        self.card_packing._sub.setText(S.t("cards.packing.subtitle"))

        self.card_regression._title.setText(
            f"<span style='font-weight:700'>{S.t('cards.regression.title')}</span>"
        )
        self.card_regression._sub.setText(S.t("cards.regression.subtitle"))
        self.card_classification._title.setText(
            f"<span style='font-weight:700'>{S.t('cards.classification.title')}</span>"
        )
        self.card_classification._sub.setText(S.t("cards.classification.subtitle"))
        self.card_forecasting._title.setText(
            f"<span style='font-weight:700'>{S.t('cards.forecasting.title')}</span>"
        )
        self.card_forecasting._sub.setText(S.t("cards.forecasting.subtitle"))

        # placeholders
        cs = S.t("home.comingSoon")
        for ph in self._coming_labels:
            ph.setText(cs)
        self._refresh_update_banner_text()

    def refresh_theme(self) -> None:
        muted = tokens(theme.is_dark()).text_muted
        for cat in (self.cat_lin, self.cat_nlp, self.cat_graph, self.cat_ml):
            cat.apply_theme()
        for ph in self._coming_labels:
            ph.setStyleSheet(f"color: {muted};")
        for card in (
            self.card_lp,
            self.card_milp,
            self.card_knap,
            self.card_nlp,
            self.card_qp,
            self.card_graph,
            self.card_packing,
            self.card_regression,
            self.card_classification,
        ):
            card._apply_theme()

    def set_update_available(self, result) -> None:
        self._update_result = result
        self._update_downloading = False
        self._update_progress = None
        self.update_banner.setEnabled(True)
        self.update_banner.setVisible(True)
        self._refresh_update_banner_text()

    def set_update_download_in_progress(self, result=None) -> None:
        if result is not None:
            self._update_result = result
        self._update_downloading = True
        self._update_progress = None
        self.update_banner.setEnabled(False)
        self.update_banner.setVisible(True)
        self._refresh_update_banner_text()

    def set_update_download_progress(self, downloaded: int, total: int) -> None:
        self._update_downloading = True
        self._update_progress = (max(0, downloaded), total)
        self._refresh_update_banner_text()

    def hide_update_banner(self) -> None:
        self._update_downloading = False
        self._update_progress = None
        self._update_result = None
        self.update_banner.setVisible(False)

    def _refresh_update_banner_text(self) -> None:
        if not self.update_banner.isVisible() and self._update_result is None:
            return
        version = getattr(self._update_result, "latest_version", None) or "-"
        if self._update_downloading:
            downloaded, total = self._update_progress or (0, -1)
            if total > 0:
                percent = min(100, round(downloaded * 100 / total))
                self.update_banner.setText(
                    S.t(
                        "updates.banner.downloading_progress",
                        version=version,
                        percent=percent,
                    )
                )
            else:
                self.update_banner.setText(
                    S.t(
                        "updates.banner.downloading_bytes",
                        version=version,
                        downloaded=_format_megabytes(downloaded),
                    )
                )
        else:
            self.update_banner.setText(S.t("updates.banner.available", version=version))


def _format_megabytes(byte_count: int) -> str:
    return f"{max(0, byte_count) / (1024 * 1024):.1f} MB"
