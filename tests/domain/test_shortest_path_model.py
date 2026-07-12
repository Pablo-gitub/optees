import pytest

from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.vertex import GraphVertex
from optees.domain.models.graph.shortest_path_model import ShortestPathModel


def test_shortest_path_model_accepts_valid_directed_graph() -> None:
    model = ShortestPathModel.from_parts(
        vertices=[GraphVertex("A", "Start"), GraphVertex("B", "Target")],
        edges=[GraphEdge("A", "B", 2.5)],
        source="A",
        destination="B",
    )

    assert model.directed
    assert model.vertex_label("A") == "Start"
    assert model.vertex_label("B") == "Target"


@pytest.mark.parametrize(
    "edge",
    [
        ("A", "B", -1),
        ("A", "A", 1),
        ("A", "B", float("inf")),
    ],
)
def test_graph_edges_reject_values_incompatible_with_dijkstra(edge) -> None:
    with pytest.raises(ValueError):
        GraphEdge(*edge)


def test_shortest_path_model_requires_declared_terminals_and_endpoints() -> None:
    vertices = [GraphVertex("A"), GraphVertex("B")]
    with pytest.raises(ValueError, match="source and destination"):
        ShortestPathModel.from_parts(
            vertices=vertices,
            edges=[],
            source="A",
            destination="C",
        )
    with pytest.raises(ValueError, match="every graph edge"):
        ShortestPathModel.from_parts(
            vertices=vertices,
            edges=[GraphEdge("A", "C", 1)],
            source="A",
            destination="B",
        )
