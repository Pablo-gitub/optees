# Shortest Paths With Dijkstra

## Model

Let a graph contain vertices `V` and weighted edges `E`. Given a source `s` and
destination `t`, choose a path `P` that minimizes the total edge weight:

```text
min sum(w_e for e in P)
```

Weights can represent distance, time, money, energy, or any additive quantity.
They must be finite and non-negative in this workflow.

## Why The Algorithm Works

Dijkstra maintains a tentative distance for each vertex. Initially only `s` has
distance zero. At each step it settles the unsettled vertex with the smallest
tentative distance and relaxes its outgoing edges.

When a vertex is settled, its distance is final. Any competing path would have
to pass through an unsettled vertex whose tentative distance is no smaller, and
then add a non-negative edge weight. This argument fails when negative edges
exist, so Optees rejects them here.

## Result Interpretation

The solution view shows the selected route, its total weight, and the settling
order. If the destination is **Unreachable**, the algorithm has exhausted every
vertex reachable from the source; it is not a solver failure.

## Scope

This first graph workflow supports finite directed or undirected graphs and
non-negative edge weights. Negative edges, all-pairs paths, spanning trees,
flows, matching, and TSP are separate future workflows.
