from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.qp_solver_port import QPSolverPort
from optees.domain.entities.qp.solution import QPSolution
from optees.domain.models.qp.qp_model import QPModel
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.qp.qp_dual_values import QPDualValues
from optees.domain.value_objects.qp.qp_kkt_residuals import QPKKTResiduals
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus
from optees.domain.value_objects.qp.qp_solver_diagnostics import QPSolverDiagnostics


class SolveQPUseCase:
    """Use case orchestrating QPModel -> canonical problem dict -> QPSolverPort -> QPSolution."""

    def __init__(self, solver_port: QPSolverPort):
        self._solver = solver_port

    def execute(self, model: QPModel) -> QPSolution:
        problem = self._map_model_to_problem(model)
        raw = self._solver.solve(problem)

        raw_status = raw.get("status", "NotSolved")
        status = QPSolveStatus.from_str(str(raw_status))
        objective = raw.get("objective")
        values = raw.get("x", {})
        extras = dict(raw.get("extras", {}))

        dual_data = raw.get("dual_values")
        dual_values = QPDualValues.from_dict(dual_data) if dual_data is not None else None

        kkt_data = raw.get("kkt_residuals")
        kkt_residuals = QPKKTResiduals.from_dict(kkt_data) if kkt_data is not None else None

        diagnostics = QPSolverDiagnostics.from_extras(extras)

        return QPSolution(
            status=status,
            objective=float(objective) if objective is not None else None,
            values=dict(values or {}),
            dual_values=dual_values,
            kkt_residuals=kkt_residuals,
            diagnostics=diagnostics,
            extras=extras,
        )

    def _map_model_to_problem(self, model: QPModel) -> Dict[str, Any]:
        is_min = model.objective.sense == ObjectiveSense.MIN
        sense_str = "min" if is_min else "max"

        variables = list(model.variable_names())
        bounds = [(v.bounds.lb, v.bounds.ub) for v in model.variables]
        c = list(model.objective.linear_coefs)
        Q = [list(row) for row in model.objective.quadratic_matrix]
        offset = float(model.objective.offset)

        constraints = [
            {
                "name": cons.name,
                "coefs": list(cons.coefs),
                "relation": cons.relation.symbol() if hasattr(cons.relation, "symbol") else str(cons.relation),
                "rhs": float(cons.rhs),
            }
            for cons in model.constraints
        ]

        options = {
            "method": model.options.method,
            "tolerance": model.options.tolerance,
            "max_iterations": model.options.max_iterations,
            "time_limit_seconds": model.options.time_limit_seconds,
            "warm_start": model.options.warm_start,
            "initial_primal": list(model.options.initial_primal) if model.options.initial_primal else None,
            "initial_dual": list(model.options.initial_dual) if model.options.initial_dual else None,
        }

        return {
            "sense": sense_str,
            "variables": variables,
            "bounds": bounds,
            "c": c,
            "Q": Q,
            "offset": offset,
            "constraints": constraints,
            "options": options,
        }
