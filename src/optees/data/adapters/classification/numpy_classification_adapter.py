from __future__ import annotations

from typing import Any, Dict

from optees.utility.classification_utils import solve_classification


class NumpyClassificationAdapter:
    """NumPy implementation of the local educational logistic-regression port."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return solve_classification(problem)
        except Exception as exc:
            return {"status": "Failed", "extras": {"message": str(exc)}}
