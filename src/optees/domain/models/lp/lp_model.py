# optees/domain/models/lp/lp_model.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List, Sequence, Iterable, Union

from optees.domain.entities.lp.variable import Variable
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.lp.constraint import Constraint
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    """Return a new tuple removing element at index idx."""
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class LPModel:
    """Aggregate root for an LP: variables, objective, constraints.

    Immutability policy: every mutator returns a NEW LPModel instance.
    """
    variables: Tuple[Variable, ...]
    objective: Objective
    constraints: Tuple[Constraint, ...]

    # ---------- Constructors ----------
    @staticmethod
    def empty(n: int = 0) -> "LPModel":
        vars_: List[Variable] = [Variable(name=f"X{i}") for i in range(1, n + 1)]
        obj = Objective().with_size(n)  # pad coefs to n with None
        cons: Tuple[Constraint, ...] = tuple()
        return LPModel(tuple(vars_), obj, cons)

    @staticmethod
    def from_parts(
        variables: Iterable[Variable],
        objective: Objective,
        constraints: Iterable[Constraint] = (),
    ) -> "LPModel":
        vars_t = tuple(variables)
        n = len(vars_t)
        obj = objective.with_size(n)
        cons_t = tuple(c.with_size(n) for c in constraints)
        model = LPModel(vars_t, obj, cons_t)
        return model._renumber_vars()

    # ---------- Basic queries ----------
    def n_vars(self) -> int:
        return len(self.variables)

    def n_constraints(self) -> int:
        return len(self.constraints)

    def var(self, i: int) -> Variable:
        return self.variables[i]

    def cons(self, r: int) -> Constraint:
        return self.constraints[r]

    # ---------- Variable operations ----------
    def add_variable(self, var: Optional[Variable] = None) -> "LPModel":
        n = self.n_vars()
        v = var if var is not None else Variable(name=f"X{n+1}")
        new_vars = tuple(list(self.variables) + [v])
        new_obj = self.objective.with_size(n + 1)
        new_cons = tuple(c.with_size(n + 1) for c in self.constraints)
        return LPModel(new_vars, new_obj, new_cons)._renumber_vars()

    def remove_variable(self, index: int) -> "LPModel":
        if not (0 <= index < self.n_vars()):
            return self
        # remove variable
        new_vars = tuple(v for i, v in enumerate(self.variables) if i != index)
        # drop corresponding column from objective and constraints
        new_obj = Objective(
            sense=self.objective.sense,
            coefs=_drop_index(self.objective.coefs, index),
            offset=self.objective.offset,
        )
        new_cons = tuple(
            Constraint(
                coefs=_drop_index(c.coefs, index),
                relation=c.relation,
                rhs=c.rhs,
            )
            for c in self.constraints
        )
        return LPModel(new_vars, new_obj, new_cons)._renumber_vars()

    def set_variable_label(self, index: int, label: str) -> "LPModel":
        if not (0 <= index < self.n_vars()):
            return self
        vs = list(self.variables)
        vs[index] = vs[index].relabel(label)
        return LPModel(tuple(vs), self.objective, self.constraints)

    def set_variable_bounds(self, index: int, lb: Optional[float], ub: Optional[float]) -> "LPModel":
        if not (0 <= index < self.n_vars()):
            return self
        vs = list(self.variables)
        vs[index] = vs[index].with_bounds(lb, ub)
        return LPModel(tuple(vs), self.objective, self.constraints)

    def apply_bounds_preset(self, index: int, preset: str, fixed_value: Optional[float] = None) -> "LPModel":
        if not (0 <= index < self.n_vars()):
            return self
        if preset == "nonneg":
            b = Bounds(0.0, None)
        elif preset == "free":
            b = Bounds(None, None)
        elif preset == "fixed":
            v = self.variables[index]
            val = fixed_value if fixed_value is not None else (v.bounds.lb if isinstance(v.bounds.lb, (int, float)) else 0.0)
            b = Bounds(float(val), float(val))
        else:
            return self
        vs = list(self.variables)
        vs[index] = Variable(name=vs[index].name, label=vs[index].label, bounds=b)
        return LPModel(tuple(vs), self.objective, self.constraints)

    # ---------- Objective operations ----------
    def set_objective_sense(self, sense: Union[str, ObjectiveSense]) -> "LPModel":
        s = ObjectiveSense.from_str(sense) if isinstance(sense, str) else sense
        return LPModel(self.variables, self.objective.with_sense(s), self.constraints)

    def set_objective_coef(self, index: int, value: Optional[float]) -> "LPModel":
        n = self.n_vars()
        obj = self.objective.with_size(n)
        if 0 <= index < len(obj.coefs):
            obj = obj.with_coef(index, value)
        return LPModel(self.variables, obj, self.constraints)

    def set_objective_offset(self, value: Optional[float]) -> "LPModel":
        off = 0.0 if value is None else float(value)
        return LPModel(self.variables, self.objective.with_offset(off), self.constraints)

    # ---------- Constraint operations ----------
    def add_constraint(self, cons: Optional[Constraint] = None) -> "LPModel":
        n = self.n_vars()
        row = cons if cons is not None else Constraint(coefs=(None,) * n, relation=Relation.LE, rhs=None)
        row = row.with_size(n)
        new_cons = tuple(list(self.constraints) + [row])
        return LPModel(self.variables, self.objective, new_cons)

    def remove_constraint(self, row: int) -> "LPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        new_cons = tuple(c for i, c in enumerate(self.constraints) if i != row)
        return LPModel(self.variables, self.objective, new_cons)

    def set_constraint_coef(self, row: int, index: int, value: Optional[float]) -> "LPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        n = self.n_vars()
        cons = list(self.constraints)
        cons[row] = cons[row].with_size(n).with_coef(index, value)
        return LPModel(self.variables, self.objective, tuple(cons))

    def set_constraint_relation(self, row: int, rel: Union[str, Relation]) -> "LPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        r = Relation.from_symbol(rel) if isinstance(rel, str) else rel
        cons = list(self.constraints)
        cons[row] = cons[row].with_relation(r)
        return LPModel(self.variables, self.objective, tuple(cons))

    def set_constraint_rhs(self, row: int, rhs: Optional[float]) -> "LPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        cons = list(self.constraints)
        cons[row] = cons[row].with_rhs(rhs)
        return LPModel(self.variables, self.objective, tuple(cons))

    # ---------- Internals ----------
    def _renumber_vars(self) -> "LPModel":
        """Ensure variables are named X1..Xn in order."""
        vs = tuple(v.rename(f"X{i}") for i, v in enumerate(self.variables, start=1))
        return LPModel(vs, self.objective, self.constraints)
