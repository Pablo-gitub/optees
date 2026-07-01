from __future__ import annotations

from optees.data.adapters.knapsack.unbounded_knapsack_solver_adapter import (
    UnboundedKnapsackSolverAdapter,
)


def test_adapter_wraps_unbounded_dynamic_programming_utility(monkeypatch):
    calls = []

    def fake_solve(values, weights, capacity):
        calls.append((values, weights, capacity))
        return 110.0, [0, 1, 0, 1]

    monkeypatch.setattr(
        "optees.data.adapters.knapsack.unbounded_knapsack_solver_adapter.solve_unbounded_knapsack",
        fake_solve,
    )

    adapter = UnboundedKnapsackSolverAdapter(max_dp_cells=1_000)
    out = adapter.solve(
        {
            "values": [10, 40, 50, 70],
            "weights": [1, 3, 4, 5],
            "capacity": 8,
            "var_names": ["A", "B", "C", "D"],
        }
    )

    assert calls == [([10.0, 40.0, 50.0, 70.0], [1, 3, 4, 5], 8)]
    assert out["status"] == "Optimal"
    assert out["objective"] == 110.0
    assert out["quantities"] == [0, 1, 0, 1]
    assert out["x"] == {"A": 0, "B": 1, "C": 0, "D": 1}
    assert out["extras"]["method"] == "unbounded_dynamic_programming"
    assert out["extras"]["remaining_capacity"] == 0
    assert out["extras"]["dp_cells"] == 36


def test_adapter_refuses_instances_above_dp_cell_limit():
    adapter = UnboundedKnapsackSolverAdapter(max_dp_cells=10)

    out = adapter.solve(
        {
            "values": [1, 2],
            "weights": [1, 2],
            "capacity": 100,
            "var_names": ["A", "B"],
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert out["quantities"] == []
    assert out["extras"]["dp_cells"] == 202
    assert out["extras"]["max_dp_cells"] == 10
    assert "too large" in out["extras"]["message"]


def test_adapter_reports_zero_weight_positive_value_as_unbounded(monkeypatch):
    def fail_if_called(values, weights, capacity):
        raise AssertionError("utility should not be called for unbounded instances")

    monkeypatch.setattr(
        "optees.data.adapters.knapsack.unbounded_knapsack_solver_adapter.solve_unbounded_knapsack",
        fail_if_called,
    )

    adapter = UnboundedKnapsackSolverAdapter()
    out = adapter.solve(
        {
            "values": [5, 1],
            "weights": [0, 1],
            "capacity": 10,
            "var_names": ["Free", "A"],
        }
    )

    assert out["status"] == "Unbounded"
    assert out["objective"] is None
    assert out["quantities"] == []
    assert "zero weight" in out["extras"]["message"]


def test_adapter_reports_invalid_input_as_not_solved():
    adapter = UnboundedKnapsackSolverAdapter()

    out = adapter.solve(
        {
            "values": [1],
            "weights": [1],
            "capacity": -1,
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert "capacity must be non-negative" in out["extras"]["message"]

