from __future__ import annotations

import pytest

from optees.data.adapters.knapsack.multi_dimensional_knapsack_solver_adapter import (
    MultiDimensionalKnapsackSolverAdapter,
)


def test_adapter_wraps_multi_dimensional_branch_and_bound(monkeypatch):
    calls = []

    def fake_solve(values, usage_matrix, capacities):
        calls.append((values, usage_matrix, capacities))
        return 22.0, [0, 2]

    monkeypatch.setattr(
        "optees.data.adapters.knapsack.multi_dimensional_knapsack_solver_adapter.solve_multi_dimensional_knapsack",
        fake_solve,
    )

    adapter = MultiDimensionalKnapsackSolverAdapter(max_items=10)
    out = adapter.solve(
        {
            "values": [8, 9, 14, 7],
            "usage_matrix": [
                [4, 1.5],
                [5, 2],
                [6, 4.5],
                [3, 2],
            ],
            "capacities": [10, 6],
            "var_names": ["A", "B", "C", "D"],
            "resource_names": ["weight", "volume"],
        }
    )

    assert calls == [
        (
            [8, 9, 14, 7],
            [[4, 1.5], [5, 2], [6, 4.5], [3, 2]],
            [10, 6],
        )
    ]
    assert out["status"] == "Optimal"
    assert out["objective"] == 22.0
    assert out["selected_indices"] == [0, 2]
    assert out["x"] == {"A": 1.0, "B": 0.0, "C": 1.0, "D": 0.0}
    assert out["extras"]["method"] == "multidimensional_branch_and_bound"
    assert out["extras"]["total_usage"] == pytest.approx([10.0, 6.0])
    assert out["extras"]["remaining_capacities"] == pytest.approx([0.0, 0.0])


def test_adapter_refuses_instances_above_item_limit():
    adapter = MultiDimensionalKnapsackSolverAdapter(max_items=1)

    out = adapter.solve(
        {
            "values": [1, 2],
            "usage_matrix": [[1], [2]],
            "capacities": [3],
            "var_names": ["A", "B"],
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert out["selected_indices"] == []
    assert out["extras"]["max_items"] == 1
    assert "too large" in out["extras"]["message"]


def test_adapter_reports_invalid_input_as_not_solved():
    adapter = MultiDimensionalKnapsackSolverAdapter()

    out = adapter.solve(
        {
            "values": [1],
            "usage_matrix": [[1, 2]],
            "capacities": [1],
        }
    )

    assert out["status"] == "NotSolved"
    assert out["objective"] is None
    assert "usage row" in out["extras"]["message"]

