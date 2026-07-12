import pytest

from optees.utility.graph_utils import solve_dijkstra


def test_dijkstra_finds_shortest_directed_path_and_settlement_trace() -> None:
    status, distance, path, extras = solve_dijkstra(
        {
            "vertices": ["A", "B", "C", "D"],
            "edges": [
                {"source": "A", "target": "B", "weight": 4},
                {"source": "A", "target": "C", "weight": 1},
                {"source": "C", "target": "B", "weight": 2},
                {"source": "B", "target": "D", "weight": 1},
                {"source": "C", "target": "D", "weight": 8},
            ],
            "source": "A",
            "destination": "D",
            "directed": True,
        }
    )

    assert status == "PathFound"
    assert distance == pytest.approx(4.0)
    assert path == ("A", "C", "B", "D")
    assert extras["settled_order"] == ("A", "C", "B", "D")
    assert extras["settled_distances"] == {"A": 0.0, "C": 1.0, "B": 3.0, "D": 4.0}


def test_dijkstra_uses_edges_in_both_directions_for_undirected_models() -> None:
    status, distance, path, _extras = solve_dijkstra(
        {
            "vertices": ["A", "B", "C"],
            "edges": [
                {"source": "A", "target": "B", "weight": 2},
                {"source": "B", "target": "C", "weight": 3},
            ],
            "source": "C",
            "destination": "A",
            "directed": False,
        }
    )

    assert status == "PathFound"
    assert distance == pytest.approx(5.0)
    assert path == ("C", "B", "A")


def test_dijkstra_reports_unreachable_destination() -> None:
    status, distance, path, extras = solve_dijkstra(
        {
            "vertices": ["A", "B", "C"],
            "edges": [{"source": "A", "target": "B", "weight": 1}],
            "source": "A",
            "destination": "C",
            "directed": True,
        }
    )

    assert status == "Unreachable"
    assert distance is None
    assert path == ()
    assert extras["settled_order"] == ("A", "B")


def test_dijkstra_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        solve_dijkstra(
            {
                "vertices": ["A", "B"],
                "edges": [{"source": "A", "target": "B", "weight": -1}],
                "source": "A",
                "destination": "B",
            }
        )
