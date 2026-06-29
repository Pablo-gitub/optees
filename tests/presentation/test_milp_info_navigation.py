import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt


def test_milp_intro_buttons_open_info_pages(window, qtbot):
    window.goto("milp")

    qtbot.mouseClick(window.milp_page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.milp_example_page

    qtbot.mouseClick(window.milp_example_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.milp_page

    qtbot.mouseClick(window.milp_page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.milp_problem_page

    qtbot.mouseClick(window.milp_problem_page.btn_back, Qt.LeftButton)
    assert window.stack.currentWidget() is window.milp_page
