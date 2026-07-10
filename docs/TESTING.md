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

## Commands
```bash
# run the complete suite from a source checkout
PYTHONPATH=src python -m pytest -q

# run the scientific/reference knapsack tests
PYTHONPATH=src python -m pytest -q \
  tests/utility/test_io_knapsack.py \
  tests/utility/test_orlib_mknap_adapter.py \
  tests/application/usecases/test_solve_knapsack_burkardt.py \
  tests/application/usecases/test_solve_multi_dimensional_knapsack_orlib.py \
  tests/application/usecases/test_solve_knapsack_reference_cases.py
```

## Reproducibility

* Pin Python and core dependencies in the project environment.
* Keep adapters deterministic; avoid hidden randomness.
* Store small datasets under `tests/data/...`; larger ones are documented with
  links, checksums, and an explicit runtime budget.
