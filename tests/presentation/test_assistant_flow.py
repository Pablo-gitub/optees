from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt


def test_floating_assistant_button_navigates_to_assistant(window, qtbot):
    window.goto("home")
    assert window.assistant_bubble.isVisible()

    qtbot.mouseClick(window.assistant_bubble, Qt.LeftButton)

    assert window.stack.currentWidget() is window.assistant_page
    assert not window.assistant_bubble.isVisible()


def test_assistant_view_analyzes_prompt_and_shows_loadable_json(window, qtbot):
    window.goto("assistant")
    window.assistant_page.prompt.setPlainText(
        "Maximize 3x + 5y subject to 2x + y <= 10; x + 3y <= 12."
    )

    qtbot.mouseClick(window.assistant_page.btn_analyze, Qt.LeftButton)

    assert "Linear" in window.assistant_page.lbl_family_value.text() or (
        "Lineare" in window.assistant_page.lbl_family_value.text()
    )
    assert window.assistant_page.json_preview.isVisible()
    assert '"variables"' in window.assistant_page.json_preview.toPlainText()
    assert window.assistant_page.btn_load.isVisible()


def test_assistant_view_recognizes_plain_bag_prompt(window, qtbot):
    window.goto("assistant")
    window.assistant_page.prompt.setPlainText(
        "maximize my bag, I have 6 objects a laptop size 6 value 20, "
        "a bottle of water size 2 value 1, earphone size 1 value 5, "
        "my phone size 3 value 10, cigarets size 2 value 3, "
        "a book size 2 value 2, my bag is only big size 10"
    )

    qtbot.mouseClick(window.assistant_page.btn_analyze, Qt.LeftButton)

    assert "Knapsack" in window.assistant_page.lbl_family_value.text()
    preview = window.assistant_page.json_preview.toPlainText()
    assert '"capacity": 10.0' in preview
    assert '"laptop"' in preview
    assert window.assistant_page.btn_load.isVisible()


@pytest.mark.parametrize(
    ("language", "expected", "unexpected"),
    [("it", "capacita", "capacity"), ("en", "capacity", "capacita")],
)
def test_assistant_view_answers_in_the_language_from_settings(
    window, qtbot, language, expected, unexpected
):
    """The prompt is English, but the answer must follow the Settings language."""
    from optees.core.string_manager import strings as S

    previous = S.current_language()
    S.set_language(language)
    try:
        window.goto("assistant")
        window.assistant_page.prompt.setPlainText(
            "I keep filling a box with the same kind of piece and I can put in "
            "as many as I want."
        )

        qtbot.mouseClick(window.assistant_page.btn_analyze, Qt.LeftButton)

        missing = window.assistant_page.missing_label.text().casefold()
        assert expected in missing
        assert unexpected not in missing
    finally:
        S.set_language(previous)
