# src/optees/presentation/controllers/lp_controller.py
from __future__ import annotations
from typing import List, Optional, Tuple
from PySide6.QtCore import QObject, Signal

from optees.domain.models.lp.lp_model import LPModel
from optees.domain.entities.lp.variable import Variable as LPVariable
from optees.domain.entities.lp.constraint import Constraint as LPConstraint
from optees.domain.entities.lp.objective import Objective as LPObjective
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense


class LPController(QObject):
    # Variables
    variables_changed = Signal(list)                # List[LPVariable]
    variable_updated = Signal(int, str)             # (index, new_label)
    bounds_changed = Signal(list)                   # List[Tuple[lb, ub]]
    bound_updated = Signal(int, object, object)     # (index, lb, ub)

    # Objective
    objective_changed = Signal(object)              # LPObjective (snapshot)
    objective_sense_changed = Signal(str)           # "min" | "max"
    objective_coef_updated = Signal(int, object)    # (index, float|None)
    objective_offset_changed = Signal(object)       # float|None

    # Constraints
    constraints_changed = Signal(list)              # List[LPConstraint] snapshot
    constraint_coef_updated = Signal(int, int, object)  # (row, var_index, float|None)
    constraint_rel_updated = Signal(int, str)           # (row, rel str)
    constraint_rhs_updated = Signal(int, object)        # (row, float|None)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: LPModel = LPModel.empty(0)

    # ---- Query (snapshots for views) ----
    def variables(self) -> List[LPVariable]:
        return list(self._model.variables)

    def constraints(self) -> List[LPConstraint]:
        return list(self._model.constraints)

    def objective(self) -> LPObjective:
        return self._model.objective

    # ---------- Variables ----------
    def set_description(self, index: int, text: str) -> None:
        before = self._model
        self._model = self._model.set_variable_label(index, text)
        if self._model is not before:
            self.variable_updated.emit(index, text)

    def set_bounds(self, index: int, lb: Optional[float], ub: Optional[float]) -> None:
        before = self._model
        try:
            self._model = self._model.set_variable_bounds(index, lb, ub)
        except ValueError:
            # Bounds invalid (lb > ub): ignore update; the row UI can show an error state.
            return
        if self._model is not before:
            self.bound_updated.emit(index, lb, ub)
            self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])

    def apply_preset(self, index: int, preset: str, *, fixed_value: Optional[float] = None) -> None:
        before = self._model
        self._model = self._model.apply_bounds_preset(index, preset, fixed_value=fixed_value)
        if self._model is not before:
            self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])

    # ---------- Objective ----------
    def set_objective_sense(self, sense: str) -> None:
        # accept "min"/"max" from UI
        before = self._model
        try:
            self._model = self._model.set_objective_sense(sense)
        except ValueError:
            return
        if self._model is not before:
            self.objective_sense_changed.emit(sense)
            self.objective_changed.emit(self._model.objective)

    def set_objective_coef(self, index: int, value: Optional[float]) -> None:
        before = self._model
        self._model = self._model.set_objective_coef(index, value)
        if self._model is not before:
            self.objective_coef_updated.emit(index, value)
            self.objective_changed.emit(self._model.objective)

    def set_objective_offset(self, value: Optional[float]) -> None:
        before = self._model
        self._model = self._model.set_objective_offset(value)
        if self._model is not before:
            self.objective_offset_changed.emit(value)
            self.objective_changed.emit(self._model.objective)

    # ---------- Add/Remove variables ----------
    def add_variable(self) -> None:
        self._model = self._model.add_variable()
        self.variables_changed.emit(list(self._model.variables))
        self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])
        self.objective_changed.emit(self._model.objective)
        self.constraints_changed.emit(list(self._model.constraints))

    def remove_variable(self, index: int) -> None:
        self._model = self._model.remove_variable(index)
        self.variables_changed.emit(list(self._model.variables))
        self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])
        self.objective_changed.emit(self._model.objective)
        self.constraints_changed.emit(list(self._model.constraints))

    # ---------- Constraints ----------
    def add_constraint(self) -> int:
        before_n = len(self._model.constraints)
        self._model = self._model.add_constraint()
        self.constraints_changed.emit(list(self._model.constraints))
        return before_n  # index of the newly added row would be 'before_n'

    def remove_constraint(self, row: int) -> None:
        self._model = self._model.remove_constraint(row)
        self.constraints_changed.emit(list(self._model.constraints))

    def set_constraint_coef(self, row: int, var_index: int, value: Optional[float]) -> None:
        before = self._model
        self._model = self._model.set_constraint_coef(row, var_index, value)
        if self._model is not before:
            self.constraint_coef_updated.emit(row, var_index, value)
            self.constraints_changed.emit(list(self._model.constraints))

    def set_constraint_rel(self, row: int, rel: str) -> None:
        before = self._model
        try:
            self._model = self._model.set_constraint_relation(row, rel)
        except ValueError:
            return
        if self._model is not before:
            # emit UI-facing symbol ("<=|=|>=")
            r = self._model.constraints[row].relation.symbol()
            self.constraint_rel_updated.emit(row, r)
            self.constraints_changed.emit(list(self._model.constraints))

    def set_constraint_rhs(self, row: int, rhs: Optional[float]) -> None:
        before = self._model
        self._model = self._model.set_constraint_rhs(row, rhs)
        if self._model is not before:
            self.constraint_rhs_updated.emit(row, rhs)
            self.constraints_changed.emit(list(self._model.constraints))
