"""Versioned JSON import/export for Dijkstra shortest-path models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.vertex import GraphVertex
from optees.domain.models.graph.shortest_path_model import ShortestPathModel


GRAPH_JSON_VERSION = "1"
SHORTEST_PATH_PROBLEM_TYPE = "shortest_path"


def shortest_path_model_from_dict(data: Mapping[str, object]) -> ShortestPathModel:
    """Build the same validated model used by the manual graph form."""

    if not isinstance(data, Mapping):
        raise ValueError("graph JSON root must be an object")
    if str(data.get("version", "")) != GRAPH_JSON_VERSION:
        raise ValueError("unsupported graph JSON version")
    if str(data.get("problem_type", "")).strip().lower() != SHORTEST_PATH_PROBLEM_TYPE:
        raise ValueError("problem_type must be 'shortest_path'")
    directed = data.get("directed", True)
    if not isinstance(directed, bool):
        raise ValueError("graph directed must be a boolean")
    vertices_data = data.get("vertices")
    edges_data = data.get("edges")
    if not isinstance(vertices_data, list) or not isinstance(edges_data, list):
        raise ValueError("graph vertices and edges must be arrays")
    try:
        vertices = tuple(
            GraphVertex(
                identifier=_required_string(item, "id", "graph vertex"),
                label=_optional_string(item, "label", ""),
            )
            for item in vertices_data
        )
        edges = tuple(
            GraphEdge(
                source=_required_string(item, "from", "graph edge"),
                target=_required_string(item, "to", "graph edge"),
                weight=_required_value(item, "weight", "graph edge"),
            )
            for item in edges_data
        )
        return ShortestPathModel.from_parts(
            vertices=vertices,
            edges=edges,
            source=_required_string(data, "source", "graph"),
            destination=_required_string(data, "destination", "graph"),
            directed=directed,
        )
    except ValueError as exc:
        raise ValueError(f"invalid shortest-path JSON: {exc}") from exc


def shortest_path_model_to_dict(model: ShortestPathModel) -> dict[str, object]:
    """Serialize a shortest-path model without presentation-only state."""

    return {
        "version": GRAPH_JSON_VERSION,
        "problem_type": SHORTEST_PATH_PROBLEM_TYPE,
        "directed": model.directed,
        "vertices": [
            {"id": vertex.identifier, "label": vertex.label}
            for vertex in model.vertices
        ],
        "edges": [
            {"from": edge.source, "to": edge.target, "weight": edge.weight}
            for edge in model.edges
        ],
        "source": model.source,
        "destination": model.destination,
    }


def shortest_path_model_from_file(path: str | Path) -> ShortestPathModel:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read graph JSON: {exc}") from exc
    return shortest_path_model_from_dict(data)


def shortest_path_model_to_file(model: ShortestPathModel, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(shortest_path_model_to_dict(model), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _required_string(item: object, key: str, subject: str) -> str:
    value = _required_value(item, key, subject)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{subject} {key!r} must be a non-empty string")
    return value


def _optional_string(item: object, key: str, default: str) -> str:
    if not isinstance(item, Mapping):
        raise ValueError("graph entries must be objects")
    value = item.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"graph {key!r} must be a string")
    return value


def _required_value(item: object, key: str, subject: str) -> object:
    if not isinstance(item, Mapping):
        raise ValueError(f"{subject} must be an object")
    if key not in item:
        raise ValueError(f"{subject} is missing {key!r}")
    return item[key]
