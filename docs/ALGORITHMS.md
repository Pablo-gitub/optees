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

### Single-Container 3D Packing

- Orthogonal placement of indivisible rectangular boxes inside one rectangular
  container, with duplicate dimensions removed from each item's admissible
  orientation set.
- Fixed, axis-specific, paired-axis, and unrestricted orthogonal rotation
  policies; diagonal placement is intentionally unsupported.
- Optional scalar capacities such as weight, selectable all-required or
  maximum-loaded-value policies, and no-gravity or simple-gravity modes.
- OR-Tools MILP backend with time limit, relative MIP gap, cooperative
  cancellation, complexity warnings, and a maximum-feasible recovery solve
  when the requested all-required model is infeasible.
- Result contract keeps requested and recovery solutions separate and reports
  placements, exclusions, used volume, objective, bound, gap, and diagnostics.
- The 3D result view is an educational orthogonal packing visualization, not a
  complete physical-stability simulation.

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

### Educational AI & Machine Learning: Linear Regression

- Local Ordinary Least Squares (OLS) and Ridge regression for finite numeric
  tabular datasets with continuous targets.
- Deterministic train/test split, fixed seed, MAE, MSE, RMSE, and R-squared
  reported separately for training and held-out test observations.
- Learned intercept and coefficients, prediction/residual table, and a fitted
  line chart when exactly one feature is selected.
- Independent arithmetic validation recomputes every published prediction,
  residual, split count, and train/test metric from the public model result.
- Versioned JSON import/export and analytic affine reference cases. Results
  are explicitly presented as predictive fits, not causal conclusions or
  guarantees of future performance. The current random holdout is intended for
  ordinary tabular relationships, not time-ordered forecasting.

### Educational AI & Machine Learning: Binary Classification

- Local binary logistic regression for finite numeric feature tables with
  exactly two non-empty target labels.
- Deterministic stratified train/test splitting. Feature standardization is
  fitted on training rows only and reused on held-out test rows, preventing
  train/test leakage.
- Accuracy, precision, recall, F1, confusion matrices, per-row predicted
  probabilities, and a 50% decision-boundary chart when exactly two features
  are selected.
- Versioned JSON import/export and reference cases for a linearly separable
  two-dimensional dataset. Results are explicitly educational predictive fits,
  not evidence of fairness, causality, or future real-world performance.

### AI & Machine Learning: Univariate Time-series Forecasting

- Regular univariate histories with explicit timestamp frequency, future
  horizon, missing-period rejection, and chronological ordering.
- Deterministic naive and seasonal-naive baselines plus additive Holt-Winters
  through statsmodels behind a shared forecasting port.
- No random split: evaluation uses a contiguous holdout or bounded
  rolling-origin windows in which training always precedes evaluation.
- MAE, RMSE, MAPE with explicit zero-denominator unavailability, and MASE where
  enough history exists. Independent validation recomputes published metrics,
  residuals, timestamp segments, and horizon progression.
- Versioned JSON, CLI, authenticated REST, MCP, bounded batch execution,
  canonical tables, forecast and residual charts, and report composition use
  the same application service.
- The headless engine is implemented. Desktop formulation and solution views,
  localized teaching pages, and worked examples remain the separate Part B
  workstream in `docs/FORECASTING_ROADMAP.md`.

### Modeling Assistant

- Local deterministic family recommendation for LP, MILP, Knapsack, NLP,
  linear regression, binary classification, Scheduling, and Robust
  Optimization.
- Conservative LP/MILP/Knapsack JSON drafting plus Regression and Binary
  Classification drafts from explicitly named, pipe-separated dataset rows.
  Every draft is validated against the same Optees importer used by the form;
  the assistant never invents observations from a prose-only description. NLP
  is currently recommendation-only; structured NLP drafting is deferred until
  its question-and-validation workflow exists.

### Graph Theory: Dijkstra Shortest Path

- Directed and undirected finite weighted graphs with source and destination.
- Deterministic Dijkstra implementation for finite non-negative edge weights.
- Path reconstruction, total weight, settled-node trace, JSON import, and a
  highlighted graph result view.
- A returned **Unreachable** status means no route exists from the selected
  source to destination; it is not a solver failure.

## Planned Families

The next sections are introduced in this order:

1. Scheduling: Unrelated Parallel Machines with required-job makespan and
   optional-job lexicographic value/makespan modes. Identical machines and
   repeated equal jobs are compact input specializations of this model.
2. Game Theory: finite two-player zero-sum matrix games, pure saddle-point
   analysis, and LP-based mixed strategies.

After these business-decision workflows, the planned sequence returns to
k-means clustering, TSP constructive/local search, Simulated Annealing, and
the broader family expansions in `docs/PROJECT_ROADMAP.md`.

## Cross-Family Methods

- Linear minimax/maximin and Chebyshev goal programming belong in LP/MILP.
- Nonlinear minimax belongs in NLP.
- Min-max regret, newsvendor, and revenue management belong to Robust
  Optimization workflows.
- Zero-sum payoff-matrix maximin/minimax belongs to Game Theory.
- Game-tree minimax and alpha-beta pruning belong to Adversarial Search / AI,
  not to the shortest-path Graph Theory workflow.

Heuristics are never presented as proof-producing exact methods. Their results
must report the random seed where applicable, run budget, elapsed time,
feasibility status, and the best-so-far objective trace.
