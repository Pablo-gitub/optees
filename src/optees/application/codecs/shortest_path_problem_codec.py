from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.utility.graph_json_io import shortest_path_model_from_dict


def shortest_path_model_from_public_dict(
    payload: dict[str, JsonValue],
) -> ShortestPathModel:
    required = (
        "version",
        "problem_type",
        "directed",
        "vertices",
        "edges",
        "source",
        "destination",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "graph.shortest_path.dijkstra is missing required fields: "
            + ", ".join(missing)
        )
    return shortest_path_model_from_dict(payload)
