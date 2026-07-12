"""Local graph algorithms used by Optees graph-theory workflows."""

from __future__ import annotations

import heapq
import math
from collections.abc import Mapping
from typing import Any


def solve_dijkstra(problem: Mapping[str, object]) -> tuple[str, float | None, tuple[str, ...], dict[str, object]]:
    """Solve a finite non-negative shortest-path problem deterministically.

    A node becomes *settled* when it is removed from the priority queue with its
    final distance. With non-negative weights, no later path can improve that
    distance; the returned order is therefore both an algorithm trace and an
    explanation of why the reconstructed destination path is shortest.
    """

    vertices = tuple(str(vertex) for vertex in problem.get("vertices", ()) or ())
    if not vertices or len(vertices) != len(set(vertices)):
        raise ValueError("Dijkstra requires unique declared vertices")
    source = str(problem.get("source") or "").strip()
    destination = str(problem.get("destination") or "").strip()
    if source not in vertices or destination not in vertices:
        raise ValueError("Dijkstra source and destination must be declared vertices")
    directed = bool(problem.get("directed", True))
    adjacency: dict[str, list[tuple[str, float]]] = {vertex: [] for vertex in vertices}
    for raw_edge in problem.get("edges", ()) or ():
        if not isinstance(raw_edge, Mapping):
            raise ValueError("Dijkstra edges must be objects")
        origin = str(raw_edge.get("source") or "").strip()
        target = str(raw_edge.get("target") or "").strip()
        if origin not in adjacency or target not in adjacency or origin == target:
            raise ValueError("Dijkstra edges must join two declared distinct vertices")
        weight = _non_negative_weight(raw_edge.get("weight"))
        adjacency[origin].append((target, weight))
        if not directed:
            adjacency[target].append((origin, weight))
    for neighbours in adjacency.values():
        neighbours.sort(key=lambda entry: (entry[0], entry[1]))

    distances = {vertex: math.inf for vertex in vertices}
    predecessors: dict[str, str] = {}
    distances[source] = 0.0
    queue: list[tuple[float, str]] = [(0.0, source)]
    settled_order: list[str] = []
    settled_distances: dict[str, float] = {}

    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        settled_order.append(vertex)
        settled_distances[vertex] = distance
        if vertex == destination:
            path = _reconstruct_path(predecessors, source, destination)
            return (
                "PathFound",
                distance,
                path,
                {
                    "settled_order": tuple(settled_order),
                    "settled_distances": settled_distances,
                    "message": "destination settled by Dijkstra",
                },
            )
        for neighbour, weight in adjacency[vertex]:
            candidate = distance + weight
            if candidate < distances[neighbour]:
                distances[neighbour] = candidate
                predecessors[neighbour] = vertex
                heapq.heappush(queue, (candidate, neighbour))

    return (
        "Unreachable",
        None,
        (),
        {
            "settled_order": tuple(settled_order),
            "settled_distances": settled_distances,
            "message": "destination is unreachable from source",
        },
    )


def find_shortest_path_dijkstra(graph_data, start_node, end_node):
    """Compatibility wrapper for the historical helper API.

    ``graph_data`` must use the canonical ``vertices``/``edges`` payload used
    by the application. The wrapper returns ``([], None)`` when no route exists.
    """

    payload = dict(graph_data or {})
    payload["source"] = start_node
    payload["destination"] = end_node
    status, distance, path, _extras = solve_dijkstra(payload)
    return (list(path), distance) if status == "PathFound" else ([], None)


def _non_negative_weight(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Dijkstra edge weights must be finite non-negative numbers")
    try:
        weight = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Dijkstra edge weights must be finite non-negative numbers") from exc
    if not math.isfinite(weight) or weight < 0:
        raise ValueError("Dijkstra requires finite non-negative edge weights")
    return weight


def _reconstruct_path(predecessors: Mapping[str, str], source: str, destination: str) -> tuple[str, ...]:
    path = [destination]
    while path[-1] != source:
        path.append(predecessors[path[-1]])
    path.reverse()
    return tuple(path)

def solve_max_flow(graph_data, source, sink):
    """
    Solves the max-flow min-cut problem to find the maximum flow through a network.

    Args:
        graph_data (dict): A dictionary representing the network graph with
                           edge capacities.
        source (str): The source node.
        sink (str): The sink node.

    Returns:
        float: The maximum flow value.
    """
    # TODO: Implement the max-flow algorithm using a specialized library.
    pass

def solve_minimum_spanning_tree(graph_data):
    """
    Finds the minimum spanning tree of a graph, connecting all nodes
    with the minimum possible total edge weight.

    Args:
        graph_data (dict): A dictionary representing the graph with edge weights.

    Returns:
        list: A list of edges representing the minimum spanning tree.
    """
    # TODO: Implement the minimum spanning tree algorithm (e.g., Kruskal's or Prim's).
    pass

def solve_tsp_heuristic(graph_data):
    """
    Finds an approximate solution to the Traveling Salesman Problem (TSP)
    using a heuristic approach.

    Args:
        graph_data (dict): A dictionary representing the graph with edge distances.

    Returns:
        tuple: A tuple containing the approximate shortest tour and its total distance.
    """
    # TODO: Implement a TSP heuristic (e.g., nearest neighbor or 2-opt).
    pass
