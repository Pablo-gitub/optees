from __future__ import annotations

from optees.data.adapters.milp import milp_solver_adapter as adapter_module
from optees.data.adapters.milp.milp_solver_adapter import MILPSolverAdapter


def test_adapter_marks_feasible_incumbent_when_configured_limit_is_reached(
    monkeypatch,
):
    monkeypatch.setattr(
        adapter_module,
        "solve_milp",
        lambda problem, time_limit: (
            "Feasible",
            7,
            {"x": 1},
            {"backend": "cbc", "wall_time_ms": 980},
        ),
    )

    result = MILPSolverAdapter().solve({"time_limit": 1})

    assert result["status"] == "Feasible"
    assert result["objective"] == 7
    assert result["extras"]["termination_reason"] == "time_limit"


def test_adapter_does_not_infer_time_limit_for_optimal_result(monkeypatch):
    monkeypatch.setattr(
        adapter_module,
        "solve_milp",
        lambda problem, time_limit: (
            "Optimal",
            7,
            {"x": 1},
            {"backend": "cbc", "wall_time_ms": 1000},
        ),
    )

    result = MILPSolverAdapter().solve({"time_limit": 1})

    assert "termination_reason" not in result["extras"]
