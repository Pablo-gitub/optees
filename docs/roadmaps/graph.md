# Graph Theory Feature Plan

## Document Status

- **State:** maintenance
- **Shipped baseline:** the complete Dijkstra shortest-path vertical slice
- **Remaining scope:** external benchmark hardening and later graph algorithms
- **Authority:** `project.md` decides when later graph expansion resumes

## Scope: Shortest Path With Dijkstra

This document records the first vertical Graph Theory slice. It deliberately
implements one complete, explainable workflow before adding other graph
algorithms.

### Domain And Solver

- [x] Directed or undirected finite graph model with labelled vertices.
- [x] Finite non-negative weighted edges only; negative weights are rejected.
- [x] Deterministic Dijkstra implementation with priority queue and path
  reconstruction.
- [x] Return settled-node order and final settled distances for explanation.
- [x] Distinguish a found path, an unreachable destination, and invalid input.

### Import And Tests

- [x] Versioned JSON import/export for vertices, edges, direction, and terminals.
- [x] Unit tests for directed, undirected, unreachable, and negative-weight
  cases, plus domain, JSON, and use-case tests.
- [ ] Add an external graph benchmark corpus during the cross-family
  benchmark-hardening phase, with provenance, known outcomes, and CI budget.

### Presentation

- [x] Formulation view for vertices, weighted edges, direction, source, and
  destination.
- [x] Result view with route, total weight, settled-node table, and highlighted
  graph drawing.
- [x] English and Italian example/problem-description pages and a reusable JSON
  example.
- [x] Add presentation tests for manual input, import, path rendering, and the
  unreachable state.

## Explicitly Deferred

- Negative edges and Bellman-Ford.
- All-pairs shortest paths, spanning trees, max flow/min cut, matching, and
  TSP.
- Manual graph positioning and benchmark import UI.
