from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox


def test_nlp_intro_buttons_open_educational_pages(window, qtbot) -> None:
    window.goto("nlp")

    qtbot.mouseClick(window.nlp_page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.nlp_example_page
    qtbot.mouseClick(window.nlp_example_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.nlp_page

    qtbot.mouseClick(window.nlp_page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.nlp_problem_page
    qtbot.mouseClick(window.nlp_problem_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.nlp_page


def test_nlp_info_dialog_is_closeable(window, qtbot) -> None:
    seen_titles: list[str] = []

    def close_dialog() -> None:
        dialog = QApplication.activeModalWidget()
        if dialog is None:
            return
        seen_titles.append(dialog.windowTitle())
        buttons = dialog.findChild(QDialogButtonBox)
        assert buttons is not None
        close_button = buttons.button(QDialogButtonBox.Close)
        assert close_button is not None
        close_button.click()

    window.goto("nlp")
    QTimer.singleShot(0, close_dialog)
    qtbot.mouseClick(window.nlp_page.btn_json_info, Qt.LeftButton)

    assert seen_titles
