from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack.knapsack_model import KnapsackModel


class KnapsackController(QObject):
    """Presentation controller for editable 0/1 knapsack models."""

    capacity_changed = Signal(int)
    items_changed = Signal(list)
    item_updated = Signal(int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = KnapsackModel.empty(0, capacity=0)

    def capacity(self) -> int:
        return self._model.capacity

    def items(self) -> list[KnapsackItem]:
        return list(self._model.items)

    def model(self) -> KnapsackModel:
        return self._model

    def set_capacity(self, value: int) -> None:
        before = self._model
        try:
            self._model = self._model.set_capacity(value)
        except ValueError:
            return
        if self._model is not before:
            self.capacity_changed.emit(self._model.capacity)

    def add_item(self, item: KnapsackItem | None = None) -> None:
        self._model = self._model.add_item(item)
        self.items_changed.emit(list(self._model.items))

    def remove_item(self, index: int) -> None:
        before = self._model
        self._model = self._model.remove_item(index)
        if self._model is not before:
            self.items_changed.emit(list(self._model.items))

    def set_item_name(self, index: int, name: str) -> None:
        before = self._model
        try:
            self._model = self._model.set_item_name(index, name)
        except ValueError:
            return
        if self._model is not before:
            self.item_updated.emit(index, self._model.items[index])

    def set_item_value(self, index: int, value: float) -> None:
        before = self._model
        try:
            self._model = self._model.set_item_value(index, value)
        except ValueError:
            return
        if self._model is not before:
            self.item_updated.emit(index, self._model.items[index])

    def set_item_weight(self, index: int, weight: int) -> None:
        before = self._model
        try:
            self._model = self._model.set_item_weight(index, weight)
        except ValueError:
            return
        if self._model is not before:
            self.item_updated.emit(index, self._model.items[index])

    def load_model(self, model: KnapsackModel) -> None:
        self._model = model
        self.capacity_changed.emit(self._model.capacity)
        self.items_changed.emit(list(self._model.items))

