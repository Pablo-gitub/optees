from __future__ import annotations

import json

import pytest

from optees.application.codecs.shortest_path_problem_codec import (
    shortest_path_model_from_public_dict,
)
from optees.application.codecs.shortest_path_result_codec import (
    ShortestPathResultCodec,
)
from optees.domain.entities.graph.solution import ShortestPathSolution


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "shortest_path",
        "directed": True,
        "vertices": [
            {"id": "A", "label": "Depot"},
            {"id": "B", "label": "Customer"},
        ],
        "edges": [{"from": "A", "to": "B", "weight": 3}],
        "source": "A",
        "destination": "B",
    }


def test_problem_codec_preserves_graph_contract():
    model = shortest_path_model_from_public_dict(_payload())

    assert model.directed is True
    assert [vertex.identifier for vertex in model.vertices] == ["A", "B"]
    assert model.vertices[0].label == "Depot"
    assert model.edges[0].weight == pytest.approx(3.0)
    assert (model.source, model.destination) == ("A", "B")


def test_problem_codec_requires_explicit_public_fields():
    payload = _payload()
    del payload["directed"]

    with pytest.raises(ValueError, match="missing required fields: directed"):
        shortest_path_model_from_public_dict(payload)


@pytest.mark.parametrize("weight", [-1, float("inf"), float("nan")])
def test_problem_codec_rejects_invalid_edge_weights(weight):
    payload = _payload()
    payload["edges"][0]["weight"] = weight

    with pytest.raises(ValueError, match="weight|non-negative|finite"):
        shortest_path_model_from_public_dict(payload)


def test_result_codec_serializes_path_and_dijkstra_trace():
    solution = ShortestPathSolution.from_solver_result(
        status="PathFound",
        distance=4,
        path=["A", "C", "B", "D"],
        extras={
            "settled_order": ["A", "C", "B", "D"],
            "settled_distances": {"A": 0, "C": 1, "B": 3, "D": 4},
            "message": "destination settled by Dijkstra",
        },
    )

    serialized = ShortestPathResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "optimal"
    assert serialized.result == {
        "distance": 4.0,
        "path": ["A", "C", "B", "D"],
        "hop_count": 3,
    }
    assert serialized.diagnostics["settled_count"] == 4
    assert serialized.diagnostics["settled_distances"]["D"] == 4.0
    json.dumps(serialized.result, allow_nan=False)
    json.dumps(serialized.diagnostics, allow_nan=False)


def test_result_codec_maps_unreachable_destination_to_infeasible():
    solution = ShortestPathSolution.from_solver_result(
        status="Unreachable",
        distance=None,
        path=[],
        extras={
            "settled_order": ["A"],
            "settled_distances": {"A": 0},
            "message": "destination is unreachable from source",
        },
    )

    serialized = ShortestPathResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "infeasible"
    assert serialized.result == {"distance": None, "path": [], "hop_count": 0}
    assert "No path" in serialized.warnings[0]
