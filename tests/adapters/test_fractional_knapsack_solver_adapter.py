from __future__ import annotations

import pytest

from optees.data.adapters.knapsack.fractional_knapsack_solver_adapter import (
    FractionalKnapsackSolverAdapter,
)


def test_adapter_wraps_fractional_greedy_utility(monkeypatch):
    calls = []

    def fake_solve(values, weights, capacity):
        calls.append((values, weights, capacity))
        return 240.0, [1.0, 1.0, 2.0 / 3.0]

    monkeypatch.setattr(
        "optees.data.adapters.knapsack.fractional_knapsack_solver_adapter.solve_fractional_knapsack",
        fake_solve,
    )

    adapter = FractionalKnapsackSolverAdapter(max_items=10)
    out = adapter.solve(
        {
            "values": [60, 100, 120],
            "weights": [10, 20, 30],
            "capacity": 50,
            "var_names": ["A", "B", "C"],
        }
    )

    assert calls == [([60, 100, 120], [10, 20, 30], 50)]
    assert out["status"] == "Optimal"
    assert out["objective"] == 240.0
    assert out["fractions"] == pytest.approx([1.0, 1.0, 2.0 / 3.0])
    assert out["x"] == pytest.approx({"A": 1.0, "B": 1.0, "C": 2.0 / 3.0})
    assert out["extras"]["method"] == "fractional_greedy_density"
    assert out["extras"]["remaining_capacity"] == pytest.approx(0.0)


def test_adapter_refuses_instances_above_item_limit():
    adapter = FractionalKnapsackSolverAdapter(max_items=1)

    out = adapter.solve(
        {
            "values": [1, 2],
            "weights": [1, 2],
            "capacity": 10,
            "var_names": ["A", "B"],
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert out["fractions"] == []
    assert out["extras"]["max_items"] == 1
    assert "too large" in out["extras"]["message"]


def test_adapter_reports_invalid_input_as_not_solved():
    adapter = FractionalKnapsackSolverAdapter()

    out = adapter.solve(
        {
            "values": [1],
            "weights": [0],
            "capacity": 10,
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert "weights must be a finite positive number" in out["extras"]["message"]

