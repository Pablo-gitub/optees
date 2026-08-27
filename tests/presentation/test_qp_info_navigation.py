from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from optees.core.string_manager import strings as S


def test_qp_intro_buttons_open_educational_pages(window, qtbot) -> None:
    window.goto("qp")

    qtbot.mouseClick(window.qp_page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.qp_example_page
    qtbot.mouseClick(window.qp_example_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.qp_page

    qtbot.mouseClick(window.qp_page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.qp_problem_page
    qtbot.mouseClick(window.qp_problem_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.qp_page


def test_solution_page_returns_to_the_formulation(window, qtbot) -> None:
    window.goto("qp_solution")

    qtbot.mouseClick(window.qp_solution_page.btn_back, Qt.LeftButton)

    assert window.stack.currentWidget() is window.qp_page


@pytest.mark.parametrize("language", ["en", "it"])
def test_educational_pages_render_content_in_each_language(window, language: str) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        for page in (window.qp_example_page, window.qp_problem_page):
            text = page.browser.toPlainText()
            assert "Document not found" not in text
            assert len(text) > 400
    finally:
        S.set_language(previous)


@pytest.mark.parametrize(
    "button_name",
    ["btn_json_info", "btn_objective_info", "btn_solver_info"],
)
def test_info_dialogs_open_and_close(window, qtbot, button_name: str) -> None:
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

    window.goto("qp")
    QTimer.singleShot(0, close_dialog)
    qtbot.mouseClick(getattr(window.qp_page, button_name), Qt.LeftButton)

    assert seen_titles and all(title for title in seen_titles)
