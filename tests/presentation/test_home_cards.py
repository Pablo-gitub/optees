from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget

from optees.core.string_manager import strings as S
from optees.presentation.views.home_view import HomePage, CARD_W, CARD_H
from optees.presentation.views.widgets.card_button import CardButton
from optees.presentation.views.widgets.flow_layout import FlowLayout


def test_card_button_dimensions_and_size_hints(qtbot) -> None:
    card = CardButton(
        "Short Title",
        "Short subtitle description.",
    )
    qtbot.addWidget(card)

    assert card.width() == CARD_W
    assert card.width() == 380
    assert card.minimumHeight() == CARD_H
    assert card.minimumHeight() == 160
    assert card.hasHeightForWidth() is True

    hint = card.sizeHint()
    assert hint.width() == 380
    assert hint.height() >= 160
    assert card.minimumSizeHint() == hint


def test_card_button_height_grows_with_longer_content(qtbot) -> None:
    short_card = CardButton("Title", "Short description.")
    qtbot.addWidget(short_card)

    long_card = CardButton(
        "A Much Longer Title That Might Wrap Over Multiple Lines",
        "This is an extensive subtitle description that contains multiple sentences to ensure "
        "that the text column wraps across many lines and proves that the card's height grows "
        "appropriately to accommodate all the text without clipping.",
    )
    qtbot.addWidget(long_card)

    assert long_card.sizeHint().height() > short_card.sizeHint().height()
    assert long_card.heightForWidth(CARD_W) == long_card.sizeHint().height()


def test_flow_layout_aligns_row_heights(qtbot) -> None:
    container = QWidget()
    qtbot.addWidget(container)
    layout = FlowLayout(container, margin=0, hspacing=10, vspacing=10)

    short_card = CardButton("Short", "Brief text.")
    long_card = CardButton(
        "Longer Card",
        "Multiple lines of description text to ensure this card requires more vertical space than the first.",
    )
    layout.addWidget(short_card)
    layout.addWidget(long_card)

    container.resize(900, 400)
    container.show()
    container.layout().activate()

    # Both cards are on the same line at 900px width (380 + 10 + 380 = 770 < 900)
    assert short_card.y() == long_card.y()
    # Their heights must be equalized to the row's maximum height
    assert short_card.height() == long_card.height()
    assert short_card.height() == long_card.sizeHint().height()


def test_nlp_and_qp_cards_in_home_page_render_without_clipping(window, qtbot) -> None:
    home = window.home_page
    card_nlp = home.card_nlp
    card_qp = home.card_qp

    assert card_nlp.width() == 380
    assert card_nlp.height() >= 160
    assert card_qp.width() == 380
    assert card_qp.height() >= 160

    # In Italian (default or set), title fits cleanly on a single line
    S.set_language("it")
    home.refresh_strings()
    window.resize(1280, 850)
    window.show()
    qtbot.waitExposed(window)

    # Both nonlinear category cards share the same row height and are at least CARD_H
    assert card_nlp.height() == card_qp.height()
    assert card_qp.height() >= CARD_H
    assert card_nlp.height() >= card_nlp.sizeHint().height()
    assert card_qp.height() >= card_qp.sizeHint().height()

    # Text must be fully contained within card geometry without clipping
    assert card_nlp._title.text() != ""
    assert card_nlp._sub.text() != ""
    assert card_nlp._title.geometry().bottom() < card_nlp.height()
    assert card_nlp._sub.geometry().bottom() < card_nlp.height()

    assert card_qp._title.text() != ""
    assert card_qp._sub.text() != ""
    assert card_qp._title.geometry().bottom() < card_qp.height()
    assert card_qp._sub.geometry().bottom() < card_qp.height()

    # Title fits in one line in Italian with 380px card width
    assert card_nlp._title.height() <= 28

    # Switch to English and verify single-line title, row alignment, and bounds
    S.set_language("en")
    home.refresh_strings()
    assert card_nlp._title.text() != ""
    assert card_nlp._title.height() <= 28
    assert card_nlp.height() == card_qp.height()
    assert card_qp._sub.geometry().bottom() < card_qp.height()
