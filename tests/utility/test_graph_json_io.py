import pytest

from optees.utility.graph_json_io import (
    shortest_path_model_from_dict,
    shortest_path_model_to_dict,
)


_PAYLOAD = {
    "version": "1",
    "problem_type": "shortest_path",
    "directed": True,
    "vertices": [
        {"id": "A", "label": "Depot"},
        {"id": "B", "label": "Customer"},
    ],
    "edges": [{"from": "A", "to": "B", "weight": 3.5}],
    "source": "A",
    "destination": "B",
}


def test_shortest_path_json_round_trip() -> None:
    model = shortest_path_model_from_dict(_PAYLOAD)

    assert shortest_path_model_to_dict(model) == _PAYLOAD


@pytest.mark.parametrize(
    "patch",
    [
        {"version": "2"},
        {"problem_type": "knapsack"},
        {"directed": "yes"},
        {"source": "missing"},
    ],
)
def test_shortest_path_json_rejects_invalid_structure(patch) -> None:
    data = dict(_PAYLOAD)
    data.update(patch)

    with pytest.raises(ValueError):
        shortest_path_model_from_dict(data)
