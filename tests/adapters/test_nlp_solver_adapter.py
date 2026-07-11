from __future__ import annotations

from typing import Any, Dict

from optees.data.adapters.nlp.nlp_solver_adapter import ScipyNLPSolverAdapter


def test_adapter_wraps_nlp_utility(monkeypatch) -> None:
    def fake_solve_nlp(problem: Dict[str, Any]):
        assert problem["method"] == "BFGS"
        return "Converged", 1.25, {"x1": 2.0}, {"iterations": 3}

    monkeypatch.setattr(
        "optees.data.adapters.nlp.nlp_solver_adapter.solve_nlp",
        fake_solve_nlp,
    )

    result = ScipyNLPSolverAdapter().solve({"method": "BFGS"})

    assert result == {
        "status": "Converged",
        "objective": 1.25,
        "x": {"x1": 2.0},
        "extras": {"iterations": 3},
    }


def test_adapter_maps_utility_errors_to_failed_result(monkeypatch) -> None:
    def failing_solve_nlp(_: Dict[str, Any]):
        raise RuntimeError("missing SciPy")

    monkeypatch.setattr(
        "optees.data.adapters.nlp.nlp_solver_adapter.solve_nlp",
        failing_solve_nlp,
    )

    result = ScipyNLPSolverAdapter().solve({})

    assert result["status"] == "Failed"
    assert result["objective"] is None
    assert result["x"] == {}
    assert result["extras"]["success"] is False
