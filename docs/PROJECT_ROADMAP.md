# Optees Project Roadmap

This document is the central roadmap for the project. Specialized roadmap files
remain useful when deep implementation detail is needed, but this page should
make it quick to understand what is already implemented, what is being
consolidated, and where the next algorithm families are going.

## Guiding Principles

- Every algorithm should have a mathematical model, use case, solver adapter,
  formulation UI, solution UI, examples, educational problem description, and
  tests.
- Scientific benchmarks should be small, reproducible, and separated from slow
  or optional tests.
- Importable formats should converge toward readable, versioned JSON. Scientific
  datasets may keep dedicated adapters, but they should not become the primary
  GUI format.
- Educational features should show not only "the answer", but also how the
  model behaves mathematically.

## Implemented

### Linear Programming (LP)

- Continuous LP model with variables, bounds, objective, and constraints.
- LP JSON import/export.
- SciPy/HiGHS solver through an adapter.
- Main statuses: `Optimal`, `Infeasible`, `Unbounded`, `NotSolved`.
- Multiple-optima analysis:
  - after finding `z*`, Optees adds the optimal-face constraint;
  - it solves auxiliary LPs `min x_i` and `max x_i`;
  - it shows the available optimal range for each variable.
- `Example` and `Problem description` pages.
- Dedicated charts and solution view.
- Tests on synthetic cases and LP Netlib datasets under `tests/data/lp/`.

### Mixed-Integer Linear Programming (MILP)

- MILP model with continuous, integer, and binary/Boolean variables.
- Mathematical normalization of binary variables to bounds `[0, 1]`.
- MILP JSON import/export.
- OR-Tools CP-SAT/CBC solver through an adapter.
- `Feasible` status separated from `NotSolved`.
- Solver options: `time_limit` and `mip_gap`.
- First formulation UI:
  - variables;
  - integrality;
  - bounds;
  - objective;
  - constraints;
  - solver options;
  - JSON import;
  - information buttons.
- `Example` and `Problem description` pages, including threshold/piecewise
  examples.
- MIPLIB 2017 dataset already present under `tests/data/miplib2017/`.

MILP details and pending work: `docs/MILP_ROADMAP.md`.

### Knapsack

- Implemented variants:
  - 0/1 Knapsack;
  - Bounded Knapsack;
  - Unbounded Knapsack;
  - Fractional Knapsack;
  - Multi-dimensional Knapsack with 0/1, bounded, unbounded, or fractional
    domain.
- Dedicated domain models for the main variants.
- Dedicated solver/use case/adapter layers.
- GUI with variant switch.
- Unified JSON import for all variants.
- Information buttons, `Example` page, and `Problem description` page.
- Solution view with summary, table, and charts:
  - used/residual capacity;
  - multi-dimensional resource usage;
  - value/weight or value/usage bar chart;
  - selected-item highlighting.
- Presentation and utility tests.
- Burkardt adapter kept as a backend benchmark, not as a GUI button.

### Release And Updates

- GitHub Actions desktop release generation.
- Application updater:
  - GitHub Releases check in packaged builds;
  - Home banner when a new version exists;
  - version/update status note in Settings.
- Internal version read from `src/optees/__init__.py`.

## In Progress / To Consolidate

### Scientific Benchmarks

Goal: increase numerical confidence without making the standard suite heavy.

- LP:
  - Netlib already present.
- MILP:
  - MIPLIB already present;
  - extract the MPS adapter from tests before exposing MPS import in the GUI.
- Knapsack:
  - keep Burkardt 0/1;
  - add a small, reliable subset for multi-dimensional knapsack;
  - add selected or generated bounded/unbounded cases with known solutions;
  - use a `slow` marker for large instances.

Candidate sources for Knapsack:

- OR-Library / Beasley, especially useful for multi-dimensional knapsack.
- Pisinger, useful for hard knapsack instances and generators.

### Technical Documentation

- Update `docs/DATASETS.md` with every dataset actually included.
- Document, for each family:
  - data format;
  - source;
  - license/usage terms when declared;
  - which tests use it;
  - which tests are standard and which are slow.

## Upcoming Algorithms

### Nonlinear Programming (NLP)

The Nonlinear section should cover continuous optimization with nonlinear
functions. Proposed roadmap:

- Unconstrained NLP:
  - minimization/maximization without constraints;
  - examples: Rosenbrock, Himmelblau, nonlinear quadratics.
- Bound-constrained NLP:
  - constraints `lb <= x <= ub`;
  - local SciPy `minimize` solvers.
- Constrained NLP:
  - nonlinear inequalities `g(x) <= 0`;
  - nonlinear equalities `h(x) = 0`.
- Least squares / curve fitting:
  - parameter estimation;
  - nonlinear regression;
  - experimental-data fitting.
- Simple Quadratic Programming:
  - quadratic objective;
  - linear constraints;
  - natural bridge between LP/MILP and NLP.
- Minimax optimization:
  - form `min max_i f_i(x)`;
  - epigraph reformulation with variable `t`:

    ```text
    minimize   t
    subject to f_i(x) <= t  for every i
    ```

- Global optimization, later phase:
  - differential evolution;
  - basin hopping;
  - simulated annealing.

Do not confuse this with game-tree minimax: game-tree minimax is not NLP and
belongs in AI/Graph.

### Graph Theory

Proposed roadmap:

- Shortest path:
  - Dijkstra;
  - Bellman-Ford;
  - Floyd-Warshall.
- Minimum spanning tree:
  - Kruskal;
  - Prim.
- Max flow / min cut:
  - Edmonds-Karp;
  - Dinic in a later phase.
- Matching / assignment:
  - bipartite matching;
  - Hungarian algorithm.
- Traveling Salesman Problem:
  - educational formulation;
  - initial heuristics;
  - possible MILP comparison.
- Game-tree minimax:
  - game tree;
  - alpha-beta pruning;
  - belongs to AI/Graph, not nonlinear programming.

### AI & Machine Learning

Long-term roadmap:

- Linear and polynomial regression.
- Basic classification.
- Clustering.
- Feature selection as an optimization problem.
- Links to Knapsack/MILP when selection requires binary variables.

## Web Landing Page

The landing page lives in the same repository as a monorepo-style app.
Current decision:

```text
apps/
  website/
```

Rationale:

- clearly separates desktop app and website;
- avoids maintaining a second repository;
- lets the site link directly to GitHub Releases;
- allows separate CI/CD workflows.
- keeps visual marketing work close to release assets and screenshots.

Current first implementation:

```text
apps/
  website/
    package.json
    vite.config.ts
    src/
      App.tsx
      i18n.ts
      main.tsx
      styles.css
    public/
      logo/
      screenshots/
    scripts/
      capture_app_screenshots.py
```

Recommended stack:

- React + Vite for the first landing page implementation;
- static production output;
- bilingual copy matching the desktop app languages: English and Italian;
- downloads linked to GitHub Releases;
- "Algorithms" section maintained manually at first or generated from docs later;
- screenshots generated from the desktop app through a repeatable script;
- deploy through GitHub Pages or equivalent static hosting.

Separate workflows:

- `.github/workflows/release.yml` for the desktop app;
- `.github/workflows/website.yml` for the website.

Before publishing:

- refine visual design and responsive layout;
- verify SEO metadata and social preview assets;
- add a website CI workflow with `npm ci` and `npm run build`;
- decide whether GitHub Pages should publish from `apps/website/dist` or from
  a dedicated deployment branch/action.

## Recommended Next Steps

1. Close release `v0.2.1` with a coherent internal version.
2. Add small, documented Knapsack benchmarks.
3. Start the NLP roadmap with domain model/use case for unconstrained NLP.
4. Implement a minimal NLP GUI.
5. Add NLP solution view and educational pages.
6. Refine `apps/website/` and add the website publish workflow when the landing
   page is ready.
