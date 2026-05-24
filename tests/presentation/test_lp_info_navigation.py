import pytest
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt


def test_lp_intro_buttons_open_info_pages(window, qtbot):
    window.goto("lp")

    qtbot.mouseClick(window.lp_page.intro.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.lp_example_page

    qtbot.mouseClick(window.lp_example_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.lp_page

    qtbot.mouseClick(window.lp_page.intro.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.lp_problem_page

    qtbot.mouseClick(window.lp_problem_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.lp_page
