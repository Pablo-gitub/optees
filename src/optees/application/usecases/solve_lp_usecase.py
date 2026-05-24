# src/optees/application/usecases/solve_lp_usecase.py
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple

from optees.application.ports.lp_solver_port import LPSolverPort
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


class SolveLPUseCase:
    """
    Orchestrates: LPModel -> (canonical problem dict) -> SolverPort -> LPSolution (domain).
    """

    def __init__(self, solver_port: LPSolverPort):
        self._solver = solver_port

    # --- Public API: return domain result (LPSolution) ---
    def execute(self, model: LPModel, *, method: str = "highs") -> LPSolution:
        """
        Execute the solve flow:
          - map LPModel to the canonical LP dict expected by the utility/port
          - call solver port
          - map raw response into a domain LPSolution
        """
        problem = self._map_model_to_problem(model, method=method)
        raw = self._solver.solve(problem)  # expected dict: {status, objective, x, extras}
        # Map raw -> domain result
        status = raw.get("status")
        objective = raw.get("objective")
        x = raw.get("x", {})
        extras = dict(raw.get("extras", {}))
        return LPSolution.from_utility_tuple(status, objective, x, extras)

    # --- Mapping LPModel -> canonical dict (solver-friendly) ---
    def _map_model_to_problem(self, model: LPModel, *, method: str) -> Dict[str, Any]:
        """
        Build the canonical LP dict expected by the solver utility:
          {
            "sense": "min"|"max",
            "c": list[float],
            "A_ub": list[list[float]] | None,
            "b_ub": list[float] | None,
            "A_eq": list[list[float]] | None,
            "b_eq": list[float] | None,
            "bounds": list[[lb, ub]] | None,   # None => ±inf
            "var_names": list[str] | None,
            "obj_offset": float
          }
        Rules:
          - Empty coefficients (None) => 0.0
          - GE constraints are multiplied by -1 to become LE (<=)
          - Bounds keep None as unbounded
        """
        n = model.n_vars()

        # sense
        sense: str
        if isinstance(model.objective.sense, ObjectiveSense):
            sense = "min" if model.objective.sense.is_min() else "max"
        else:
            s = str(model.objective.sense).lower()
            sense = "min" if s == "min" else "max"

        # objective coefficients (None -> 0.0)
        c: List[float] = [self._coalesce_number(model.objective.coefs[i]) for i in range(n)]

        # bounds
        bounds: List[Tuple[Optional[float], Optional[float]]] = []
        for v in model.variables:
            lb = v.bounds.lb
            ub = v.bounds.ub
            bounds.append((lb if lb is not None else None, ub if ub is not None else None))

        # var names
        var_names: List[str] = [v.name for v in model.variables]

        # constraints split
        A_ub: List[List[float]] = []
        b_ub: List[float] = []
        A_eq: List[List[float]] = []
        b_eq: List[float] = []

        for cons in model.constraints:
            # coefficients row with None -> 0.0
            row = [self._coalesce_number(x) for x in cons.coefs]
            rhs_val = self._coalesce_number(cons.rhs)

            rel_symbol: str
            if isinstance(cons.relation, Relation):
                rel_symbol = cons.relation.symbol()
            else:
                rel_symbol = str(cons.relation)

            if rel_symbol == "<=":
                A_ub.append(row)
                b_ub.append(rhs_val)
            elif rel_symbol == "=":
                A_eq.append(row)
                b_eq.append(rhs_val)
            elif rel_symbol == ">=":
                # multiply both sides by -1 to convert to <=
                A_ub.append([-a for a in row])
                b_ub.append(-rhs_val)
            else:
                # Unknown relation: ignore row (or raise). We choose to ignore safely.
                continue

        # normalize empties to None (utility accepts None)
        A_ub_out = A_ub if len(A_ub) else None
        b_ub_out = b_ub if len(b_ub) else None
        A_eq_out = A_eq if len(A_eq) else None
        b_eq_out = b_eq if len(b_eq) else None

        obj_offset = float(model.objective.offset or 0.0)

        problem: Dict[str, Any] = {
            "sense": sense,
            "c": c,
            "A_ub": A_ub_out,
            "b_ub": b_ub_out,
            "A_eq": A_eq_out,
            "b_eq": b_eq_out,
            "bounds": bounds if len(bounds) else None,
            "var_names": var_names if len(var_names) else None,
            "obj_offset": obj_offset,
            # not part of the canonical schema, but some adapters may forward it:
            "method": method,
        }
        return problem

    @staticmethod
    def _coalesce_number(x: Optional[float]) -> float:
        """Turn None into 0.0 for numeric arrays/vectors."""
        return 0.0 if x is None else float(x)
