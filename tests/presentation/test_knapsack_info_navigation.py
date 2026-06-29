import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox


def test_knapsack_intro_buttons_open_info_pages(window, qtbot):
    window.goto("knapsack")

    qtbot.mouseClick(window.knap_page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.knapsack_example_page

    qtbot.mouseClick(window.knapsack_example_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.knap_page

    qtbot.mouseClick(window.knap_page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.knapsack_problem_page

    qtbot.mouseClick(window.knapsack_problem_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.knap_page


def test_knapsack_info_button_opens_closeable_dialog(window, qtbot):
    window.goto("knapsack")
    seen_titles = []

    def close_dialog():
        dialog = QApplication.activeModalWidget()
        if dialog is None:
            return
        seen_titles.append(dialog.windowTitle())
        buttons = dialog.findChild(QDialogButtonBox)
        assert buttons is not None
        close_btn = buttons.button(QDialogButtonBox.Close)
        assert close_btn is not None
        close_btn.click()

    QTimer.singleShot(0, close_dialog)
    qtbot.mouseClick(window.knap_page.btn_capacity_info, Qt.LeftButton)

    assert seen_titles

