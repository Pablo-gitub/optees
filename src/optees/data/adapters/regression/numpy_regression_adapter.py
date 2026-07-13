from __future__ import annotations

from typing import Any, Dict

from optees.application.ports.regression_solver_port import RegressionSolverPort
from optees.utility.regression_utils import solve_regression


class NumpyRegressionAdapter(RegressionSolverPort):
    """Expose the local transparent numerical implementation through a port."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return solve_regression(problem)
        except Exception as exc:
            return {
                "status": "Failed",
                "intercept": None,
                "coefficients": {},
                "train_metrics": {},
                "test_metrics": {},
                "predictions": [],
                "extras": {"message": str(exc)},
            }
