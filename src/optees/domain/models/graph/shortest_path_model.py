from __future__ import annotations

from dataclasses import dataclass

from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.vertex import GraphVertex


@dataclass(frozen=True)
class ShortestPathModel:
    """Weighted graph and terminal pair for a Dijkstra shortest-path run."""

    vertices: tuple[GraphVertex, ...]
    edges: tuple[GraphEdge, ...]
    source: str
    destination: str
    directed: bool = True

    def __post_init__(self) -> None:
        vertices = tuple(self.vertices)
        edges = tuple(self.edges)
        if not vertices:
            raise ValueError("shortest-path model must contain at least one vertex")
        identifiers = tuple(vertex.identifier for vertex in vertices)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("graph vertex identifiers must be unique")
        source = str(self.source or "").strip()
        destination = str(self.destination or "").strip()
        if source not in identifiers or destination not in identifiers:
            raise ValueError("source and destination must reference declared vertices")
        for edge in edges:
            if edge.source not in identifiers or edge.target not in identifiers:
                raise ValueError("every graph edge must reference declared vertices")
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "destination", destination)
        object.__setattr__(self, "directed", bool(self.directed))

    @classmethod
    def from_parts(
        cls,
        *,
        vertices: list[GraphVertex] | tuple[GraphVertex, ...],
        edges: list[GraphEdge] | tuple[GraphEdge, ...],
        source: str,
        destination: str,
        directed: bool = True,
    ) -> "ShortestPathModel":
        return cls(tuple(vertices), tuple(edges), source, destination, directed)

    def vertex_label(self, identifier: str) -> str:
        for vertex in self.vertices:
            if vertex.identifier == identifier:
                return vertex.label or vertex.identifier
        return identifier
