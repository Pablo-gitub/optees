from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality


def _drop_index[T](seq: Sequence[T], idx: int) -> Tuple[T, ...]:
    return tuple(x for i, x in enumerate(seq) if i != idx)


@dataclass(frozen=True)
class MILPModel:
    """Aggregate root for a mixed-integer linear problem."""

    variables: Tuple[MILPVariable, ...]
    objective: Objective
    constraints: Tuple[Constraint, ...]
    time_limit: Optional[float] = None
    mip_gap: Optional[float] = None

    @staticmethod
    def empty(n: int = 0) -> "MILPModel":
        variables: List[MILPVariable] = [
            MILPVariable(name=f"X{i}") for i in range(1, n + 1)
        ]
        return MILPModel(tuple(variables), Objective().with_size(n), tuple())

    @staticmethod
    def from_parts(
        variables: Iterable[MILPVariable],
        objective: Objective,
        constraints: Iterable[Constraint] = (),
        *,
        time_limit: Optional[float] = None,
        mip_gap: Optional[float] = None,
    ) -> "MILPModel":
        vars_t = tuple(variables)
        n = len(vars_t)
        return MILPModel(
            vars_t,
            objective.with_size(n),
            tuple(c.with_size(n) for c in constraints),
            time_limit=time_limit,
            mip_gap=mip_gap,
        )

    def n_vars(self) -> int:
        return len(self.variables)

    def n_constraints(self) -> int:
        return len(self.constraints)

    def add_variable(self, var: Optional[MILPVariable] = None) -> "MILPModel":
        n = self.n_vars()
        new_var = var or MILPVariable(name=f"X{n + 1}")
        return MILPModel(
            self.variables + (new_var,),
            self.objective.with_size(n + 1),
            tuple(c.with_size(n + 1) for c in self.constraints),
            self.time_limit,
            self.mip_gap,
        )

    def remove_variable(self, index: int) -> "MILPModel":
        if not (0 <= index < self.n_vars()):
            return self
        new_obj = Objective(
            sense=self.objective.sense,
            coefs=_drop_index(self.objective.coefs, index),
            offset=self.objective.offset,
        )
        new_constraints = tuple(
            Constraint(_drop_index(c.coefs, index), c.relation, c.rhs)
            for c in self.constraints
        )
        return MILPModel(
            _drop_index(self.variables, index),
            new_obj,
            new_constraints,
            self.time_limit,
            self.mip_gap,
        )

    def set_variable_label(self, index: int, label: str) -> "MILPModel":
        if not (0 <= index < self.n_vars()):
            return self
        variables = list(self.variables)
        variables[index] = variables[index].relabel(label)
        return MILPModel(tuple(variables), self.objective, self.constraints, self.time_limit, self.mip_gap)

    def set_variable_bounds(self, index: int, lb: Optional[float], ub: Optional[float]) -> "MILPModel":
        if not (0 <= index < self.n_vars()):
            return self
        variables = list(self.variables)
        variables[index] = variables[index].with_bounds(lb, ub)
        return MILPModel(tuple(variables), self.objective, self.constraints, self.time_limit, self.mip_gap)

    def set_variable_integrality(self, index: int, integrality: Union[str, Integrality, None]) -> "MILPModel":
        if not (0 <= index < self.n_vars()):
            return self
        variables = list(self.variables)
        variables[index] = variables[index].with_integrality(integrality)
        return MILPModel(tuple(variables), self.objective, self.constraints, self.time_limit, self.mip_gap)

    def set_objective_sense(self, sense: Union[str, ObjectiveSense]) -> "MILPModel":
        value = ObjectiveSense.from_str(sense) if isinstance(sense, str) else sense
        return MILPModel(self.variables, self.objective.with_sense(value), self.constraints, self.time_limit, self.mip_gap)

    def set_objective_coef(self, index: int, value: Optional[float]) -> "MILPModel":
        obj = self.objective.with_size(self.n_vars())
        if 0 <= index < len(obj.coefs):
            obj = obj.with_coef(index, value)
        return MILPModel(self.variables, obj, self.constraints, self.time_limit, self.mip_gap)

    def set_objective_offset(self, value: Optional[float]) -> "MILPModel":
        return MILPModel(
            self.variables,
            self.objective.with_offset(0.0 if value is None else float(value)),
            self.constraints,
            self.time_limit,
            self.mip_gap,
        )

    def add_constraint(self, cons: Optional[Constraint] = None) -> "MILPModel":
        n = self.n_vars()
        row = (cons or Constraint(coefs=(None,) * n, relation=Relation.LE, rhs=None)).with_size(n)
        return MILPModel(self.variables, self.objective, self.constraints + (row,), self.time_limit, self.mip_gap)

    def remove_constraint(self, row: int) -> "MILPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        return MILPModel(
            self.variables,
            self.objective,
            tuple(c for i, c in enumerate(self.constraints) if i != row),
            self.time_limit,
            self.mip_gap,
        )

    def set_constraint_coef(self, row: int, index: int, value: Optional[float]) -> "MILPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        constraints = list(self.constraints)
        constraints[row] = constraints[row].with_size(self.n_vars()).with_coef(index, value)
        return MILPModel(self.variables, self.objective, tuple(constraints), self.time_limit, self.mip_gap)

    def set_constraint_relation(self, row: int, rel: Union[str, Relation]) -> "MILPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        relation = Relation.from_symbol(rel) if isinstance(rel, str) else rel
        constraints = list(self.constraints)
        constraints[row] = constraints[row].with_relation(relation)
        return MILPModel(self.variables, self.objective, tuple(constraints), self.time_limit, self.mip_gap)

    def set_constraint_rhs(self, row: int, rhs: Optional[float]) -> "MILPModel":
        if not (0 <= row < self.n_constraints()):
            return self
        constraints = list(self.constraints)
        constraints[row] = constraints[row].with_rhs(rhs)
        return MILPModel(self.variables, self.objective, tuple(constraints), self.time_limit, self.mip_gap)

    def with_solver_options(
        self,
        *,
        time_limit: Optional[float] = None,
        mip_gap: Optional[float] = None,
    ) -> "MILPModel":
        return MILPModel(self.variables, self.objective, self.constraints, time_limit, mip_gap)
