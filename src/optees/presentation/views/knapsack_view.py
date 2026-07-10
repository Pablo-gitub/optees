from __future__ import annotations

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
from optees.core.design import tokens
from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.entities.knapsack.multi_dimensional_item import (
    MultiDimensionalKnapsackItem,
)
from optees.domain.entities.knapsack.multi_dimensional_quantity_solution import (
    MultiDimensionalQuantityKnapsackSolution,
)
from optees.domain.entities.knapsack.multi_dimensional_resource import (
    MultiDimensionalKnapsackResource,
)
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.domain.models.knapsack.fractional_knapsack_model import FractionalKnapsackModel
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)
from optees.domain.models.knapsack.unbounded_knapsack_model import UnboundedKnapsackModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.knapsack.variant import KnapsackVariant
from optees.domain.value_objects.milp.integrality import Integrality
from optees.presentation.controllers.knapsack_controller import KnapsackController
from optees.presentation.views.lp_view.section import Section
from optees.utility.knapsack_json_io import (
    DOMAIN_BOUNDED,
    DOMAIN_FRACTIONAL,
    DOMAIN_UNBOUNDED,
    DOMAIN_ZERO_ONE,
    VARIANT_BOUNDED,
    VARIANT_FRACTIONAL,
    VARIANT_MULTI_DIMENSIONAL,
    VARIANT_UNBOUNDED,
    VARIANT_ZERO_ONE,
    KnapsackJsonProblem,
    knapsack_problem_from_file,
)


def _invalid_border() -> str:
    """Inline stylesheet for an invalid input field (theme-aware danger color)."""
    return f"border: 1px solid {tokens(theme.is_dark()).danger};"


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

_MULTI_DOMAIN_ZERO_ONE = "zero_one"
_MULTI_DOMAIN_BOUNDED = "bounded"
_MULTI_DOMAIN_UNBOUNDED = "unbounded"
_MULTI_DOMAIN_FRACTIONAL = "fractional"
_MULTI_DOMAIN_VALUES = (
    _MULTI_DOMAIN_ZERO_ONE,
    _MULTI_DOMAIN_BOUNDED,
    _MULTI_DOMAIN_UNBOUNDED,
    _MULTI_DOMAIN_FRACTIONAL,
)

_JSON_VARIANT_TO_UI_VARIANT = {
    VARIANT_ZERO_ONE: KnapsackVariant.ZERO_ONE,
    VARIANT_BOUNDED: KnapsackVariant.BOUNDED,
    VARIANT_UNBOUNDED: KnapsackVariant.UNBOUNDED,
    VARIANT_FRACTIONAL: KnapsackVariant.FRACTIONAL,
    VARIANT_MULTI_DIMENSIONAL: KnapsackVariant.MULTI_DIMENSIONAL,
}

_JSON_DOMAIN_TO_MULTI_DOMAIN = {
    DOMAIN_ZERO_ONE: _MULTI_DOMAIN_ZERO_ONE,
    DOMAIN_BOUNDED: _MULTI_DOMAIN_BOUNDED,
    DOMAIN_UNBOUNDED: _MULTI_DOMAIN_UNBOUNDED,
    DOMAIN_FRACTIONAL: _MULTI_DOMAIN_FRACTIONAL,
}


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

        self.btn_remove.setObjectName("rowRemoveButton")
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
            self.edit_value.setStyleSheet(_invalid_border())
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
            self.edit_weight.setStyleSheet(_invalid_border())
            return
        self.edit_weight.setStyleSheet("")
        self.weight_changed.emit(self._index, weight)

    def _emit_max_quantity(self) -> None:
        try:
            max_quantity = _parse_int(self.edit_max_quantity.text(), default=1)
        except ValueError:
            self.edit_max_quantity.setStyleSheet(_invalid_border())
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


class _ResourceRow(QWidget):
    remove_requested = Signal(int)
    changed = Signal()

    def __init__(self, *, index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._index = index

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.lbl_index = QLabel(f"R{index + 1}")
        self.lbl_index.setFixedWidth(_ITEM_INDEX_WIDTH)

        self.edit_name = QLineEdit()
        self.edit_name.setObjectName("knapsackResourceName")
        self.edit_name.setFixedHeight(28)
        self.edit_name.setMinimumWidth(170)
        self.edit_name.editingFinished.connect(self.changed.emit)

        self.edit_capacity = QLineEdit()
        self.edit_capacity.setObjectName("knapsackResourceCapacity")
        self.edit_capacity.setFixedHeight(28)
        self.edit_capacity.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.edit_capacity.editingFinished.connect(self.changed.emit)

        self.btn_remove = QToolButton()

        self.btn_remove.setObjectName("rowRemoveButton")
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
        row.addWidget(self.edit_capacity)
        row.addWidget(self.btn_remove)

        self.refresh_strings()

    def set_index(self, index: int) -> None:
        self._index = index
        self.lbl_index.setText(f"R{index + 1}")

    def refresh_strings(self) -> None:
        self.edit_name.setPlaceholderText(S.t("knapsack.resources.name_placeholder"))
        self.edit_capacity.setPlaceholderText(S.t("knapsack.resources.capacity_placeholder"))
        self.btn_remove.setToolTip(S.t("knapsack.resources.remove"))


class _ResourcesSection(Section):
    add_clicked = Signal()
    remove_clicked = Signal(int)
    resources_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)

        self._header = QHBoxLayout()
        self._header.setContentsMargins(0, 0, 0, 0)
        self._header.setSpacing(8)
        self.body.addLayout(self._header)

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

    def add_resource(self) -> None:
        row = _ResourceRow(index=len(self.rows()))
        row.remove_requested.connect(self.remove_clicked.emit)
        row.changed.connect(self.resources_changed.emit)
        self._rows.addWidget(row)
        self.resources_changed.emit()

    def set_resources(self, resources: list[tuple[str, str]]) -> None:
        _clear_layout(self._rows)
        for index, (name, capacity) in enumerate(resources):
            row = _ResourceRow(index=index)
            row.edit_name.setText(name)
            row.edit_capacity.setText(capacity)
            row.remove_requested.connect(self.remove_clicked.emit)
            row.changed.connect(self.resources_changed.emit)
            self._rows.addWidget(row)
        self.resources_changed.emit()

    def remove_resource(self, index: int) -> None:
        rows = self.rows()
        if len(rows) <= 1 or not (0 <= index < len(rows)):
            return
        widget = rows[index]
        self._rows.removeWidget(widget)
        widget.deleteLater()
        for new_index, row in enumerate(self.rows()):
            row.set_index(new_index)
        self.resources_changed.emit()

    def rows(self) -> list[_ResourceRow]:
        rows: list[_ResourceRow] = []
        for i in range(self._rows.count()):
            widget = self._rows.itemAt(i).widget()
            if isinstance(widget, _ResourceRow):
                rows.append(widget)
        return rows

    def resource_names(self) -> list[str]:
        return [
            row.edit_name.text().strip() or f"Resource {index + 1}"
            for index, row in enumerate(self.rows())
        ]

    def refresh_strings(self) -> None:
        self.set_title(S.t("knapsack.resources.section"))
        self._hint.setText(S.t("knapsack.resources.hint"))
        self.btn_add.setText(S.t("knapsack.resources.add"))
        _clear_layout(self._header)
        col_idx = QLabel(S.t("knapsack.resources.columns.variable"))
        col_name = QLabel(S.t("knapsack.resources.columns.name"))
        col_capacity = QLabel(S.t("knapsack.resources.columns.capacity"))
        col_idx.setFixedWidth(_ITEM_INDEX_WIDTH)
        col_capacity.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self._header.addWidget(col_idx)
        self._header.addWidget(col_name, 1)
        self._header.addWidget(col_capacity)
        self._header.addSpacing(_ITEM_REMOVE_BUTTON_WIDTH)
        for row in self.rows():
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))


class _MultiItemRow(QWidget):
    remove_requested = Signal(int)

    def __init__(
        self,
        *,
        index: int,
        resource_names: list[str],
        show_quantity_limit: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._usage_edits: list[QLineEdit] = []
        self._show_quantity_limit = show_quantity_limit

        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(8)

        self.lbl_index = QLabel(_item_var_name(index))
        self.lbl_index.setFixedWidth(_ITEM_INDEX_WIDTH)

        self.edit_name = QLineEdit()
        self.edit_name.setObjectName("knapsackMultiItemName")
        self.edit_name.setFixedHeight(28)
        self.edit_name.setMinimumWidth(170)

        self.edit_value = QLineEdit()
        self.edit_value.setObjectName("knapsackMultiItemValue")
        self.edit_value.setFixedHeight(28)
        self.edit_value.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)

        self.edit_quantity_limit = QLineEdit()
        self.edit_quantity_limit.setObjectName("knapsackMultiItemQuantityLimit")
        self.edit_quantity_limit.setFixedHeight(28)
        self.edit_quantity_limit.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self.edit_quantity_limit.setVisible(show_quantity_limit)

        self.btn_remove = QToolButton()

        self.btn_remove.setObjectName("rowRemoveButton")
        icon = QIcon.fromTheme("edit-delete")
        if not icon.isNull():
            self.btn_remove.setIcon(icon)
        else:
            self.btn_remove.setText("x")
        self.btn_remove.setAutoRaise(True)
        self.btn_remove.setFixedSize(_ITEM_REMOVE_BUTTON_WIDTH, 28)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self._index))

        self._row.addWidget(self.lbl_index)
        self._row.addWidget(self.edit_name, 1)
        self._row.addWidget(self.edit_value)
        self._row.addWidget(self.edit_quantity_limit)
        self.set_resource_names(resource_names)
        self.refresh_strings()

    def set_index(self, index: int) -> None:
        self._index = index
        self.lbl_index.setText(_item_var_name(index))

    def set_resource_names(self, resource_names: list[str]) -> None:
        values = [edit.text() for edit in self._usage_edits]
        for edit in self._usage_edits:
            self._row.removeWidget(edit)
            edit.deleteLater()
        self._usage_edits = []
        self._row.removeWidget(self.btn_remove)

        for index, _resource_name in enumerate(resource_names):
            edit = QLineEdit(values[index] if index < len(values) else "")
            edit.setObjectName("knapsackMultiItemResourceUsage")
            edit.setFixedHeight(28)
            edit.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
            edit.setPlaceholderText(S.t("knapsack.multi_items.usage_placeholder"))
            self._usage_edits.append(edit)
            self._row.addWidget(edit)

        self._row.addWidget(self.btn_remove)

    def set_show_quantity_limit(self, show: bool) -> None:
        self._show_quantity_limit = show
        self.edit_quantity_limit.setVisible(show)

    def usage_edits(self) -> list[QLineEdit]:
        return list(self._usage_edits)

    def refresh_strings(self) -> None:
        self.edit_name.setPlaceholderText(S.t("knapsack.multi_items.name_placeholder"))
        self.edit_value.setPlaceholderText(S.t("knapsack.multi_items.value_placeholder"))
        self.edit_quantity_limit.setPlaceholderText(
            S.t("knapsack.multi_items.quantity_limit_placeholder")
        )
        for edit in self._usage_edits:
            edit.setPlaceholderText(S.t("knapsack.multi_items.usage_placeholder"))
        self.btn_remove.setToolTip(S.t("knapsack.multi_items.remove"))


class _MultiItemsSection(Section):
    add_clicked = Signal()
    remove_clicked = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)

        self._resource_names = ["Resource 1", "Resource 2"]
        self._show_quantity_limit = False
        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)

        self._header = QHBoxLayout()
        self._header.setContentsMargins(0, 0, 0, 0)
        self._header.setSpacing(8)
        self.body.addLayout(self._header)

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

    def add_item(self) -> None:
        row = _MultiItemRow(
            index=len(self.rows()),
            resource_names=self._resource_names,
            show_quantity_limit=self._show_quantity_limit,
        )
        row.remove_requested.connect(self.remove_clicked.emit)
        self._rows.addWidget(row)

    def set_items(
        self,
        items: list[tuple[str, str, Optional[str], tuple[str, ...]]],
    ) -> None:
        _clear_layout(self._rows)
        for index, (name, value, quantity_limit, usages) in enumerate(items):
            row = _MultiItemRow(
                index=index,
                resource_names=self._resource_names,
                show_quantity_limit=self._show_quantity_limit,
            )
            row.edit_name.setText(name)
            row.edit_value.setText(value)
            if quantity_limit is not None:
                row.edit_quantity_limit.setText(quantity_limit)
            for edit, usage in zip(row.usage_edits(), usages):
                edit.setText(usage)
            row.remove_requested.connect(self.remove_clicked.emit)
            self._rows.addWidget(row)

    def remove_item(self, index: int) -> None:
        rows = self.rows()
        if not (0 <= index < len(rows)):
            return
        widget = rows[index]
        self._rows.removeWidget(widget)
        widget.deleteLater()
        for new_index, row in enumerate(self.rows()):
            row.set_index(new_index)

    def set_resource_names(self, resource_names: list[str]) -> None:
        self._resource_names = resource_names or ["Resource 1"]
        self._rebuild_header()
        for row in self.rows():
            row.set_resource_names(self._resource_names)

    def set_show_quantity_limit(self, show: bool) -> None:
        self._show_quantity_limit = show
        self._rebuild_header()
        for row in self.rows():
            row.set_show_quantity_limit(show)

    def rows(self) -> list[_MultiItemRow]:
        rows: list[_MultiItemRow] = []
        for i in range(self._rows.count()):
            widget = self._rows.itemAt(i).widget()
            if isinstance(widget, _MultiItemRow):
                rows.append(widget)
        return rows

    def refresh_strings(self) -> None:
        self.set_title(S.t("knapsack.multi_items.section"))
        self._hint.setText(S.t("knapsack.multi_items.hint"))
        self.btn_add.setText(S.t("knapsack.multi_items.add"))
        self._rebuild_header()
        for row in self.rows():
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))

    def _rebuild_header(self) -> None:
        _clear_layout(self._header)
        col_idx = QLabel(S.t("knapsack.multi_items.columns.variable"))
        col_name = QLabel(S.t("knapsack.multi_items.columns.name"))
        col_value = QLabel(S.t("knapsack.multi_items.columns.value"))
        col_idx.setFixedWidth(_ITEM_INDEX_WIDTH)
        col_value.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
        self._header.addWidget(col_idx)
        self._header.addWidget(col_name, 1)
        self._header.addWidget(col_value)
        if self._show_quantity_limit:
            col_limit = QLabel(S.t("knapsack.multi_items.columns.quantity_limit"))
            col_limit.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
            col_limit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._header.addWidget(col_limit)
        for resource_name in self._resource_names:
            label = QLabel(resource_name)
            label.setFixedWidth(_ITEM_NUMERIC_COLUMN_WIDTH)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._header.addWidget(label)
        self._header.addSpacing(_ITEM_REMOVE_BUTTON_WIDTH)


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
        self._multi_domain = _MULTI_DOMAIN_ZERO_ONE

        self.intro = Section()
        import_actions = QWidget()
        import_actions_layout = QHBoxLayout(import_actions)
        import_actions_layout.setContentsMargins(0, 0, 0, 0)
        import_actions_layout.setSpacing(6)

        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("knapsackImportJsonButton")
        self.btn_import_json.setCursor(Qt.PointingHandCursor)
        self.btn_import_json.clicked.connect(self._on_import_json)

        self.btn_json_info = _make_info_button(S.t("knapsack.import.json_info_tooltip"), self)
        self.btn_json_info.setObjectName("knapsackJsonInfoButton")
        self.btn_json_info.clicked.connect(self._show_json_import_info)

        import_actions_layout.addWidget(self.btn_import_json)
        import_actions_layout.addWidget(self.btn_json_info)
        self.intro.set_header_action(import_actions)

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

        self.multi_domain_sec = Section()
        self.multi_domain_hint = QLabel()
        self.multi_domain_hint.setWordWrap(True)
        self.multi_domain_hint.setStyleSheet(theme.secondary_text_css(self))
        self.multi_domain_sec.body.addWidget(self.multi_domain_hint)
        self.multi_domain_group = QButtonGroup(self)
        self.multi_domain_group.setExclusive(True)
        self.multi_domain_buttons: dict[str, QPushButton] = {}
        multi_domain_row = QHBoxLayout()
        multi_domain_row.setContentsMargins(0, 0, 0, 0)
        multi_domain_row.setSpacing(8)
        for domain in _MULTI_DOMAIN_VALUES:
            button = QPushButton()
            button.setCheckable(True)
            button.setObjectName(f"knapsackMultiDomain_{domain}")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, d=domain: self._set_multi_domain(d))
            self.multi_domain_group.addButton(button)
            self.multi_domain_buttons[domain] = button
            multi_domain_row.addWidget(button)
        multi_domain_row.addStretch(1)
        self.multi_domain_sec.body.addLayout(multi_domain_row)
        self.multi_domain_description = QLabel()
        self.multi_domain_description.setWordWrap(True)
        self.multi_domain_description.setStyleSheet(theme.secondary_text_css(self))
        self.multi_domain_sec.body.addWidget(self.multi_domain_description)
        root.addWidget(self.multi_domain_sec)

        self.resources_sec = _ResourcesSection()
        self.btn_resources_info = _make_info_button(
            S.t("knapsack.resources.info_tooltip"),
            self,
        )
        self.btn_resources_info.clicked.connect(self._show_resources_info)
        self.resources_sec.set_header_action(self.btn_resources_info)
        root.addWidget(self.resources_sec)

        self.multi_items_sec = _MultiItemsSection()
        self.btn_multi_items_info = _make_info_button(
            S.t("knapsack.multi_items.info_tooltip"),
            self,
        )
        self.btn_multi_items_info.clicked.connect(self._show_multi_items_info)
        self.multi_items_sec.set_header_action(self.btn_multi_items_info)
        root.addWidget(self.multi_items_sec)

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
        self._multi_dimensional_solve_uc = None
        self._multi_dimensional_milp_solve_uc = None
        self._bounded_max_quantities: list[int] = []
        self._last_solved_model = None

        self.items_sec.add_clicked.connect(self._on_add_item)
        self.items_sec.remove_clicked.connect(self._on_remove_item)
        self.items_sec.name_changed.connect(self._on_item_name_changed)
        self.items_sec.value_changed.connect(self._on_item_value_changed)
        self.items_sec.weight_changed.connect(self._on_item_weight_changed)
        self.items_sec.max_quantity_changed.connect(self._on_item_max_quantity_changed)
        self.resources_sec.add_clicked.connect(self._on_add_resource)
        self.resources_sec.remove_clicked.connect(self._on_remove_resource)
        self.resources_sec.resources_changed.connect(self._on_resources_changed)
        self.multi_items_sec.add_clicked.connect(self._on_add_multi_item)
        self.multi_items_sec.remove_clicked.connect(self._on_remove_multi_item)

        self._init_multi_dimensional_defaults()

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

    def set_multi_dimensional_solve_usecase(self, usecase) -> None:
        self._multi_dimensional_solve_uc = usecase

    def set_multi_dimensional_milp_solve_usecase(self, usecase) -> None:
        self._multi_dimensional_milp_solve_uc = usecase

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

    def _init_multi_dimensional_defaults(self) -> None:
        self.resources_sec.add_resource()
        self.resources_sec.add_resource()
        self.multi_items_sec.set_resource_names(self.resources_sec.resource_names())
        self.multi_items_sec.add_item()
        self.multi_items_sec.add_item()

    def _on_add_resource(self) -> None:
        self.resources_sec.add_resource()
        self._on_resources_changed()

    def _on_remove_resource(self, index: int) -> None:
        self.resources_sec.remove_resource(index)
        self._on_resources_changed()

    def _on_resources_changed(self) -> None:
        self.multi_items_sec.set_resource_names(self.resources_sec.resource_names())
        self._update_optimize_enabled()

    def _on_add_multi_item(self) -> None:
        self.multi_items_sec.add_item()
        self._update_optimize_enabled()

    def _on_remove_multi_item(self, index: int) -> None:
        self.multi_items_sec.remove_item(index)
        self._update_optimize_enabled()

    def _on_capacity_edited(self) -> None:
        if not self._ctrl:
            return
        if self._variant is KnapsackVariant.FRACTIONAL:
            try:
                _parse_float(self.edit_capacity.text())
            except ValueError:
                self.edit_capacity.setStyleSheet(_invalid_border())
                return
            self.edit_capacity.setStyleSheet("")
            return
        try:
            capacity = _parse_int(self.edit_capacity.text())
        except ValueError:
            self.edit_capacity.setStyleSheet(_invalid_border())
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
            self.edit_capacity.setStyleSheet(_invalid_border())
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
        elif self._variant is KnapsackVariant.MULTI_DIMENSIONAL:
            try:
                model = self._build_multi_dimensional_model()
            except ValueError:
                QMessageBox.warning(
                    self,
                    S.t("knapsack.errors.invalid_title"),
                    S.t("knapsack.errors.invalid_body"),
                )
                return
            if self._multi_domain == _MULTI_DOMAIN_ZERO_ONE:
                if not self._multi_dimensional_solve_uc:
                    return
                solution = self._multi_dimensional_solve_uc.execute(model)
            else:
                if not self._multi_dimensional_milp_solve_uc:
                    return
                try:
                    milp_model, milp_var_names = self._build_multi_dimensional_milp_model(
                        model
                    )
                except ValueError:
                    QMessageBox.warning(
                        self,
                        S.t("knapsack.errors.invalid_title"),
                        S.t("knapsack.errors.invalid_body"),
                    )
                    return
                milp_solution = self._multi_dimensional_milp_solve_uc.execute(milp_model)
                quantities = [
                    float(milp_solution.values.get(var_name, 0.0))
                    for var_name in milp_var_names
                ]
                extras = dict(milp_solution.extras or {})
                extras["method"] = extras.get("method") or _multi_domain_method(
                    self._multi_domain
                )
                extras["multi_domain"] = self._multi_domain
                solution = MultiDimensionalQuantityKnapsackSolution.from_model_quantities(
                    model,
                    status=getattr(milp_solution.status, "value", milp_solution.status),
                    objective=milp_solution.objective,
                    quantities=quantities,
                    extras=extras,
                )
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

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("knapsack.import.json_dialog_title"),
            "",
            "Knapsack JSON (*.json);;All files (*)",
        )
        if not path:
            return

        try:
            problem = knapsack_problem_from_file(path)
            self._load_json_problem(problem)
        except Exception as exc:
            QMessageBox.warning(
                self,
                S.t("knapsack.import.error_title"),
                S.t("knapsack.import.error_body", detail=str(exc)),
            )

    def _load_json_problem(self, problem: KnapsackJsonProblem) -> None:
        variant = _JSON_VARIANT_TO_UI_VARIANT.get(problem.variant)
        if variant is None:
            raise ValueError(f"unsupported knapsack variant: {problem.variant}")

        self._last_solved_model = None
        self._set_variant(variant)
        if variant is KnapsackVariant.MULTI_DIMENSIONAL:
            self._load_multi_dimensional_json_problem(problem)
            return
        self._load_single_resource_json_problem(problem)

    def load_json_problem(self, problem: KnapsackJsonProblem) -> None:
        """Load a validated Knapsack JSON problem into the current formulation view."""
        self._load_json_problem(problem)

    def _load_single_resource_json_problem(self, problem: KnapsackJsonProblem) -> None:
        if problem.capacity is None:
            raise ValueError("capacity is required")

        if self._variant is KnapsackVariant.BOUNDED:
            self._bounded_max_quantities = [
                int(item.max_quantity) if item.max_quantity is not None else 1
                for item in problem.items
            ]
        else:
            self._bounded_max_quantities = [1] * len(problem.items)

        capacity = int(problem.capacity) if float(problem.capacity).is_integer() else 0
        placeholder_items = tuple(
            KnapsackItem(
                item.name,
                item.value,
                int(item.weight or 0) if float(item.weight or 0).is_integer() else 0,
            )
            for item in problem.items
        )
        model = Knapsack01Model.from_parts(placeholder_items, capacity=capacity)
        if self._ctrl:
            self._ctrl.load_model(model)
        else:
            self.items_sec.set_items(list(model.items), self._bounded_max_quantities)

        self.edit_capacity.setText(_fmt_number(problem.capacity))
        for index, (row, item) in enumerate(zip(self.items_sec.rows(), problem.items)):
            row.edit_name.setText(item.name)
            row.edit_value.setText(_fmt_number(item.value))
            row.edit_weight.setText(_fmt_number(item.weight or 0.0))
            if self._variant is KnapsackVariant.BOUNDED:
                max_quantity = (
                    self._bounded_max_quantities[index]
                    if index < len(self._bounded_max_quantities)
                    else 1
                )
                row.edit_max_quantity.setText("" if max_quantity == 1 else str(max_quantity))
        self._update_optimize_enabled()

    def _load_multi_dimensional_json_problem(self, problem: KnapsackJsonProblem) -> None:
        domain = _JSON_DOMAIN_TO_MULTI_DOMAIN.get(problem.domain)
        if domain is None:
            raise ValueError(f"unsupported multi-dimensional domain: {problem.domain}")

        self._set_multi_domain(domain)
        self.resources_sec.set_resources(
            [
                (resource.name, _fmt_number(resource.capacity))
                for resource in problem.resources
            ]
        )
        self.multi_items_sec.set_resource_names(self.resources_sec.resource_names())
        self.multi_items_sec.set_items(
            [
                (
                    item.name,
                    _fmt_number(item.value),
                    _fmt_optional_quantity_limit(item.max_quantity),
                    tuple(_fmt_number(value) for value in item.usage),
                )
                for item in problem.items
            ]
        )
        self._update_optimize_enabled()

    def _show_json_import_info(self) -> None:
        _InfoDialog(
            S.t("knapsack.import.json_info_title"),
            S.t("knapsack.import.json_info_body"),
            S.t("knapsack.import.json_info_html"),
            self,
        ).exec()

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

    def _show_resources_info(self) -> None:
        _InfoDialog(
            S.t("knapsack.resources.info_title"),
            S.t("knapsack.resources.info_body"),
            S.t("knapsack.resources.info_html"),
            self,
        ).exec()

    def _show_multi_items_info(self) -> None:
        _InfoDialog(
            S.t("knapsack.multi_items.info_title"),
            S.t("knapsack.multi_items.info_body"),
            S.t("knapsack.multi_items.info_html"),
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
        self.btn_import_json.setText(S.t("knapsack.import.json_button"))
        self.btn_import_json.setToolTip(S.t("knapsack.import.json_tooltip"))
        self.btn_json_info.setToolTip(S.t("knapsack.import.json_info_tooltip"))
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
        self.multi_domain_sec.set_title(S.t("knapsack.multi_domain.section"))
        self.multi_domain_hint.setText(S.t("knapsack.multi_domain.hint"))
        for domain, button in self.multi_domain_buttons.items():
            button.setText(S.t(f"knapsack.multi_domain.labels.{domain}"))
        self.multi_domain_description.setText(
            S.t(f"knapsack.multi_domain.descriptions.{self._multi_domain}")
        )
        self.btn_resources_info.setToolTip(S.t("knapsack.resources.info_tooltip"))
        self.resources_sec.refresh_strings()
        self.btn_multi_items_info.setToolTip(S.t("knapsack.multi_items.info_tooltip"))
        self.multi_items_sec.refresh_strings()
        self.formula_sec.set_title(S.t("knapsack.formula.section"))
        self.btn_algorithm_info.setToolTip(S.t("knapsack.formula.info_tooltip"))
        self.btn_optimize.setText(S.t("knapsack.actions.optimize"))
        self._apply_variant()

    def refresh_theme(self) -> None:
        title_fg = tokens(theme.is_dark()).text
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
        self.multi_domain_sec.refresh_theme()
        self.multi_domain_hint.setStyleSheet(theme.secondary_text_css(self))
        self.multi_domain_description.setStyleSheet(theme.secondary_text_css(self))
        self.resources_sec.refresh_theme()
        self.multi_items_sec.refresh_theme()
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

    def _set_multi_domain(self, domain: str) -> None:
        if domain not in _MULTI_DOMAIN_VALUES:
            return
        self._multi_domain = domain
        self._apply_variant()

    def _apply_variant(self) -> None:
        is_zero_one = self._variant is KnapsackVariant.ZERO_ONE
        is_bounded = self._variant is KnapsackVariant.BOUNDED
        is_unbounded = self._variant is KnapsackVariant.UNBOUNDED
        is_fractional = self._variant is KnapsackVariant.FRACTIONAL
        is_multi_dimensional = self._variant is KnapsackVariant.MULTI_DIMENSIONAL
        is_executable = (
            is_zero_one
            or is_bounded
            or is_unbounded
            or is_fractional
            or is_multi_dimensional
        )
        uses_standard_form = is_executable and not is_multi_dimensional
        button = self.variant_buttons.get(self._variant)
        if button is not None and not button.isChecked():
            button.setChecked(True)

        self.variant_description.setText(
            S.t(f"knapsack.variant.descriptions.{self._variant.value}")
        )
        self.variant_placeholder_sec.setVisible(not is_executable)
        self.capacity_sec.setVisible(uses_standard_form)
        self.items_sec.setVisible(uses_standard_form)
        self.resources_sec.setVisible(is_multi_dimensional)
        self.multi_items_sec.setVisible(is_multi_dimensional)
        self.multi_domain_sec.setVisible(is_multi_dimensional)
        self.multi_domain_sec.set_title(S.t("knapsack.multi_domain.section"))
        self.multi_domain_hint.setText(S.t("knapsack.multi_domain.hint"))
        self.multi_domain_description.setText(
            S.t(f"knapsack.multi_domain.descriptions.{self._multi_domain}")
        )
        for domain, domain_button in self.multi_domain_buttons.items():
            domain_button.setText(S.t(f"knapsack.multi_domain.labels.{domain}"))
            if domain == self._multi_domain and not domain_button.isChecked():
                domain_button.setChecked(True)
        self.multi_items_sec.set_show_quantity_limit(
            self._multi_domain in (_MULTI_DOMAIN_BOUNDED, _MULTI_DOMAIN_FRACTIONAL)
        )
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
        elif is_multi_dimensional:
            formula_key = "knapsack.formula.multi_dimensional_body"
        self.formula.setText(S.t(formula_key))
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
        if self._variant is KnapsackVariant.MULTI_DIMENSIONAL:
            self.btn_optimize.setEnabled(
                bool(self.resources_sec.rows()) and bool(self.multi_items_sec.rows())
            )
            return

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

    def _build_multi_dimensional_model(self) -> MultiDimensionalKnapsackModel:
        resources = []
        for index, row in enumerate(self.resources_sec.rows()):
            name = row.edit_name.text().strip() or f"Resource {index + 1}"
            capacity = _parse_float(row.edit_capacity.text())
            resources.append(MultiDimensionalKnapsackResource(name, capacity))

        items = []
        for index, row in enumerate(self.multi_items_sec.rows()):
            name = row.edit_name.text().strip() or f"Item {index + 1}"
            value = _parse_float(row.edit_value.text())
            usage = tuple(_parse_float(edit.text()) for edit in row.usage_edits())
            items.append(MultiDimensionalKnapsackItem(name, value, usage))

        return MultiDimensionalKnapsackModel.from_parts(
            tuple(resources),
            tuple(items),
        )

    def _build_multi_dimensional_milp_model(
        self,
        model: MultiDimensionalKnapsackModel,
    ) -> tuple[MILPModel, list[str]]:
        variables = []
        var_names = []
        for index, item in enumerate(model.items):
            var_name = _item_var_name(index)
            var_names.append(var_name)
            upper = self._multi_domain_upper_bound(index)
            if self._multi_domain == _MULTI_DOMAIN_BOUNDED:
                integrality = Integrality.INTEGER
            elif self._multi_domain == _MULTI_DOMAIN_UNBOUNDED:
                integrality = Integrality.INTEGER
                upper = None
            elif self._multi_domain == _MULTI_DOMAIN_FRACTIONAL:
                integrality = Integrality.CONTINUOUS
            else:
                integrality = Integrality.BINARY
                upper = 1.0
            variables.append(
                MILPVariable(
                    name=var_name,
                    label=item.name,
                    bounds=Bounds(0.0, upper),
                    integrality=integrality,
                )
            )

        objective = Objective(
            sense=ObjectiveSense.MAX,
            coefs=tuple(item.value for item in model.items),
        )
        constraints = tuple(
            Constraint(
                tuple(item.resource_usage[resource_index] for item in model.items),
                Relation.LE,
                resource.capacity,
            )
            for resource_index, resource in enumerate(model.resources)
        )
        return (
            MILPModel.from_parts(
                tuple(variables),
                objective,
                constraints,
            ),
            var_names,
        )

    def _multi_domain_upper_bound(self, item_index: int) -> Optional[float]:
        if self._multi_domain not in (_MULTI_DOMAIN_BOUNDED, _MULTI_DOMAIN_FRACTIONAL):
            return None
        rows = self.multi_items_sec.rows()
        if not (0 <= item_index < len(rows)):
            return 1.0
        default = 1.0
        return _parse_optional_upper_bound(
            rows[item_index].edit_quantity_limit.text(),
            default=default,
        )


def _fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.6g}"


def _fmt_optional_quantity_limit(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if value == float("inf"):
        return "inf"
    return _fmt_number(value)


def _parse_optional_upper_bound(text: str, *, default: float = 1.0) -> Optional[float]:
    value = (text or "").strip().lower()
    if not value:
        return default
    if value in {"inf", "+inf", "infinity", "+infinity"}:
        return None
    parsed = _parse_float(value)
    if parsed < 0:
        raise ValueError("upper bound must be non-negative")
    return parsed


def _multi_domain_method(domain: str) -> str:
    return {
        _MULTI_DOMAIN_BOUNDED: "multidimensional_bounded_milp",
        _MULTI_DOMAIN_UNBOUNDED: "multidimensional_unbounded_milp",
        _MULTI_DOMAIN_FRACTIONAL: "multidimensional_fractional_lp",
    }.get(domain, "multidimensional_milp")
