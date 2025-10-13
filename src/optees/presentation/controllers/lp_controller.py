# src/optees/presentation/controllers/lp_controller.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from PySide6.QtCore import QObject, Signal

@dataclass
class LPVariable:
    name: str
    label: str = ""
    lb: Optional[float] = 0.0
    ub: Optional[float] = None

@dataclass
class LPConstraint:
    # Linear constraint: sum_i a[i] * x_i (rel) rhs
    coefs: List[Optional[float]]
    rel: str = "<="                     # one of "<=", "=", ">="
    rhs: Optional[float] = None

# NEW: stato dell’obiettivo
@dataclass
class LPObjective:
    sense: str = "max"                        # "min" | "max"
    coefs: List[Optional[float]] = None       # len == n_vars
    offset: Optional[float] = None

    def __post_init__(self):
        if self.coefs is None:
            self.coefs = []

class LPController(QObject):
    variables_changed = Signal(list)                # List[LPVariable]
    variable_updated = Signal(int, str)             # (index, new_label)
    bounds_changed = Signal(list)                   # List[Tuple[lb, ub]]
    bound_updated = Signal(int, object, object)     # (index, lb, ub)

    # Objective signals (NEW)
    objective_changed = Signal(object)              # LPObjective (snapshot)
    objective_sense_changed = Signal(str)           # "min" | "max"
    objective_coef_updated = Signal(int, object)    # (index, float|None)
    objective_offset_changed = Signal(object)       # float|None

    constraints_changed = Signal(list)            # emits List[LPConstraint] snapshot
    constraint_coef_updated = Signal(int, int, object)  # (row, var_index, float|None)
    constraint_rel_updated = Signal(int, str)           # (row, rel)
    constraint_rhs_updated = Signal(int, object)        # (row, float|None)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._vars: List[LPVariable] = []
        self._objective = LPObjective()
        self._constraints: List[LPConstraint] = []

    # ---- Query ----
    def variables(self) -> List[LPVariable]:
        return list(self._vars)
    
    def constraints(self) -> List[LPConstraint]:
        # return a shallow-safe snapshot
        return [LPConstraint(coefs=list(c.coefs), rel=c.rel, rhs=c.rhs) for c in self._constraints]

    # NEW: get snapshot dell’obiettivo
    def objective(self) -> LPObjective:
        # ritorna una copia shallow sicura
        return LPObjective(
            sense=self._objective.sense,
            coefs=list(self._objective.coefs),
            offset=self._objective.offset
        )

    # ---------- rename/label ----------
    def set_description(self, index: int, text: str) -> None:
        if 0 <= index < len(self._vars):
            self._vars[index].label = text
            self.variable_updated.emit(index, text)

    # ---------- bounds API ----------
    def set_bounds(self, index: int, lb: Optional[float], ub: Optional[float]) -> None:
        if 0 <= index < len(self._vars):
            self._vars[index].lb = lb
            self._vars[index].ub = ub
            self.bound_updated.emit(index, lb, ub)
            self.bounds_changed.emit([(v.lb, v.ub) for v in self._vars])

    def apply_preset(self, index: int, preset: str, *, fixed_value: Optional[float] = None) -> None:
        if not (0 <= index < len(self._vars)):
            return
        if preset == "nonneg":
            lb, ub = 0.0, None
        elif preset == "free":
            lb, ub = None, None
        elif preset == "fixed":
            v = self._vars[index]
            val = fixed_value if fixed_value is not None else (v.lb if isinstance(v.lb, (int, float)) else 0.0)
            lb = ub = float(val)
        else:
            return
        self.set_bounds(index, lb, ub)

    # ---------- objective API (NEW) ----------
    def set_objective_sense(self, sense: str) -> None:
        if sense not in ("min", "max"):
            return
        if self._objective.sense != sense:
            self._objective.sense = sense
            self.objective_sense_changed.emit(sense)
            self.objective_changed.emit(self.objective())

    def set_objective_coef(self, index: int, value: Optional[float]) -> None:
        # assicura coerenza lunghezze
        self._ensure_obj_size(len(self._vars))
        if 0 <= index < len(self._objective.coefs):
            self._objective.coefs[index] = value
            self.objective_coef_updated.emit(index, value)
            self.objective_changed.emit(self.objective())

    def set_objective_offset(self, value: Optional[float]) -> None:
        self._objective.offset = value
        self.objective_offset_changed.emit(value)
        self.objective_changed.emit(self.objective())

    def _ensure_obj_size(self, n: int) -> None:
        """Pad/tronca il vettore dei coefficienti per allinearlo al numero variabili."""
        cur = len(self._objective.coefs)
        if cur < n:
            self._objective.coefs.extend([None] * (n - cur))
        elif cur > n:
            self._objective.coefs = self._objective.coefs[:n]

    def _ensure_cons_columns(self, n: int) -> None:
        # Pad/trim coefficients in every constraint to match variable count
        for c in self._constraints:
            cur = len(c.coefs)
            if cur < n:
                c.coefs.extend([None] * (n - cur))
            elif cur > n:
                c.coefs = c.coefs[:n]

    # ---------- add/remove ----------
    def add_variable(self) -> None:
        idx = len(self._vars) + 1
        self._vars.append(LPVariable(name=f"X{idx}"))
        self._ensure_obj_size(len(self._vars))
        self._ensure_cons_columns(len(self._vars))
        self.variables_changed.emit(self.variables())
        self.bounds_changed.emit([(v.lb, v.ub) for v in self._vars])
        self.objective_changed.emit(self.objective())
        self.constraints_changed.emit(self.constraints())

    def remove_variable(self, index: int) -> None:
        if 0 <= index < len(self._vars):
            del self._vars[index]
            for i, v in enumerate(self._vars, start=1):
                v.name = f"X{i}"
            self._ensure_obj_size(len(self._vars))
            self._ensure_cons_columns(len(self._vars))
            self.variables_changed.emit(self.variables())
            self.bounds_changed.emit([(v.lb, v.ub) for v in self._vars])
            self.objective_changed.emit(self.objective())
            self.constraints_changed.emit(self.constraints())

    # ---------- constraints API (NEW) ----------
    def add_constraint(self) -> int:
        n = len(self._vars)
        row = LPConstraint(coefs=[None]*n, rel="<=", rhs=None)
        self._constraints.append(row)
        self.constraints_changed.emit(self.constraints())
        return len(self._constraints) - 1
    
    def remove_constraint(self, row: int) -> None:
        if 0 <= row < len(self._constraints):
            del self._constraints[row]
            # Notifica: la view si riallineerà via constraints_changed
            self.constraints_changed.emit(self.constraints())

    def set_constraint_coef(self, row: int, var_index: int, value: Optional[float]) -> None:
        if 0 <= row < len(self._constraints):
            self._ensure_cons_columns(len(self._vars))
            if 0 <= var_index < len(self._constraints[row].coefs):
                self._constraints[row].coefs[var_index] = value
                self.constraint_coef_updated.emit(row, var_index, value)
                self.constraints_changed.emit(self.constraints())

    def set_constraint_rel(self, row: int, rel: str) -> None:
        if rel not in ("<=", "=", ">="):
            return
        if 0 <= row < len(self._constraints):
            self._constraints[row].rel = rel
            self.constraint_rel_updated.emit(row, rel)
            self.constraints_changed.emit(self.constraints())

    def set_constraint_rhs(self, row: int, rhs: Optional[float]) -> None:
        if 0 <= row < len(self._constraints):
            self._constraints[row].rhs = rhs
            self.constraint_rhs_updated.emit(row, rhs)
            self.constraints_changed.emit(self.constraints())
