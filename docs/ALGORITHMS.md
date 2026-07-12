# Algorithms: Implemented And Planned

This is the concise algorithm catalogue. The authoritative implementation order
and completion criteria are in `docs/PROJECT_ROADMAP.md`.

## Implemented

### Linear Programming

- Continuous LP through SciPy/HiGHS.
- `highs`, `highs-ds`, and `highs-ipm` methods.
- Infeasible, unbounded, and not-solved statuses.
- Multiple-optima ranges: after finding `z*`, Optees adds `c^T x = z*` and
  solves `min x_i` and `max x_i` for each variable.

### Mixed-Integer Linear Programming

- Continuous, integer, and binary decision variables.
- OR-Tools adapter with time-limit and MIP-gap options.
- `Optimal` and `Feasible` kept distinct.
- Linear threshold and piecewise formulations can be entered manually; a guided
  wizard is planned.

### Knapsack

- 0/1 Knapsack: exact dynamic programming.
- Bounded Knapsack: exact dynamic programming over admissible quantities.
- Unbounded Knapsack: exact dynamic programming with repeated item types.
- Fractional Knapsack: exact greedy selection by value/weight density.
- Multi-dimensional Knapsack: exact 0/1 branch-and-bound; the formulation UI
  delegates bounded and unbounded domains to MILP and fractional domains to LP.

### Continuous Nonlinear Programming

- Scalar continuous objectives with optional box bounds and a required feasible
  initial point.
- Safe expression language: declared variables, arithmetic, powers, and a
  restricted set of one-argument elementary functions. User text is never
  evaluated as arbitrary Python.
- SciPy local numerical methods: BFGS and Nelder-Mead for unbounded problems,
  L-BFGS-B for box-bounded problems.
- `Converged`, `IterationLimit`, `Failed`, and `NotSolved` states. `Converged`
  is a local numerical termination state, not a global-optimum certificate.
- Versioned JSON import/export, localized formulation/result pages, objective
  trace, and analytic reference regressions for Rosenbrock, Himmelblau,
  bounded quadratics, and maximization.

### Modeling Assistant

- Local deterministic family recommendation for LP, MILP, Knapsack, NLP,
  Scheduling, and Robust Optimization.
- Conservative LP/MILP/Knapsack JSON drafting validated against Optees
  importers. NLP is currently recommendation-only; structured NLP drafting is
  deferred until its question-and-validation workflow exists.

### Graph Theory: Dijkstra Shortest Path

- Directed and undirected finite weighted graphs with source and destination.
- Deterministic Dijkstra implementation for finite non-negative edge weights.
- Path reconstruction, total weight, settled-node trace, JSON import, and a
  highlighted graph result view.
- A returned **Unreachable** status means no route exists from the selected
  source to destination; it is not a solver failure.

## Planned Families

The next sections are introduced in this order:

1. Heuristics & Metaheuristics: TSP constructive/local-search baseline, then
   Simulated Annealing and problem-specific metaheuristics.
2. Scheduling and Robust/Stochastic Optimization: workflow-specific models
   built first on the MILP, Graph, and Heuristic foundations.
3. AI & Machine Learning: educational models and optimization links after the
   optimization families are stable.

## Cross-Family Methods

- Linear minimax/maximin and Chebyshev goal programming belong in LP/MILP.
- Nonlinear minimax belongs in NLP.
- Min-max regret, newsvendor, and revenue management belong to Robust
  Optimization workflows.
- Game-tree minimax and alpha-beta pruning belong to Graph Theory / AI.

Heuristics are never presented as proof-producing exact methods. Their results
must report the random seed where applicable, run budget, elapsed time,
feasibility status, and the best-so-far objective trace.
