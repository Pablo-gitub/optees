from __future__ import annotations

from optees.data.adapters.knapsack.bounded_knapsack_solver_adapter import (
    BoundedKnapsackSolverAdapter,
)


def test_adapter_wraps_bounded_dynamic_programming_utility(monkeypatch):
    calls = []

    def fake_solve(values, weights, max_quantities, capacity):
        calls.append((values, weights, max_quantities, capacity))
        return 22.0, [2, 1]

    monkeypatch.setattr(
        "optees.data.adapters.knapsack.bounded_knapsack_solver_adapter.solve_bounded_knapsack",
        fake_solve,
    )

    adapter = BoundedKnapsackSolverAdapter(max_dp_states=1_000)
    out = adapter.solve(
        {
            "values": [6, 10],
            "weights": [2, 3],
            "max_quantities": [3, 2],
            "capacity": 7,
            "var_names": ["A", "B"],
        }
    )

    assert calls == [([6, 10], [2, 3], [3, 2], 7)]
    assert out["status"] == "Optimal"
    assert out["objective"] == 22.0
    assert out["quantities"] == [2, 1]
    assert out["x"] == {"A": 2, "B": 1}
    assert out["extras"]["method"] == "bounded_dynamic_programming"
    assert out["extras"]["remaining_capacity"] == 0
    assert out["extras"]["dp_cells"] == out["extras"]["dp_states"]


def test_adapter_refuses_instances_above_dp_state_limit():
    adapter = BoundedKnapsackSolverAdapter(max_dp_states=10)

    out = adapter.solve(
        {
            "values": [1, 2],
            "weights": [1, 2],
            "max_quantities": [10, 10],
            "capacity": 100,
            "var_names": ["A", "B"],
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert out["quantities"] == []
    assert out["extras"]["dp_states"] == 2_222
    assert out["extras"]["dp_cells"] == 2_222
    assert out["extras"]["max_dp_cells"] == 10
    assert "too large" in out["extras"]["message"]


def test_adapter_reports_invalid_input_as_not_solved():
    adapter = BoundedKnapsackSolverAdapter()

    out = adapter.solve(
        {
            "values": [1],
            "weights": [1],
            "max_quantities": [1],
            "capacity": -1,
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert "capacity must be non-negative" in out["extras"]["message"]
