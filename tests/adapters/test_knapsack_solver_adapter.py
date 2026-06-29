from __future__ import annotations

from optees.data.adapters.knapsack.knapsack_solver_adapter import KnapsackSolverAdapter


def test_adapter_wraps_dynamic_programming_utility(monkeypatch):
    calls = []

    def fake_solve(values, weights, capacity):
        calls.append((values, weights, capacity))
        return 9.0, [0, 2]

    monkeypatch.setattr(
        "optees.data.adapters.knapsack.knapsack_solver_adapter.solve_knapsack_01",
        fake_solve,
    )

    adapter = KnapsackSolverAdapter(max_dp_cells=1_000)
    out = adapter.solve(
        {
            "values": [4, 5, 5],
            "weights": [2, 3, 3],
            "capacity": 5,
            "var_names": ["A", "B", "C"],
        }
    )

    assert calls == [([4, 5, 5], [2, 3, 3], 5)]
    assert out["status"] == "Optimal"
    assert out["objective"] == 9.0
    assert out["selected_indices"] == [0, 2]
    assert out["x"] == {"A": 1.0, "B": 0.0, "C": 1.0}
    assert out["extras"]["method"] == "dynamic_programming"
    assert out["extras"]["remaining_capacity"] == 0


def test_adapter_refuses_instances_above_dp_cell_limit():
    adapter = KnapsackSolverAdapter(max_dp_cells=10)

    out = adapter.solve(
        {
            "values": [1, 2, 3],
            "weights": [1, 2, 3],
            "capacity": 100,
            "var_names": ["A", "B", "C"],
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert out["selected_indices"] == []
    assert out["extras"]["dp_cells"] == 404
    assert out["extras"]["max_dp_cells"] == 10
    assert "too large" in out["extras"]["message"]
