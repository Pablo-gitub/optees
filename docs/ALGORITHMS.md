# Algorithms: Implemented & Planned

## Implemented (MVP)
### Linear Programming (continuous)
- `solve_lp(problem, method="highs")` using SciPy/HiGHS.
  - Methods: `highs`, `highs-ds`, `highs-ipm`.
  - Sensitivity snapshot via HiGHS marginals in `perform_sensitivity_analysis`.
  - Alternate optima detection via optimal-face ranges: after finding `z*`, the solver adds `c^T x = z*` and computes `min/max x_i` for each variable.
  - Range analysis runs automatically for models up to 50 variables; larger benchmark models can opt in with `compute_optimal_ranges="always"`.

### 0/1 Knapsack
- `solve_knapsack_01(values, weights, capacity)` baseline DP (`O(n·capacity)`).
  - Deterministic reconstruction; good for teaching & tests.

## Near-term roadmap
### MILP / Branch-and-Bound
- Wrapper on **OR-Tools CP-SAT** for integer/boolean models (`solve_milp`).
- Goal: single canonical MILP schema (vars, domains, linear constraints, objective).

### Pre-processing
- `pre_process_lp_data`: conservative cleanup for redundant equalities and proportional duplicate inequalities.
- Redundant equality removal checks the augmented system `[A | b]` so inconsistent dependent rows are preserved and reported by the solver.

### Educational UX
- Dual explanations (simple + detailed math).
- Algorithm steps visualization for small instances (e.g., knapsack DP table snapshots).

## Design principles
- Prefer robust, maintained libraries (SciPy/HiGHS, OR-Tools).
- Keep wrappers thin and inputs canonical.
- Make “fallbacks” explicit (e.g., DP for small knapsack, OR-Tools for large).
