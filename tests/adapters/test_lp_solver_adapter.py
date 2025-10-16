from __future__ import annotations
from typing import Dict, Any
import types
import pytest

from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter

def test_adapter_wraps_utility(monkeypatch):
    # finta utility.solve_lp: ritorna tuple come la vera utility
    def fake_solve_lp(problem: Dict[str, Any], method: str = "highs"):
        assert problem["sense"] in ("min", "max")
        return ("Optimal", 1.23, {"X1": 1.0}, {"nit": 3})

    # patch della funzione chiamata dall'adapter
    monkeypatch.setattr("optees.data.adapters.lp.lp_solver_adapter.solve_lp", fake_solve_lp)

    adapter = LPSolverAdapter()
    out = adapter.solve({"sense": "min", "c": [0.0], "bounds": [(0.0, None)], "method": "highs"})
    assert out["status"] == "Optimal"
    assert out["objective"] == 1.23
    assert out["x"] == {"X1": 1.0}
    assert out["extras"]["nit"] == 3
    assert out["extras"]["method"] == "highs"
