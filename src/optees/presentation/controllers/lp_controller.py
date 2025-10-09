from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from PySide6.QtCore import QObject, Signal


@dataclass
class LPVariable:
    name: str                  # X1, X2, ...
    label: str = ""            # short display name from Variables card
    lb: Optional[float] = 0.0  # default LP lower bound
    ub: Optional[float] = None # default LP upper bound (+inf)

class LPController(QObject):
    variables_changed = Signal(list)              # emits List[LPVariable]
    variable_updated = Signal(int, str)           # (index, new_label)
    bounds_changed = Signal(list)                 # emits List[Tuple[lb, ub]]
    bound_updated = Signal(int, object, object)   # (index, lb, ub)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._vars: List[LPVariable] = []

    # ---- Query ----
    def variables(self) -> List[LPVariable]:
        return list(self._vars)

    # ---------- rename/label from Variables card ----------
    def set_description(self, index: int, text: str) -> None:
        if 0 <= index < len(self._vars):
            self._vars[index].label = text
            self.variable_updated.emit(index, text)

    # ---------- bounds API ----------
    def set_bounds(self, index: int, lb: Optional[float], ub: Optional[float]) -> None:
        """Set per-variable bounds and emit granular + bulk signals."""
        if 0 <= index < len(self._vars):
            self._vars[index].lb = lb
            self._vars[index].ub = ub
            self.bound_updated.emit(index, lb, ub)
            self.bounds_changed.emit([(v.lb, v.ub) for v in self._vars])

    def apply_preset(self, index: int, preset: str, *, fixed_value: Optional[float] = None) -> None:
        """Apply a preset: 'nonneg', 'free', 'fixed'."""
        if not (0 <= index < len(self._vars)):
            return
        if preset == "nonneg":
            lb, ub = 0.0, None
        elif preset == "free":
            lb, ub = None, None
        elif preset == "fixed":
            # if no fixed_value is provided, use current lb if numeric, else 0.0
            v = self._vars[index]
            val = fixed_value
            if val is None:
                val = v.lb if isinstance(v.lb, (int, float)) else 0.0
            lb = ub = float(val)
        else:
            return
        self.set_bounds(index, lb, ub)

    # ---------- add/remove keep bounds coherent ----------
    def add_variable(self) -> None:
        idx = len(self._vars) + 1
        self._vars.append(LPVariable(name=f"X{idx}"))
        self.variables_changed.emit(self.variables())
        self.bounds_changed.emit([(v.lb, v.ub) for v in self._vars])

    def remove_variable(self, index: int) -> None:
        if 0 <= index < len(self._vars):
            del self._vars[index]
            for i, v in enumerate(self._vars, start=1):
                v.name = f"X{i}"
            self.variables_changed.emit(self.variables())
            self.bounds_changed.emit([(v.lb, v.ub) for v in self._vars])