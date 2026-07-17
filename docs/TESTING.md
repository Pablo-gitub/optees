# Testing Strategy

## Philosophy
- **TDD first**: write a small failing test → implement → refactor.
- Keep the solver APIs **source-agnostic**; use adapters in tests when you want to verify parsing.
- Prefer **small, deterministic tests**; add smoke/integration tests for real datasets.

## Types of tests
- **Unit** (fast): pure functions, e.g. `solve_lp` on toy problems; `solve_knapsack_01` with tiny arrays.
- **Adapter tests**: parse external formats → check shapes, bounds, feasibility, and objective consistency.
- **Integration smoke**: end-to-end for a specific instance (adapter → solve → checks).
- **Performance (later)**: quick sanity on large problems with time/iter thresholds.
- **Property-based (optional)**: random feasible instances to check invariants.

## Current coverage
- `tests/utility/test_lp_utils.py`: toy LPs + LPnetlib MAT smoke via `load_lpnetlib_mat`.
- `tests/utility/test_knapsack_utils.py`: baseline DP cases.
- `tests/utility/test_io_knapsack_param.py`: auto-discovery of Burkardt-style instances.
- `tests/application/usecases/test_solve_knapsack_burkardt.py`: end-to-end 0/1
  reference cases and a DP-budget guard.
- `tests/utility/test_orlib_mknap_adapter.py`: OR-Library `mknap1` parsing and
  matrix-orientation checks.
- `tests/application/usecases/test_solve_multi_dimensional_knapsack_orlib.py`:
  published OR-Library optima for small multi-dimensional instances.
- `tests/application/usecases/test_solve_knapsack_reference_cases.py`:
  deterministic Bounded and Unbounded quantity regression cases.
- `tests/utility/test_miplib_milp_e2e.py`: size-capped, optional MIPLIB
  end-to-end checks when PuLP and the solver dependencies are available.
- `tests/utility/test_nlp_expression.py`: restricted expression syntax, unsafe
  constructs, invalid function domains, and finite-value checks.
- `tests/domain/test_nlp_model.py`, `tests/utility/test_nlp_utils.py`, and
  `tests/application/usecases/test_solve_nlp_usecase.py`: continuous NLP
  domain, numerical status, canonical mapping, and SciPy adapter coverage.
- `tests/utility/test_nlp_reference_cases.py`: Rosenbrock, Himmelblau,
  bounded quadratic, and maximization analytic regressions.
- `tests/presentation/test_nlp_flow_happy.py` and
  `tests/presentation/test_nlp_info_navigation.py`: localized NLP formulation,
  import, solution, educational-page, and info-dialog flows.
- `tests/domain/test_shortest_path_model.py`, `tests/utility/test_graph_utils.py`,
  `tests/utility/test_graph_json_io.py`, and
  `tests/application/usecases/test_solve_shortest_path_usecase.py`: Dijkstra
  model validation, directed/undirected path finding, unreachable terminals,
  non-negative weight checks, JSON, and canonical mapping.
- `tests/presentation/test_graph_flow_happy.py`: graph Home navigation, manual
  solve flow, imported graph form, highlighted route result, and unreachable
  explanation.
- `tests/domain/test_classification_model.py`,
  `tests/utility/test_classification_utils.py`,
  `tests/utility/test_classification_json_io.py`, and
  `tests/application/usecases/test_train_classification_usecase.py`: binary
  classification validation, local logistic regression, held-out metrics,
  versioned JSON, and canonical mapping.
- `tests/utility/test_classification_reference_cases.py`:
  deterministic two-dimensional logistic-regression reference case.
- `tests/adapters/test_assistant_classification_prompts.py`:
  equivalent English and Italian prompts across technical and colloquial
  descriptions.
- `tests/adapters/test_assistant_ai_drafting.py`: explicit English/Italian
  Regression and Binary Classification table drafts, importer validation,
  decimal-comma handling, and refusal of ambiguous or invalid datasets.
- `tests/presentation/test_classification_flow_happy.py`: Home navigation,
  train flow, imported data, localized documentation, and decision-boundary
  result view.
- `tests/interfaces/http/` and
  `tests/application/services/test_local_server_process*.py`: authenticated
  REST contracts, real loopback transport, subprocess lifecycle, occupied-port
  fallback, session-token replacement, OpenAPI access, and shutdown.

## Commands
```bash
# run the complete suite from a source checkout
PYTHONPATH=src python -m pytest -q

# profile the slowest tests while running the authoritative complete suite
PYTHONPATH=src python -m pytest -q --durations=40

# rerun only the previous failures and stop at the first new failure
PYTHONPATH=src python -m pytest -q --lf -x

# run the scientific/reference knapsack tests
PYTHONPATH=src python -m pytest -q \
  tests/utility/test_io_knapsack.py \
  tests/utility/test_orlib_mknap_adapter.py \
  tests/application/usecases/test_solve_knapsack_burkardt.py \
  tests/application/usecases/test_solve_multi_dimensional_knapsack_orlib.py \
  tests/application/usecases/test_solve_knapsack_reference_cases.py
```

## Runtime Baseline

The Phase 7 baseline on an Apple Silicon development machine is 883 passed,
6 skipped, and 3 third-party SWIG deprecation warnings in about 6 minutes.
Profiling showed two distinct expensive groups:

- scientific MIPLIB and Burkardt integrations account for roughly 96 seconds
  across the six slowest cases;
- localized presentation flows repeatedly construct the complete `MainWindow`
  and commonly require 3–5 seconds per case.

The next test-infrastructure iteration should therefore introduce explicit
`benchmark` and `gui` groups, measure `pytest-xdist` first on the non-GUI
subset with two and four workers, and gradually replace full-window fixtures
with narrower view/controller fixtures. Parallel execution must not become the
default until isolation is demonstrated. Dependency-based selection remains
secondary because i18n files, datasets, assets, and dynamic composition are
material non-code inputs.

## Reproducibility

* Pin Python and core dependencies in the project environment.
* Keep adapters deterministic; avoid hidden randomness.
* Store small datasets under `tests/data/...`; larger ones are documented with
  links, checksums, and an explicit runtime budget.
