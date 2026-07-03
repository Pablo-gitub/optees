from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.domain.models.knapsack.fractional_knapsack_model import FractionalKnapsackModel
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.models.knapsack.unbounded_knapsack_model import UnboundedKnapsackModel
from optees.domain.value_objects.knapsack.variant import KnapsackVariant
from optees.presentation.controllers.knapsack_controller import KnapsackController
from optees.presentation.views.lp_view.section import Section
from optees.utility.data_adapters.knapsack_burkardt_adapter import load_knapsack_burkardt


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


_ITEM_INDEX_WIDTH = 44
_ITEM_NUMERIC_COLUMN_WIDTH = 130
_ITEM_REMOVE_BUTTON_WIDTH = 28


def _item_var_name(index: int) -> str:
    return f"X{index + 1}"


def _is_default_item(item: KnapsackItem, index: int) -> bool:
    return (
        item.name == f"Item {index + 1}"
        and float(item.value) == 0.0
        and int(item.weight) == 0
    )


class _ItemRow(QWidget):
    remove_requested = Signal(int)
    name_changed = Signal(int, str)
    value_changed = Signal(int, float)
    weight_changed = Signal(int, int)
    max_quantity_changed = Signal(int, int)

    def __init__(
        self,
        *,
        index: int,
        item: KnapsackItem,
        max_quantity: int = 1,
        show_max_quantity: bool = False,
        weight_is_float: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._weight_is_float = weight_is_float

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        is_default_item = _is_default_item(item, index)

        self.lbl_index = QLabel(_item_var_name(index))
        self.lbl_index.setFixedWidth(_ITEM_INDEX_WIDTH)

        self.edit_name = QLineEdit("" if is_default_item else item.name)
        self.edit_name.setObjectName("knapsackItemName")
        self.edit_name.setFixedHeight(28)
        self.edit_name.setMinimumWidth(170)
        self.edit_name.editingFinished.connect(self._emit_name)

        self.edit_value = QLineEdit("" if is_default_item else _fmt_number(item.value))
        self.edit_value.setObjectName("knapsackItemValue")
        self.edit_value.setFixedHeight(28)
        self.edit_value.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.edit_value.editingFinished.connect(self._emit_value)

        self.edit_weight = QLineEdit("" if is_default_item else str(item.weight))
        self.edit_weight.setObjectName("knapsackItemWeight")
        self.edit_weight.setFixedHeight(28)
        self.edit_weight.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.edit_weight.editingFinished.connect(self._emit_weight)

        self.edit_max_quantity = QLineEdit("" if max_quantity == 1 else str(max_quantity))
        self.edit_max_quantity.setObjectName("knapsackItemMaxQuantity")
        self.edit_max_quantity.setFixedHeight(28)
        self.edit_max_quantity.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.edit_max_quantity.editingFinished.connect(self._emit_max_quantity)
        self.edit_max_quantity.setVisible(show_max_quantity)

        self.btn_remove = QToolButton()
        icon = QIcon.fromTheme("edit-delete")
        if not icon.isNull():
            self.btn_remove.setIcon(icon)
        else:
            self.btn_remove.setText("x")
        self.btn_remove.setAutoRaise(True)
        self.btn_remove.setFixedSize(_ITEM_REMOVE_BUTTON_WIDTH, 28)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self._index))

        row.addWidget(self.lbl_index)
        row.addWidget(self.edit_name, 1)
        row.addWidget(self.edit_value)
        row.addWidget(self.edit_weight)
        row.addWidget(self.edit_max_quantity)
        row.addWidget(self.btn_remove)

        self.refresh_strings()

    def set_index(self, index: int) -> None:
        self._index = index
        self.lbl_index.setText(_item_var_name(index))

    def refresh_strings(self) -> None:
        self.edit_name.setPlaceholderText(S.t("knapsack.items.name_placeholder"))
        self.edit_value.setPlaceholderText(S.t("knapsack.items.value_placeholder"))
        self.edit_weight.setPlaceholderText(S.t("knapsack.items.weight_placeholder"))
        self.edit_max_quantity.setPlaceholderText(S.t("knapsack.items.max_quantity_placeholder"))
        self.btn_remove.setToolTip(S.t("knapsack.items.remove"))

    def set_show_max_quantity(self, show: bool) -> None:
        self.edit_max_quantity.setVisible(show)

    def set_weight_is_float(self, enabled: bool) -> None:
        self._weight_is_float = enabled

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
            if self._weight_is_float:
                _parse_float(self.edit_weight.text())
                self.edit_weight.setStyleSheet("")
                return
            weight = _parse_int(self.edit_weight.text())
        except ValueError:
            self.edit_weight.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
            return
        self.edit_weight.setStyleSheet("")
        self.weight_changed.emit(self._index, weight)

    def _emit_max_quantity(self) -> None:
        try:
            max_quantity = _parse_int(self.edit_max_quantity.text(), default=1)
        except ValueError:
            self.edit_max_quantity.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
            return
        self.edit_max_quantity.setStyleSheet("")
        self.max_quantity_changed.emit(self._index, max_quantity)


class _ItemsSection(Section):
    add_clicked = Signal()
    remove_clicked = Signal(int)
    name_changed = Signal(int, str)
    value_changed = Signal(int, float)
    weight_changed = Signal(int, int)
    max_quantity_changed = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)
        self._hint_key = "knapsack.items.hint"

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.col_idx = QLabel()
        self.col_name = QLabel()
        self.col_value = QLabel()
        self.col_weight = QLabel()
        self.col_max_quantity = QLabel()
        self.col_idx.setFixedWidth(_ITEM_INDEX_WIDTH)
        self.col_value.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.col_weight.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.col_max_quantity.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        for label in (
            self.col_idx,
            self.col_name,
            self.col_value,
            self.col_weight,
            self.col_max_quantity,
        ):
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.addWidget(self.col_idx)
        header.addWidget(self.col_name, 1)
        header.addWidget(self.col_value)
        header.addWidget(self.col_weight)
        header.addWidget(self.col_max_quantity)
        header.addSpacing(_ITEM_REMOVE_BUTTON_WIDTH)
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

        self._show_max_quantity = False
        self._weight_is_float = False
        self.refresh_strings()

    def set_items(
        self,
        items: list[KnapsackItem],
        max_quantities: Optional[list[int]] = None,
    ) -> None:
        _clear_layout(self._rows)
        max_quantities = max_quantities or []
        for index, item in enumerate(items):
            max_quantity = max_quantities[index] if index < len(max_quantities) else 1
            row = _ItemRow(
                index=index,
                item=item,
                max_quantity=max_quantity,
                show_max_quantity=self._show_max_quantity,
                weight_is_float=self._weight_is_float,
            )
            row.remove_requested.connect(self.remove_clicked.emit)
            row.name_changed.connect(self.name_changed.emit)
            row.value_changed.connect(self.value_changed.emit)
            row.weight_changed.connect(self.weight_changed.emit)
            row.max_quantity_changed.connect(self.max_quantity_changed.emit)
            self._rows.addWidget(row)

    def rows(self) -> list[_ItemRow]:
        rows: list[_ItemRow] = []
        for i in range(self._rows.count()):
            widget = self._rows.itemAt(i).widget()
            if isinstance(widget, _ItemRow):
                rows.append(widget)
        return rows

    def refresh_strings(self) -> None:
        self.set_title(S.t("knapsack.items.section"))
        self._hint.setText(S.t(self._hint_key))
        self.col_idx.setText(S.t("knapsack.items.columns.variable"))
        self.col_name.setText(S.t("knapsack.items.columns.name"))
        self.col_value.setText(S.t("knapsack.items.columns.value"))
        self.col_weight.setText(S.t("knapsack.items.columns.weight"))
        self.col_max_quantity.setText(S.t("knapsack.items.columns.max_quantity"))
        self.btn_add.setText(S.t("knapsack.items.add"))
        for row in self.rows():
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))

    def set_bounded_mode(self, enabled: bool) -> None:
        self._show_max_quantity = enabled
        self.col_max_quantity.setVisible(enabled)
        for row in self.rows():
            row.set_show_max_quantity(enabled)

    def set_weight_is_float(self, enabled: bool) -> None:
        self._weight_is_float = enabled
        for row in self.rows():
            row.set_weight_is_float(enabled)

    def set_hint_key(self, key: str) -> None:
        self._hint_key = key
        self._hint.setText(S.t(self._hint_key))


class KnapsackView(QWidget):
    """Editable knapsack formulation page with variant selection."""

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
        self._variant = KnapsackVariant.ZERO_ONE

        self.intro = Section()
        self.btn_import_burkardt = QPushButton()
        self.btn_import_burkardt.setObjectName("knapsackImportBurkardtButton")
        self.btn_import_burkardt.setCursor(Qt.PointingHandCursor)
        self.btn_import_burkardt.clicked.connect(self._on_import_burkardt)
        self.intro.set_header_action(self.btn_import_burkardt)

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

        self.variant_sec = Section()
        self.variant_sec.setObjectName("knapsackVariantSection")
        self.variant_hint = QLabel()
        self.variant_hint.setWordWrap(True)
        self.variant_hint.setStyleSheet(theme.secondary_text_css(self))
        self.variant_sec.body.addWidget(self.variant_hint)

        self.variant_group = QButtonGroup(self)
        self.variant_group.setExclusive(True)
        self.variant_buttons: dict[KnapsackVariant, QPushButton] = {}
        variant_row = QHBoxLayout()
        variant_row.setContentsMargins(0, 0, 0, 0)
        variant_row.setSpacing(8)
        for variant in KnapsackVariant:
            button = QPushButton()
            button.setCheckable(True)
            button.setObjectName(f"knapsackVariant_{variant.value}")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, v=variant: self._set_variant(v))
            self.variant_group.addButton(button)
            self.variant_buttons[variant] = button
            variant_row.addWidget(button)
        variant_row.addStretch(1)
        self.variant_sec.body.addLayout(variant_row)

        self.variant_description = QLabel()
        self.variant_description.setWordWrap(True)
        self.variant_description.setStyleSheet(theme.secondary_text_css(self))
        self.variant_sec.body.addWidget(self.variant_description)
        root.addWidget(self.variant_sec)

        self.variant_placeholder_sec = Section()
        self.variant_placeholder_sec.setObjectName("knapsackVariantPlaceholder")
        self.variant_placeholder_text = QLabel()
        self.variant_placeholder_text.setWordWrap(True)
        self.variant_placeholder_text.setStyleSheet(theme.secondary_text_css(self))
        self.variant_placeholder_sec.body.addWidget(self.variant_placeholder_text)
        root.addWidget(self.variant_placeholder_sec)

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
        self._bounded_solve_uc = None
        self._unbounded_solve_uc = None
        self._fractional_solve_uc = None
        self._bounded_max_quantities: list[int] = []
        self._last_solved_model = None

        self.items_sec.add_clicked.connect(self._on_add_item)
        self.items_sec.remove_clicked.connect(self._on_remove_item)
        self.items_sec.name_changed.connect(self._on_item_name_changed)
        self.items_sec.value_changed.connect(self._on_item_value_changed)
        self.items_sec.weight_changed.connect(self._on_item_weight_changed)
        self.items_sec.max_quantity_changed.connect(self._on_item_max_quantity_changed)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self._apply_variant()
        self.refresh_strings()
        self.refresh_theme()

    def set_controller(self, controller: KnapsackController) -> None:
        self._ctrl = controller
        if not self._ctrl.items():
            self._ctrl.set_capacity(0)
            self._ctrl.add_item()
            self._ctrl.add_item()

        self._ctrl.capacity_changed.connect(self._on_capacity_changed)
        self._ctrl.items_changed.connect(self._on_items_changed)

        self._on_capacity_changed(self._ctrl.capacity())
        self._on_items_changed(self._ctrl.items())

    def set_solve_usecase(self, usecase) -> None:
        self._solve_uc = usecase

    def set_bounded_solve_usecase(self, usecase) -> None:
        self._bounded_solve_uc = usecase

    def set_unbounded_solve_usecase(self, usecase) -> None:
        self._unbounded_solve_uc = usecase

    def set_fractional_solve_usecase(self, usecase) -> None:
        self._fractional_solve_uc = usecase

    def current_problem_model(self):
        if self._last_solved_model is not None:
            return self._last_solved_model
        return self._ctrl.model() if self._ctrl else None

    def _on_capacity_changed(self, capacity: int) -> None:
        text = "" if capacity == 0 else str(capacity)
        if self.edit_capacity.text() != text:
            self.edit_capacity.setText(text)

    def _on_items_changed(self, items: list[KnapsackItem]) -> None:
        self._resize_bounded_quantities(len(items))
        self.items_sec.set_items(items, self._bounded_max_quantities)
        self._update_optimize_enabled()

    def _on_capacity_edited(self) -> None:
        if not self._ctrl:
            return
        if self._variant is KnapsackVariant.FRACTIONAL:
            try:
                _parse_float(self.edit_capacity.text())
            except ValueError:
                self.edit_capacity.setStyleSheet("border: 1px solid rgba(220,53,69,.90);")
                return
            self.edit_capacity.setStyleSheet("")
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

    def _on_item_max_quantity_changed(self, index: int, value: int) -> None:
        self._resize_bounded_quantities(index + 1)
        self._bounded_max_quantities[index] = value

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
                if self._variant is KnapsackVariant.BOUNDED:
                    max_quantity = _parse_int(row.edit_max_quantity.text(), default=1)
                    if max_quantity < 0:
                        raise ValueError("max quantity must be non-negative")
            except ValueError:
                QMessageBox.warning(
                    self,
                    S.t("knapsack.errors.invalid_title"),
                    S.t("knapsack.errors.invalid_body"),
                )
                return False
            if self._variant is KnapsackVariant.BOUNDED:
                self._resize_bounded_quantities(index + 1)
                self._bounded_max_quantities[index] = max_quantity
            self._ctrl.set_item_name(index, name)
            self._ctrl.set_item_value(index, value)
            self._ctrl.set_item_weight(index, weight)
        return True

    def _on_optimize_clicked(self) -> None:
        if not self._ctrl:
            return

        if self._variant is KnapsackVariant.FRACTIONAL:
            if not self._fractional_solve_uc:
                return
            try:
                model = self._build_fractional_model()
            except ValueError:
                QMessageBox.warning(
                    self,
                    S.t("knapsack.errors.invalid_title"),
                    S.t("knapsack.errors.invalid_body"),
                )
                return
            solution = self._fractional_solve_uc.execute(model)
        else:
            if not self._sync_rows_to_controller():
                return

            if self._variant is KnapsackVariant.ZERO_ONE:
                if not self._solve_uc:
                    return
                model = self._ctrl.model()
                solution = self._solve_uc.execute(model)
            elif self._variant is KnapsackVariant.BOUNDED:
                if not self._bounded_solve_uc:
                    return
                model = self._build_bounded_model()
                solution = self._bounded_solve_uc.execute(model)
            elif self._variant is KnapsackVariant.UNBOUNDED:
                if not self._unbounded_solve_uc:
                    return
                model = self._build_unbounded_model()
                solution = self._unbounded_solve_uc.execute(model)
            else:
                return

        self._last_solved_model = model
        self.solve_completed.emit(solution)

    def _on_import_burkardt(self) -> None:
        if self._variant is not KnapsackVariant.ZERO_ONE:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("knapsack.import.dialog_title"),
            "",
            "Burkardt knapsack (*.txt);;All files (*)",
        )
        if not path:
            return

        try:
            file_path = Path(path)
            instance = _infer_burkardt_instance(file_path)
            data = load_knapsack_burkardt(str(file_path.parent), instance)
            items = tuple(
                KnapsackItem(
                    f"{instance}_item_{i + 1}",
                    value,
                    weight,
                )
                for i, (value, weight) in enumerate(zip(data["values"], data["weights"]))
            )
            model = Knapsack01Model.from_parts(items, capacity=data["capacity"])
        except Exception as exc:
            QMessageBox.warning(
                self,
                S.t("knapsack.import.error_title"),
                S.t("knapsack.import.error_body", detail=str(exc)),
            )
            return

        if self._ctrl:
            self._ctrl.load_model(model)

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
        self.btn_import_burkardt.setText(S.t("knapsack.import.burkardt_button"))
        self.btn_import_burkardt.setToolTip(S.t("knapsack.import.burkardt_tooltip"))
        self.intro_text.setText(S.t("knapsack.header.description"))
        self.btn_example.setText(S.t("knapsack.header.buttons.example"))
        self.btn_problem.setText(S.t("knapsack.header.buttons.problem"))
        self.variant_sec.set_title(S.t("knapsack.variant.section"))
        self.variant_hint.setText(S.t("knapsack.variant.hint"))
        for variant, button in self.variant_buttons.items():
            button.setText(S.t(f"knapsack.variant.labels.{variant.value}"))
        self.capacity_sec.set_title(S.t("knapsack.capacity.section"))
        self.btn_capacity_info.setToolTip(S.t("knapsack.capacity.info_tooltip"))
        self.lbl_capacity.setText(S.t("knapsack.capacity.label"))
        self.edit_capacity.setPlaceholderText(S.t("knapsack.capacity.placeholder"))
        self.btn_items_info.setToolTip(S.t("knapsack.items.info_tooltip"))
        self.items_sec.refresh_strings()
        self.formula_sec.set_title(S.t("knapsack.formula.section"))
        self.btn_algorithm_info.setToolTip(S.t("knapsack.formula.info_tooltip"))
        self.btn_optimize.setText(S.t("knapsack.actions.optimize"))
        self._apply_variant()

    def refresh_theme(self) -> None:
        title_fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        self.page_title.setStyleSheet(f"color: {title_fg}; margin-top: 8px; margin-bottom: 8px;")
        self.intro.refresh_theme()
        self.intro_text.setStyleSheet(theme.secondary_text_css(self))
        self.variant_sec.refresh_theme()
        self.variant_hint.setStyleSheet(theme.secondary_text_css(self))
        self.variant_description.setStyleSheet(theme.secondary_text_css(self))
        self.variant_placeholder_sec.refresh_theme()
        self.variant_placeholder_text.setStyleSheet(theme.secondary_text_css(self))
        self.capacity_sec.refresh_theme()
        self.items_sec.refresh_theme()
        self.formula_sec.refresh_theme()
        self.formula.setStyleSheet(theme.secondary_text_css(self))

    def current_variant(self) -> KnapsackVariant:
        return self._variant

    def _set_variant(self, variant: KnapsackVariant) -> None:
        if self._variant is variant:
            self._apply_variant()
            return
        self._variant = variant
        self._apply_variant()

    def _apply_variant(self) -> None:
        is_zero_one = self._variant is KnapsackVariant.ZERO_ONE
        is_bounded = self._variant is KnapsackVariant.BOUNDED
        is_unbounded = self._variant is KnapsackVariant.UNBOUNDED
        is_fractional = self._variant is KnapsackVariant.FRACTIONAL
        is_executable = is_zero_one or is_bounded or is_unbounded or is_fractional
        button = self.variant_buttons.get(self._variant)
        if button is not None and not button.isChecked():
            button.setChecked(True)

        self.variant_description.setText(
            S.t(f"knapsack.variant.descriptions.{self._variant.value}")
        )
        self.variant_placeholder_sec.setVisible(not is_executable)
        self.capacity_sec.setVisible(is_executable)
        self.items_sec.setVisible(is_executable)
        self.items_sec.set_bounded_mode(is_bounded)
        self.items_sec.set_weight_is_float(is_fractional)
        self.items_sec.set_hint_key(
            "knapsack.items.fractional_hint"
            if is_fractional
            else "knapsack.items.hint"
        )
        self.formula_sec.setVisible(is_executable)
        formula_key = "knapsack.formula.body"
        if is_bounded:
            formula_key = "knapsack.formula.bounded_body"
        elif is_unbounded:
            formula_key = "knapsack.formula.unbounded_body"
        elif is_fractional:
            formula_key = "knapsack.formula.fractional_body"
        self.formula.setText(S.t(formula_key))
        self.btn_import_burkardt.setEnabled(is_zero_one)

        if not is_executable:
            self.variant_placeholder_sec.set_title(
                S.t(
                    "knapsack.variant.placeholder_title",
                    variant=S.t(f"knapsack.variant.labels.{self._variant.value}"),
                )
            )
            self.variant_placeholder_text.setText(
                S.t(f"knapsack.variant.placeholders.{self._variant.value}")
            )
        self._update_optimize_enabled()

    def _update_optimize_enabled(self) -> None:
        items = self._ctrl.items() if self._ctrl else []
        self.btn_optimize.setEnabled(
            self._variant
            in (
                KnapsackVariant.ZERO_ONE,
                KnapsackVariant.BOUNDED,
                KnapsackVariant.UNBOUNDED,
                KnapsackVariant.FRACTIONAL,
            )
            and bool(items)
        )

    def _resize_bounded_quantities(self, item_count: int) -> None:
        if len(self._bounded_max_quantities) < item_count:
            self._bounded_max_quantities.extend(
                [1] * (item_count - len(self._bounded_max_quantities))
            )
        elif len(self._bounded_max_quantities) > item_count:
            del self._bounded_max_quantities[item_count:]

    def _build_bounded_model(self) -> BoundedKnapsackModel:
        if not self._ctrl:
            raise ValueError("missing knapsack controller")
        items = []
        for index, item in enumerate(self._ctrl.items()):
            max_quantity = (
                self._bounded_max_quantities[index]
                if index < len(self._bounded_max_quantities)
                else 1
            )
            items.append(
                BoundedKnapsackItem(
                    item.name,
                    item.value,
                    item.weight,
                    max_quantity,
                )
            )
        return BoundedKnapsackModel.from_parts(
            tuple(items),
            capacity=self._ctrl.capacity(),
        )

    def _build_unbounded_model(self) -> UnboundedKnapsackModel:
        if not self._ctrl:
            raise ValueError("missing knapsack controller")
        items = tuple(
            UnboundedKnapsackItem(
                item.name,
                item.value,
                item.weight,
            )
            for item in self._ctrl.items()
        )
        return UnboundedKnapsackModel.from_parts(
            items,
            capacity=self._ctrl.capacity(),
        )

    def _build_fractional_model(self) -> FractionalKnapsackModel:
        capacity = _parse_float(self.edit_capacity.text())
        items = []
        for index, row in enumerate(self.items_sec.rows()):
            name = row.edit_name.text().strip() or f"Item {index + 1}"
            value = _parse_float(row.edit_value.text())
            weight = _parse_float(row.edit_weight.text())
            items.append(FractionalKnapsackItem(name, value, weight))
        return FractionalKnapsackModel.from_parts(
            tuple(items),
            capacity=capacity,
        )


def _fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.6g}"


def _infer_burkardt_instance(path: Path) -> str:
    stem = path.stem
    for suffix in ("_c", "_w", "_p", "_s"):
        if stem.lower().endswith(suffix):
            return stem[: -len(suffix)].lower()
    raise ValueError("Select a Burkardt file named <instance>_c.txt, _w.txt, _p.txt or _s.txt.")
