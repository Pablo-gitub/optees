# Algorithms: Implemented & Planned

## Implemented (MVP)
### Linear Programming (continuous)
- `solve_lp(problem, method="highs")` using SciPy/HiGHS.
  - Methods: `highs`, `highs-ds`, `highs-ipm`.
  - Optional: sensitivity via HiGHS marginals (to be exposed by `perform_sensitivity_analysis`).

### 0/1 Knapsack
- `solve_knapsack_01(values, weights, capacity)` baseline DP (`O(n·capacity)`).
  - Deterministic reconstruction; good for teaching & tests.

## Near-term roadmap
### MILP / Branch-and-Bound
- Wrapper on **OR-Tools CP-SAT** for integer/boolean models (`solve_milp`).
- Goal: single canonical MILP schema (vars, domains, linear constraints, objective).

### Pre-processing
- `pre_process_lp_data`: drop zero rows/cols, normalize bounds, simple scaling.
- Redundant constraints detection (basic linear algebra / rank checks).

### Educational UX
- Dual explanations (simple + detailed math).
- Algorithm steps visualization for small instances (e.g., knapsack DP table snapshots).

## Design principles
- Prefer robust, maintained libraries (SciPy/HiGHS, OR-Tools).
- Keep wrappers thin and inputs canonical.
- Make “fallbacks” explicit (e.g., DP for small knapsack, OR-Tools for large).