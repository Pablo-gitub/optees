from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from PySide6.QtCore import QObject, Signal


@dataclass
class LPVariable:
    name: str
    description: str = ""


class LPController(QObject):
    variables_changed = Signal(list)          # emits List[LPVariable]
    variable_updated = Signal(int, str)       # (index, new_description)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._vars: List[LPVariable] = []

    # ---- Query ----
    def variables(self) -> List[LPVariable]:
        return list(self._vars)

    # ---- Commands ----
    def add_variable(self) -> None:
        idx = len(self._vars) + 1
        self._vars.append(LPVariable(name=f"X{idx}"))
        self.variables_changed.emit(self.variables())

    def remove_variable(self, index: int) -> None:
        if 0 <= index < len(self._vars):
            del self._vars[index]
            # rinomina coerentemente X1..Xn
            for i, v in enumerate(self._vars, start=1):
                v.name = f"X{i}"
            self.variables_changed.emit(self.variables())

    def set_description(self, index: int, text: str) -> None:
        if 0 <= index < len(self._vars):
            self._vars[index].description = text
            self.variable_updated.emit(index, text)
