from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.value_objects.milp.integrality import Integrality


class MILPController(QObject):
    """Presentation controller for editable MILP models.

    It mirrors the LP controller but carries one extra mathematical datum:
    each variable lives either in R (continuous), Z (integer), or {0, 1}
    (binary). Binary variables are normalized by the domain model to bounds
    [0, 1], because x in {0, 1} is equivalent to x integer plus 0 <= x <= 1.
    """

    # Variables
    variables_changed = Signal(list)                # List[MILPVariable]
    variable_updated = Signal(int, str)             # (index, new_label)
    integrality_updated = Signal(int, str)          # (index, "C" | "I" | "B")
    bounds_changed = Signal(list)                   # List[Tuple[lb, ub]]
    bound_updated = Signal(int, object, object)     # (index, lb, ub)

    # Objective
    objective_changed = Signal(object)              # Objective snapshot
    objective_sense_changed = Signal(str)           # "min" | "max"
    objective_coef_updated = Signal(int, object)    # (index, float|None)
    objective_offset_changed = Signal(object)       # float|None

    # Constraints
    constraints_changed = Signal(list)              # List[Constraint] snapshot
    constraint_coef_updated = Signal(int, int, object)
    constraint_rel_updated = Signal(int, str)
    constraint_rhs_updated = Signal(int, object)

    # Solver options
    solver_options_changed = Signal(object, object) # (time_limit, mip_gap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: MILPModel = MILPModel.empty(0)

    # ---- Query snapshots ----
    def variables(self) -> List[MILPVariable]:
        return list(self._model.variables)

    def constraints(self) -> List[Constraint]:
        return list(self._model.constraints)

    def objective(self) -> Objective:
        return self._model.objective

    def time_limit(self) -> Optional[float]:
        return self._model.time_limit

    def mip_gap(self) -> Optional[float]:
        return self._model.mip_gap

    # ---- Variables ----
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
            return
        if self._model is not before:
            self.bound_updated.emit(index, lb, ub)
            self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])

    def apply_preset(
        self,
        index: int,
        preset: str,
        *,
        fixed_value: Optional[float] = None,
    ) -> None:
        if not (0 <= index < len(self._model.variables)):
            return
        variable = self._model.variables[index]
        if variable.integrality is Integrality.BINARY:
            self.set_integrality(index, Integrality.BINARY)
            return
        if preset == "nonneg":
            lb, ub = 0.0, None
        elif preset == "free":
            lb, ub = None, None
        elif preset == "fixed":
            value = fixed_value
            if value is None:
                value = variable.bounds.lb if isinstance(variable.bounds.lb, (int, float)) else 0.0
            lb, ub = float(value), float(value)
        else:
            return
        self.set_bounds(index, lb, ub)

    def set_integrality(self, index: int, integrality: str | Integrality | None) -> None:
        before = self._model
        try:
            kind = Integrality.from_token(integrality)
            self._model = self._model.set_variable_integrality(index, kind)
        except ValueError:
            return
        if self._model is not before:
            self.integrality_updated.emit(index, kind.value)
            self.variables_changed.emit(list(self._model.variables))
            self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])

    def add_variable(self) -> None:
        self._model = self._model.add_variable()
        self._emit_bulk_model_changed()

    def remove_variable(self, index: int) -> None:
        self._model = self._model.remove_variable(index)
        self._emit_bulk_model_changed()

    # ---- Objective ----
    def set_objective_sense(self, sense: str) -> None:
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

    # ---- Constraints ----
    def add_constraint(self) -> int:
        before_n = len(self._model.constraints)
        self._model = self._model.add_constraint()
        self.constraints_changed.emit(list(self._model.constraints))
        return before_n

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
            symbol = self._model.constraints[row].relation.symbol()
            self.constraint_rel_updated.emit(row, symbol)
            self.constraints_changed.emit(list(self._model.constraints))

    def set_constraint_rhs(self, row: int, rhs: Optional[float]) -> None:
        before = self._model
        self._model = self._model.set_constraint_rhs(row, rhs)
        if self._model is not before:
            self.constraint_rhs_updated.emit(row, rhs)
            self.constraints_changed.emit(list(self._model.constraints))

    # ---- Solver options ----
    def set_solver_options(
        self,
        *,
        time_limit: Optional[float] = None,
        mip_gap: Optional[float] = None,
    ) -> None:
        before = self._model
        self._model = self._model.with_solver_options(time_limit=time_limit, mip_gap=mip_gap)
        if self._model is not before:
            self.solver_options_changed.emit(self._model.time_limit, self._model.mip_gap)

    def model(self) -> MILPModel:
        """Return an immutable snapshot of the current MILPModel."""
        return self._model

    def load_model(self, model: MILPModel) -> None:
        self._model = model
        self._emit_bulk_model_changed()
        self.solver_options_changed.emit(self._model.time_limit, self._model.mip_gap)

    def _emit_bulk_model_changed(self) -> None:
        self.variables_changed.emit(list(self._model.variables))
        self.bounds_changed.emit([(v.bounds.lb, v.bounds.ub) for v in self._model.variables])
        self.objective_changed.emit(self._model.objective)
        self.constraints_changed.emit(list(self._model.constraints))
