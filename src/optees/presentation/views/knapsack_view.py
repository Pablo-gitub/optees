from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.presentation.controllers.knapsack_controller import KnapsackController
from optees.presentation.views.lp_view.section import Section


def _make_info_button(tooltip: str, parent: Optional[QWidget] = None) -> QPushButton:
    button = QPushButton("i", parent)
    button.setObjectName("btnSchemaInfo")
    button.setCursor(Qt.PointingHandCursor)
    button.setFixedSize(24, 24)
    button.setToolTip(tooltip)
    return button


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(520, 380)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        intro_label = QLabel(intro)
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)

        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setHtml(html)
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn:
            close_btn.setText(S.t("knapsack.info.close"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def _parse_float(text: str, *, default: float = 0.0) -> float:
    value = (text or "").strip().replace(",", ".")
    if not value:
        return default
    if "/" in value:
        a, b = value.split("/", 1)
        return float(a) / float(b)
    return float(value)


def _parse_int(text: str, *, default: int = 0) -> int:
    value = (text or "").strip().replace(",", ".")
    if not value:
        return default
    parsed = float(value)
    if not parsed.is_integer():
        raise ValueError("expected integer")
    return int(parsed)


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class _ItemRow(QWidget):
    remove_requested = Signal(int)
    name_changed = Signal(int, str)
    value_changed = Signal(int, float)
    weight_changed = Signal(int, int)

    def __init__(
        self,
        *,
        index: int,
        item: KnapsackItem,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._index = index

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.lbl_index = QLabel(str(index + 1))
        self.lbl_index.setMinimumWidth(34)

        self.edit_name = QLineEdit(item.name)
        self.edit_name.setObjectName("knapsackItemName")
        self.edit_name.setFixedHeight(28)
        self.edit_name.setMinimumWidth(170)
        self.edit_name.editingFinished.connect(self._emit_name)

        self.edit_value = QLineEdit(_fmt_number(item.value))
        self.edit_value.setObjectName("knapsackItemValue")
        self.edit_value.setFixedHeight(28)
        self.edit_value.setMaximumWidth(130)
        self.edit_value.editingFinished.connect(self._emit_value)

        self.edit_weight = QLineEdit(str(item.weight))
        self.edit_weight.setObjectName("knapsackItemWeight")
        self.edit_weight.setFixedHeight(28)
        self.edit_weight.setMaximumWidth(130)
        self.edit_weight.editingFinished.connect(self._emit_weight)

        self.btn_remove = QToolButton()
        icon = QIcon.fromTheme("edit-delete")
        if not icon.isNull():
            self.btn_remove.setIcon(icon)
        else:
            self.btn_remove.setText("x")
        self.btn_remove.setAutoRaise(True)
        self.btn_remove.setFixedSize(28, 28)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self._index))

        row.addWidget(self.lbl_index)
        row.addWidget(self.edit_name, 1)
        row.addWidget(self.edit_value)
        row.addWidget(self.edit_weight)
        row.addWidget(self.btn_remove)

        self.refresh_strings()

    def set_index(self, index: int) -> None:
        self._index = index
        self.lbl_index.setText(str(index + 1))

    def refresh_strings(self) -> None:
        self.edit_name.setPlaceholderText(S.t("knapsack.items.name_placeholder"))
        self.edit_value.setPlaceholderText(S.t("knapsack.items.value_placeholder"))
        self.edit_weight.setPlaceholderText(S.t("knapsack.items.weight_placeholder"))
        self.btn_remove.setToolTip(S.t("knapsack.items.remove"))

    def _emit_name(self) -> None:
        text = self.edit_name.text().strip()
        if text:
            self.name_changed.emit(self._index, text)

    def _emit_value(self) -> None:
        try:
            value = _parse_float(self.edit_value.text())
        except ValueError:
            self.edit_value.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
            return
        self.edit_value.setStyleSheet("")
        self.value_changed.emit(self._index, value)

    def _emit_weight(self) -> None:
        try:
            weight = _parse_int(self.edit_weight.text())
        except ValueError:
            self.edit_weight.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
            return
        self.edit_weight.setStyleSheet("")
        self.weight_changed.emit(self._index, weight)


class _ItemsSection(Section):
    add_clicked = Signal()
    remove_clicked = Signal(int)
    name_changed = Signal(int, str)
    value_changed = Signal(int, float)
    weight_changed = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.col_idx = QLabel("#")
        self.col_name = QLabel()
        self.col_value = QLabel()
        self.col_weight = QLabel()
        self.col_idx.setMinimumWidth(34)
        self.col_value.setMaximumWidth(130)
        self.col_weight.setMaximumWidth(130)
        header.addWidget(self.col_idx)
        header.addWidget(self.col_name, 1)
        header.addWidget(self.col_value)
        header.addWidget(self.col_weight)
        header.addSpacing(28)
        self.body.addLayout(header)

        self._rows = QVBoxLayout()
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(8)
        self.body.addLayout(self._rows)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self.add_clicked.emit)
        footer.addWidget(self.btn_add)
        self.body.addLayout(footer)

        self.refresh_strings()

    def set_items(self, items: list[KnapsackItem]) -> None:
        _clear_layout(self._rows)
        for index, item in enumerate(items):
            row = _ItemRow(index=index, item=item)
            row.remove_requested.connect(self.remove_clicked.emit)
            row.name_changed.connect(self.name_changed.emit)
            row.value_changed.connect(self.value_changed.emit)
            row.weight_changed.connect(self.weight_changed.emit)
            self._rows.addWidget(row)

    def rows(self) -> list[_ItemRow]:
        return self.findChildren(_ItemRow)

    def refresh_strings(self) -> None:
        self.set_title(S.t("knapsack.items.section"))
        self._hint.setText(S.t("knapsack.items.hint"))
        self.col_name.setText(S.t("knapsack.items.columns.name"))
        self.col_value.setText(S.t("knapsack.items.columns.value"))
        self.col_weight.setText(S.t("knapsack.items.columns.weight"))
        self.btn_add.setText(S.t("knapsack.items.add"))
        for row in self.rows():
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))


class KnapsackView(QWidget):
    """Editable 0/1 knapsack formulation page."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop)
        outer.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        self.page_title = QLabel()
        self.page_title.setTextFormat(Qt.RichText)
        root.addWidget(self.page_title)

        self.intro = Section()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        self.intro_text.setStyleSheet(theme.secondary_text_css(self))
        self.intro.body.addWidget(self.intro_text)

        info_actions = QHBoxLayout()
        info_actions.setContentsMargins(0, 0, 0, 0)
        info_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_problem = QPushButton()
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        info_actions.addWidget(self.btn_example)
        info_actions.addWidget(self.btn_problem)
        self.intro.body.addLayout(info_actions)
        root.addWidget(self.intro)

        self.capacity_sec = Section()
        self.btn_capacity_info = _make_info_button(S.t("knapsack.capacity.info_tooltip"), self)
        self.btn_capacity_info.clicked.connect(self._show_capacity_info)
        self.capacity_sec.set_header_action(self.btn_capacity_info)
        cap_row = QHBoxLayout()
        cap_row.setContentsMargins(0, 0, 0, 0)
        cap_row.setSpacing(8)
        self.lbl_capacity = QLabel()
        self.edit_capacity = QLineEdit()
        self.edit_capacity.setObjectName("knapsackCapacity")
        self.edit_capacity.setFixedHeight(28)
        self.edit_capacity.setMaximumWidth(160)
        self.edit_capacity.editingFinished.connect(self._on_capacity_edited)
        cap_row.addWidget(self.lbl_capacity)
        cap_row.addWidget(self.edit_capacity)
        cap_row.addStretch(1)
        self.capacity_sec.body.addLayout(cap_row)
        root.addWidget(self.capacity_sec)

        self.items_sec = _ItemsSection()
        self.btn_items_info = _make_info_button(S.t("knapsack.items.info_tooltip"), self)
        self.btn_items_info.clicked.connect(self._show_items_info)
        self.items_sec.set_header_action(self.btn_items_info)
        root.addWidget(self.items_sec)

        self.formula_sec = Section()
        self.btn_algorithm_info = _make_info_button(S.t("knapsack.formula.info_tooltip"), self)
        self.btn_algorithm_info.clicked.connect(self._show_algorithm_info)
        self.formula_sec.set_header_action(self.btn_algorithm_info)
        self.formula = QLabel()
        self.formula.setWordWrap(True)
        self.formula.setTextFormat(Qt.RichText)
        self.formula_sec.body.addWidget(self.formula)
        root.addWidget(self.formula_sec)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setObjectName("knapsackOptimizeButton")
        self.btn_optimize.clicked.connect(self._on_optimize_clicked)
        footer.addWidget(self.btn_optimize)
        root.addLayout(footer)
        root.addStretch(1)

        self._ctrl: Optional[KnapsackController] = None
        self._solve_uc = None

        self.items_sec.add_clicked.connect(self._on_add_item)
        self.items_sec.remove_clicked.connect(self._on_remove_item)
        self.items_sec.name_changed.connect(self._on_item_name_changed)
        self.items_sec.value_changed.connect(self._on_item_value_changed)
        self.items_sec.weight_changed.connect(self._on_item_weight_changed)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def set_controller(self, controller: KnapsackController) -> None:
        self._ctrl = controller
        if not self._ctrl.items():
            self._ctrl.set_capacity(5)
            self._ctrl.add_item(KnapsackItem("A", 3, 2))
            self._ctrl.add_item(KnapsackItem("B", 4, 3))
            self._ctrl.add_item(KnapsackItem("C", 5, 4))

        self._ctrl.capacity_changed.connect(self._on_capacity_changed)
        self._ctrl.items_changed.connect(self._on_items_changed)

        self._on_capacity_changed(self._ctrl.capacity())
        self._on_items_changed(self._ctrl.items())

    def set_solve_usecase(self, usecase) -> None:
        self._solve_uc = usecase

    def _on_capacity_changed(self, capacity: int) -> None:
        if self.edit_capacity.text() != str(capacity):
            self.edit_capacity.setText(str(capacity))

    def _on_items_changed(self, items: list[KnapsackItem]) -> None:
        self.items_sec.set_items(items)
        self.btn_optimize.setEnabled(bool(items))

    def _on_capacity_edited(self) -> None:
        if not self._ctrl:
            return
        try:
            capacity = _parse_int(self.edit_capacity.text())
        except ValueError:
            self.edit_capacity.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
            return
        self.edit_capacity.setStyleSheet("")
        self._ctrl.set_capacity(capacity)

    def _on_add_item(self) -> None:
        if self._ctrl:
            self._ctrl.add_item()

    def _on_remove_item(self, index: int) -> None:
        if self._ctrl:
            self._ctrl.remove_item(index)

    def _on_item_name_changed(self, index: int, value: str) -> None:
        if self._ctrl:
            self._ctrl.set_item_name(index, value)

    def _on_item_value_changed(self, index: int, value: float) -> None:
        if self._ctrl:
            self._ctrl.set_item_value(index, value)

    def _on_item_weight_changed(self, index: int, value: int) -> None:
        if self._ctrl:
            self._ctrl.set_item_weight(index, value)

    def _sync_rows_to_controller(self) -> bool:
        if not self._ctrl:
            return False
        try:
            capacity = _parse_int(self.edit_capacity.text())
        except ValueError:
            self.edit_capacity.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
            QMessageBox.warning(
                self,
                S.t("knapsack.errors.invalid_title"),
                S.t("knapsack.errors.invalid_body"),
            )
            return False
        self.edit_capacity.setStyleSheet("")
        self._ctrl.set_capacity(capacity)
        for index, row in enumerate(self.items_sec.rows()):
            name = row.edit_name.text().strip() or f"Item {index + 1}"
            try:
                value = _parse_float(row.edit_value.text())
                weight = _parse_int(row.edit_weight.text())
            except ValueError:
                QMessageBox.warning(
                    self,
                    S.t("knapsack.errors.invalid_title"),
                    S.t("knapsack.errors.invalid_body"),
                )
                return False
            self._ctrl.set_item_name(index, name)
            self._ctrl.set_item_value(index, value)
            self._ctrl.set_item_weight(index, weight)
        return True

    def _on_optimize_clicked(self) -> None:
        if not self._ctrl or not self._solve_uc:
            return
        if not self._sync_rows_to_controller():
            return
        solution = self._solve_uc.execute(self._ctrl.model())
        self.solve_completed.emit(solution)

    def _show_capacity_info(self) -> None:
        _InfoDialog(
            S.t("knapsack.capacity.info_title"),
            S.t("knapsack.capacity.info_body"),
            S.t("knapsack.capacity.info_html"),
            self,
        ).exec()

    def _show_items_info(self) -> None:
        _InfoDialog(
            S.t("knapsack.items.info_title"),
            S.t("knapsack.items.info_body"),
            S.t("knapsack.items.info_html"),
            self,
        ).exec()

    def _show_algorithm_info(self) -> None:
        _InfoDialog(
            S.t("knapsack.formula.info_title"),
            S.t("knapsack.formula.info_body"),
            S.t("knapsack.formula.info_html"),
            self,
        ).exec()

    def refresh_strings(self) -> None:
        self.page_title.setText(
            f"<span style='font-size:20px; font-weight:700'>{S.t('knapsack.header.title')}</span>"
        )
        self.intro.set_title(S.t("knapsack.header.section"))
        self.intro_text.setText(S.t("knapsack.header.description"))
        self.btn_example.setText(S.t("knapsack.header.buttons.example"))
        self.btn_problem.setText(S.t("knapsack.header.buttons.problem"))
        self.capacity_sec.set_title(S.t("knapsack.capacity.section"))
        self.btn_capacity_info.setToolTip(S.t("knapsack.capacity.info_tooltip"))
        self.lbl_capacity.setText(S.t("knapsack.capacity.label"))
        self.edit_capacity.setPlaceholderText(S.t("knapsack.capacity.placeholder"))
        self.btn_items_info.setToolTip(S.t("knapsack.items.info_tooltip"))
        self.items_sec.refresh_strings()
        self.formula_sec.set_title(S.t("knapsack.formula.section"))
        self.btn_algorithm_info.setToolTip(S.t("knapsack.formula.info_tooltip"))
        self.formula.setText(S.t("knapsack.formula.body"))
        self.btn_optimize.setText(S.t("knapsack.actions.optimize"))

    def refresh_theme(self) -> None:
        title_fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        self.page_title.setStyleSheet(f"color: {title_fg}; margin-top: 8px; margin-bottom: 8px;")
        self.intro.refresh_theme()
        self.intro_text.setStyleSheet(theme.secondary_text_css(self))
        self.capacity_sec.refresh_theme()
        self.items_sec.refresh_theme()
        self.formula_sec.refresh_theme()
        self.formula.setStyleSheet(theme.secondary_text_css(self))


def _fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.6g}"
