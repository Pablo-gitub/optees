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

## Commands
```bash
# run all
python -m unittest -v

# run a module
python -m unittest -v tests.utility.test_lp_utils
````

## Reproducibility

* Pin Python & SciPy in `requirements.txt` / `environment.yml`.
* Keep adapters deterministic; avoid hidden randomness.
* Store small datasets under `tests/data/...`; larger ones documented with links and checksums.

