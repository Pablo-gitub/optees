from __future__ import annotations

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.graph.solution import ShortestPathSolution
from optees.domain.value_objects.graph.shortest_path_status import ShortestPathStatus


_STATUS_MAP = {
    ShortestPathStatus.PATH_FOUND: MathematicalStatus.OPTIMAL,
    ShortestPathStatus.UNREACHABLE: MathematicalStatus.INFEASIBLE,
    ShortestPathStatus.NOT_SOLVED: MathematicalStatus.NOT_SOLVED,
}


class ShortestPathResultCodec:
    capability_id = "graph.shortest_path.dijkstra"
    result_schema_version = "1"

    def serialize(self, solution: ShortestPathSolution) -> SerializedResult:
        result = _strict_payload(
            {
                "distance": solution.distance,
                "path": list(solution.path),
                "hop_count": max(0, len(solution.path) - 1),
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "message": solution.message,
                "settled_order": list(solution.settled_order),
                "settled_distances": solution.settled_distances,
                "settled_count": len(solution.settled_order),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=_STATUS_MAP[solution.status],
            result=result,
            diagnostics=diagnostics,
            warnings=_warnings(solution.status),
        )


def _warnings(status: ShortestPathStatus) -> tuple[str, ...]:
    if status is ShortestPathStatus.UNREACHABLE:
        return ("No path connects the requested source and destination.",)
    if status is ShortestPathStatus.NOT_SOLVED:
        return ("Dijkstra produced no usable shortest-path result.",)
    return ()


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
