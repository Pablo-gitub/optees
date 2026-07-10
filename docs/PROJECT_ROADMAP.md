# Optees Project Roadmap

This is the authoritative implementation roadmap for Optees. Specialized
documents keep the detail for a single family, while this page decides the
order in which the product grows.

Related documents:

- `docs/MILP_ROADMAP.md` for MILP-specific completion work;
- `docs/DATASETS.md` for included scientific datasets;
- `docs/TESTING.md` for the test strategy;
- `docs/RELEASING.md` for build, signing, and tag verification;
- `docs/ALGORITHMS.md` for the concise algorithm catalogue.

## Product Standard

An algorithm family is considered complete enough to be exposed in the
application only when it has:

1. a precise domain model and documented mathematical formulation;
2. a use case and a solver adapter behind a stable port;
3. a versioned JSON format when a structured formulation is appropriate;
4. formulation and solution views that explain both the data and the result;
5. examples, an educational problem-description page, and localized UI text;
6. unit, integration, and presentation tests scaled to the risk of the
   implementation;
7. small reproducible reference cases, plus scientific benchmarks where they
   are available and suitable.

Exact solvers must distinguish a proven optimum from a feasible incumbent.
Heuristic methods must explicitly state that they return a best-found solution,
not a proof of optimality.

## Delivery Strategy

Optees will use a **breadth-first, then coordinated-depth** strategy.

- First, deliver one complete vertical slice for each major product section:
  Nonlinear Programming, Graph Theory, and Heuristics & Metaheuristics.
- Then expand the established families horizontally, adding comparable depth to
  LP/MILP, NLP, Graphs, and Heuristics.
- Cross-cutting features such as JSON import, benchmarks, solution explanation,
  the Modeling Assistant, localization, and release packaging evolve only when
  they can support the families that actually exist.

This avoids two bad outcomes: an application with only a very deep Linear
Programming section, and an application with many empty categories. Every new
section must earn its place through one usable end-to-end workflow before its
advanced variants are added.

## Current Baseline

### Linear Programming

- Continuous LP model with variables, bounds, objective, and constraints.
- SciPy/HiGHS adapter, JSON import/export, and core statuses.
- Multiple-optima analysis through optimal-face auxiliary LPs.
- Educational pages, solution charts, synthetic tests, and LP Netlib cases.

### Mixed-Integer Linear Programming

- Continuous, integer, and binary variables with binary normalization to
  bounds `[0, 1]`.
- OR-Tools adapter, JSON import/export, time limit, MIP gap, and `Feasible`
  versus `NotSolved` status.
- Formulation UI, educational pages, threshold/piecewise examples, and MIPLIB
  regression data.
- Remaining family-specific work is tracked in `docs/MILP_ROADMAP.md`.

### Knapsack

- 0/1, Bounded, Unbounded, Fractional, and Multi-dimensional variants.
- Variant-aware formulation UI, JSON import, dedicated solvers, solution
  summaries, tables, charts, Burkardt 0/1 cases, OR-Library multi-dimensional
  benchmark cases, and documented Bounded/Unbounded reference cases.

### Modeling Assistant

- Fully local, deterministic, rule-based solver recommendation.
- English and Italian natural-language regression prompts, including expert and
  beginner wording.
- Conservative LP, MILP, and Knapsack JSON drafting validated by the existing
  importers before the UI may load a draft.

### Product Delivery

- Desktop release workflow and packaged-build update checks through GitHub
  Releases.
- React/Vite website lives under `apps/website/` and remains a separate
  deployment track within this repository.

## Phased Implementation Plan

### Phase 0 - Consolidate The Current Baseline

**Completed for `0.4.0`.** The Modeling Assistant baseline is committed;
Knapsack coverage now includes documented reference cases and OR-Library
regression data; release metadata, runtime dependencies, bundle assets, and
documentation were verified together.

The macOS bundle was built from the repository, checked for its versioned
`Info.plist`, i18n/document/icon assets, ad-hoc signature, and an offscreen
startup. The GitHub workflow remains responsible for clean builds on the other
two supported platforms and for Developer ID signing/notarization when secrets
are configured.

### Phase 1 - Nonlinear Programming: First Vertical Slice

**Next implementation focus.** Start a complete continuous nonlinear
optimization workflow without opening another unfinished family in parallel.

The next new end-to-end family is continuous nonlinear optimization.

- Domain model for continuous variables, bounds, a nonlinear objective, and
  safe structured function representation. Do not evaluate arbitrary Python
  expressions entered by users.
- Unconstrained and bound-constrained minimization using maintained SciPy
  methods such as BFGS, Nelder-Mead, and L-BFGS-B where applicable.
- Formulation view for variables, bounds, initial point, method, and stopping
  options.
- Solution view showing status, candidate point, objective, iterations,
  termination reason, and convergence history.
- Educational examples and benchmark tests: Rosenbrock, Himmelblau, and small
  nonlinear quadratics.

**Explicitly deferred:** nonlinear constraints, least squares, quadratic
programming, nonlinear minimax, and global optimization.

### Phase 2 - Graph Theory: First Vertical Slice

The first graph workflow should be shortest path because it has a clear model,
a visual result, and accessible reference data.

- Directed/undirected weighted graph model and versioned JSON import/export.
- Graph editor with vertices, arcs, weights, source, and destination.
- Dijkstra for non-negative weights, with path reconstruction and explanation
  of settled nodes and total cost.
- Solution view that highlights the selected route over the input graph.
- Tests for hand-built examples and a small documented benchmark corpus.

**Explicitly deferred:** negative weights, all-pairs shortest paths, spanning
trees, flow, matching, and TSP.

### Phase 3 - Heuristics & Metaheuristics: First Vertical Slice

Heuristics deserves its own product section. It is a family of search methods,
not a mathematical-programming model, and it must make approximation and
reproducibility visible to the user.

The first vertical slice should use TSP after the Graph foundation exists:

- graph-tour model and a small TSP formulation view;
- deterministic constructive baseline: Nearest Neighbour;
- local improvement baseline: 2-opt;
- solution view with route, total distance, iterations, elapsed time, and
  best-so-far trace;
- fixed random seed and explicit run budget for every non-deterministic method;
- comparison against an exact result only for small instances where an exact
  baseline is practical.

The first true metaheuristic should be Simulated Annealing. Genetic Algorithm,
Tabu Search, Ant Colony Optimization, and other methods follow only after the
common run-reporting contract is stable.

**Explicitly deferred:** a generic "one metaheuristic for every problem"
abstraction. Each supported problem needs a valid encoding, neighbourhood,
feasibility repair, and objective evaluation contract.

### Phase 4 - Coordinated Family Expansion

Once the four major sections have one complete workflow, deepen them in an
order that reuses the new foundations.

| Family | Next capabilities |
| --- | --- |
| LP / MILP | Dedicated `MILPSolutionView`, MPS import adapter, threshold-model wizard, linear minimax/maximin, Chebyshev goal programming, and min-max regret where the model is linear. |
| Knapsack | Multiple-choice Knapsack, additional benchmark suites, and heuristic-versus-exact comparison for instances where DP or MILP becomes expensive. |
| NLP | Nonlinear constraints, least squares, quadratic programming, nonlinear minimax, and global methods such as differential evolution. |
| Graph Theory | Bellman-Ford, minimum spanning tree, max flow/min cut, matching, and exact/heuristic TSP comparison. |
| Heuristics | Simulated Annealing, then problem-specific Genetic Algorithm or Tabu Search; every result keeps seed, budget, incumbent trace, and feasibility diagnostics. |
| Scheduling | Parallel-machine makespan first, using a MILP formulation and later heuristic comparators; time-indexed and sequence-dependent models follow only with dedicated visualizations. |
| Robust & Stochastic Optimization | Explicit scenario model, min-max regret, then newsvendor and revenue-management workflows with uncertainty assumptions visible in the UI. |

### Phase 5 - Modeling Assistant: Structured Guidance

Expand the assistant only after the target formulation pages exist.

- Ask targeted follow-up questions instead of guessing omitted data.
- Draft and validate structured JSON for the newly implemented families.
- Explain optimal, infeasible, unbounded, and best-found heuristic results.
- Suggest modeling corrections while preserving the rule that no user model is
  overwritten without confirmation.
- Evaluate optional local or cloud LLM providers only through a benchmark suite
  that measures classification, drafting validity, safety, and reproducibility.
  No LLM provider is required for Optees.

### Phase 6 - AI & Machine Learning And Website Maturity

- Add educational regression, classification, clustering, and feature
  selection only after the optimization sections are stable.
- Use the website to document real released capabilities, benchmark evidence,
  screenshots, downloads, and algorithm limitations; it must not advertise
  unfinished families as available.

## Cross-Family Concepts

### Min-Max, Max-Min, And Regret

Min-max is not a standalone solver category. It belongs to the family that
defines the objective and constraints:

| Context | Correct placement |
| --- | --- |
| Linear continuous or mixed-integer models | LP/MILP, often through an epigraph variable or a Chebyshev goal-programming formulation. |
| Nonlinear objective or constraints | NLP. |
| Uncertain scenarios and regret | Robust Optimization models, initially documented within the Modeling Assistant and later exposed as a dedicated family/workflow. |
| Game trees | Graph Theory / AI, using minimax and alpha-beta pruning. |

Max-min follows the same rule: it is a modelling objective, not an algorithm
family by itself.

## Benchmark And Documentation Policy

- Every imported dataset records source, license or usage notes, file format,
  expected result, and the tests that consume it in `docs/DATASETS.md`.
- Small deterministic cases belong in the standard suite; large scientific cases
  may use `slow` markers.
- Each educational page must distinguish exact algorithms, numerical local
  optimization, and heuristics.
- `docs/PROJECT_ROADMAP.md` owns sequencing; specialized documents own detailed
  implementation checklists.

## Website Delivery Track

The website remains under `apps/website/`, built with React and Vite. It has a
separate publication workflow from the desktop application, but it follows the
same release evidence: localized content, tested screenshots, accurate download
links, SEO metadata, and no claims for features that have not shipped.
