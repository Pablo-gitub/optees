from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from optees.application.ports.milp_solver_port import MILPSolverPort
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality


class SolveMILPUseCase:
    """Orchestrates MILPModel -> canonical dict -> solver port -> MILPSolution."""

    def __init__(self, solver_port: MILPSolverPort):
        self._solver = solver_port

    def execute(self, model: MILPModel) -> MILPSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)
        return MILPSolution.from_utility_tuple(
            raw.get("status"),
            raw.get("objective"),
            raw.get("x", {}),
            dict(raw.get("extras", {})),
        )

    def _map_model_to_problem(self, model: MILPModel) -> Dict[str, Any]:
        n = model.n_vars()
        sense = _sense_to_str(model.objective.sense)
        c: List[float] = [_coalesce_number(model.objective.coefs[i]) for i in range(n)]
        bounds: List[Tuple[Optional[float], Optional[float]]] = [
            (v.bounds.lb, v.bounds.ub) for v in model.variables
        ]
        integrality: List[Optional[str]] = [
            None if v.integrality is Integrality.CONTINUOUS else v.integrality.value
            for v in model.variables
        ]
        var_names = [v.name for v in model.variables]

        A_ub: List[List[float]] = []
        b_ub: List[float] = []
        A_eq: List[List[float]] = []
        b_eq: List[float] = []

        for cons in model.constraints:
            row = [_coalesce_number(x) for x in cons.coefs]
            rhs = _coalesce_number(cons.rhs)
            rel = cons.relation.symbol() if isinstance(cons.relation, Relation) else str(cons.relation)
            if rel == "<=":
                A_ub.append(row)
                b_ub.append(rhs)
            elif rel == "=":
                A_eq.append(row)
                b_eq.append(rhs)
            elif rel == ">=":
                A_ub.append([-a for a in row])
                b_ub.append(-rhs)

        problem: Dict[str, Any] = {
            "sense": sense,
            "c": c,
            "A_ub": A_ub or None,
            "b_ub": b_ub or None,
            "A_eq": A_eq or None,
            "b_eq": b_eq or None,
            "bounds": bounds or None,
            "integrality": integrality,
            "var_names": var_names or None,
            "obj_offset": float(model.objective.offset or 0.0),
        }
        if model.time_limit is not None:
            problem["time_limit"] = float(model.time_limit)
        if model.mip_gap is not None:
            problem["mip_gap"] = float(model.mip_gap)
        return problem


def _sense_to_str(sense: object) -> str:
    if isinstance(sense, ObjectiveSense):
        return "min" if sense.is_min() else "max"
    return "min" if str(sense).lower() == "min" else "max"


def _coalesce_number(value: Optional[float]) -> float:
    return 0.0 if value is None else float(value)
