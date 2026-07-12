from optees.application.usecases.solve_shortest_path_usecase import SolveShortestPathUseCase
from optees.domain.entities.graph.edge import GraphEdge
from optees.domain.entities.graph.vertex import GraphVertex
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.domain.value_objects.graph.shortest_path_status import ShortestPathStatus


class FakeShortestPathSolver:
    def __init__(self) -> None:
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "PathFound",
            "distance": 3,
            "path": ["A", "B"],
            "extras": {"settled_order": ["A", "B"], "settled_distances": {"A": 0, "B": 3}},
        }


def test_solve_shortest_path_usecase_maps_model_and_result() -> None:
    model = ShortestPathModel.from_parts(
        vertices=[GraphVertex("A"), GraphVertex("B")],
        edges=[GraphEdge("A", "B", 3)],
        source="A",
        destination="B",
        directed=True,
    )
    solver = FakeShortestPathSolver()

    solution = SolveShortestPathUseCase(solver).execute(model)

    assert solver.problem == {
        "vertices": ["A", "B"],
        "edges": [{"source": "A", "target": "B", "weight": 3.0}],
        "source": "A",
        "destination": "B",
        "directed": True,
    }
    assert solution.status is ShortestPathStatus.PATH_FOUND
    assert solution.distance == 3.0
    assert solution.path == ("A", "B")
