# Current Capability Inventory

This inventory records the contracts that exist in Optees 0.8.0 before the
local solver service introduces public execution envelopes. It is descriptive,
not aspirational: backend availability, status semantics, diagnostics, and
tests are taken from the current code.

## Cross-Cutting Findings

- Every listed workflow already has an in-memory `*_from_dict` entry point.
  No service adapter needs to create temporary JSON files.
- The Knapsack codec first produces `KnapsackJsonProblem`; variant-specific
  application mapping is not yet centralized behind one execution facade.
- Domain results are frozen dataclasses containing enums, tuples, nested
  dataclasses, and sometimes raw `extras`. None is a versioned public result
  contract yet.
- Raw `extras` cannot be returned blindly. LP may contain SciPy/NumPy values
  and nested HiGHS blocks; every result codec must explicitly normalize and
  reject non-finite numbers.
- Job lifecycle is absent. Existing statuses describe mathematical or training
  outcomes and must not be reused for queued/running/cancelled job states.
- Only single-container packing exposes cooperative cancellation. MILP and
  packing accept elapsed-time limits; NLP accepts an iteration limit, not a
  wall-clock limit.
- Optional-backend availability is handled inconsistently. Adapters generally
  return `NotSolved`/`Failed`; there is no shared capability availability
  descriptor.

## Capability Matrix

| Capability ID | Input model / payload codec | Use case | Port and adapter | Domain result | Runtime controls |
| --- | --- | --- | --- | --- | --- |
| `lp.continuous` | `LPModel`; `lp_model_from_dict` | `SolveLPUseCase` | `LPSolverPort`; `LPSolverAdapter` | `LPSolution` | method only; no time limit or cancellation |
| `milp.linear` | `MILPModel`; `milp_model_from_dict` | `SolveMILPUseCase` | `MILPSolverPort`; `MILPSolverAdapter` | `MILPSolution` | time limit and relative MIP gap; no cancellation |
| `knapsack.zero_one` | `Knapsack01Model`; shared `knapsack_problem_from_dict` DTO | `SolveKnapsackUseCase` | `KnapsackSolverPort`; `KnapsackSolverAdapter` | `KnapsackSolution` | internal DP-size guard; no time limit or cancellation |
| `knapsack.bounded` | `BoundedKnapsackModel`; shared Knapsack DTO | `SolveBoundedKnapsackUseCase` | `BoundedKnapsackSolverPort`; `BoundedKnapsackSolverAdapter` | `BoundedKnapsackSolution` | internal DP-size guard; no time limit or cancellation |
| `knapsack.unbounded` | `UnboundedKnapsackModel`; shared Knapsack DTO | `SolveUnboundedKnapsackUseCase` | `UnboundedKnapsackSolverPort`; `UnboundedKnapsackSolverAdapter` | `UnboundedKnapsackSolution` | internal DP-size guard; no time limit or cancellation |
| `knapsack.fractional` | `FractionalKnapsackModel`; shared Knapsack DTO | `SolveFractionalKnapsackUseCase` | `FractionalKnapsackSolverPort`; `FractionalKnapsackSolverAdapter` | `FractionalKnapsackSolution` | item-count guard; no time limit or cancellation |
| `knapsack.multi_dimensional` | `MultiDimensionalKnapsackModel`; shared Knapsack DTO | `SolveMultiDimensionalKnapsackUseCase` | `MultiDimensionalKnapsackSolverPort`; `MultiDimensionalKnapsackSolverAdapter` | `MultiDimensionalKnapsackSolution` or `MultiDimensionalQuantityKnapsackSolution` | search-size guard; no time limit or cancellation |
| `nlp.continuous_local` | `NLPModel`; `nlp_model_from_dict` | `SolveNLPUseCase` | `NLPSolverPort`; `ScipyNLPSolverAdapter` | `NLPSolution` | method, tolerance, maximum iterations; no time limit or cancellation |
| `graph.shortest_path.dijkstra` | `ShortestPathModel`; `shortest_path_model_from_dict` | `SolveShortestPathUseCase` | `ShortestPathSolverPort`; `DijkstraSolverAdapter` | `ShortestPathSolution` | none; synchronous and no cancellation |
| `ml.regression.linear` | `RegressionModel`; `regression_model_from_dict` | `TrainRegressionUseCase` | `RegressionSolverPort`; `NumpyRegressionAdapter` | `RegressionSolution` | model options only; no time limit or cancellation |
| `ml.classification.binary_logistic` | `BinaryClassificationModel`; `classification_model_from_dict` | `TrainClassificationUseCase` | `ClassificationSolverPort`; `NumpyClassificationAdapter` | `ClassificationSolution` | training options only; no wall-clock limit or cancellation |
| `packing.single_container_3d` | `SingleContainerPackingModel`; `packing_model_from_dict` | `SolveSingleContainerPackingUseCase` | `PackingSolverPort`; `OrtoolsSingleContainerPackingAdapter` | `PackingSolveResult` containing requested and optional recovery `PackingSolution` | time limit, MIP gap, cooperative cancellation |

Paths in the table are under `src/optees`; test paths below are under `tests`.

## Capability Details

### `lp.continuous`

- **Input:** `domain/models/lp/lp_model.py`; schema v1 codec in
  `utility/lp_json_io.py` supports variables, bounds, objective offset, and
  linear constraints.
- **Backend:** SciPy `linprog` with HiGHS through `utility/lp_utils.py`.
- **Statuses:** `Optimal`, `Infeasible`, `Unbounded`, `NotSolved`.
- **Diagnostics:** method, iteration counts, message, status code, success, and
  optional HiGHS equality, inequality, lower-bound, and upper-bound blocks.
- **Domain-specific output:** objective, variable values, sensitivity data, and
  optimal-face variable ranges in `extras["alt_opt"]` when computed.
- **Serialization gap:** `LPSolution`, `SolverDiagnostics`, enum values, HiGHS
  blocks, and optimal ranges need an explicit finite JSON codec.
- **Regression base:** `utility/test_lp_json_io.py`,
  `application/usecases/test_solve_lp_usecase.py`,
  `adapters/test_lp_solver_adapter.py`, LP presentation tests, and NETLIB tests.

### `milp.linear`

- **Input:** `domain/models/milp/milp_model.py`; schema v1 codec in
  `utility/milp_json_io.py` includes variable integrality, time limit, and MIP
  gap.
- **Backends:** OR-Tools CP-SAT for compatible integer models and CBC for mixed
  or non-integer data.
- **Statuses:** `Optimal`, `Feasible`, `Infeasible`, `Unbounded`, `NotSolved`.
- **Diagnostics:** backend, status, message, best bound, relative gap, wall
  time, nodes, branches, and conflicts where supported.
- **Serialization gap:** normalize domain dataclasses and omit unavailable
  backend diagnostics rather than synthesizing them.
- **Regression base:** `utility/test_milp_json_io.py`,
  `application/usecases/test_solve_milp_usecase.py`,
  `utility/test_miplib_milp_e2e.py`, and MILP presentation tests.

### Knapsack family

- **Input:** `utility/knapsack_json_io.py` parses schema v1 into a shared
  `KnapsackJsonProblem`, including variant, domain, resources, quantities, and
  item data. The execution facade still needs an application-owned mapper from
  that DTO to each domain model.
- **Backends:** local deterministic dynamic programming, greedy fractional
  selection, and bounded search/branch-and-bound adapters depending on the
  variant.
- **Statuses:** `Optimal`, `Feasible`, `Infeasible`, `Unbounded`, `NotSolved`.
- **Diagnostics:** method, message, item count, capacity, explored/estimated DP
  cells, configured limit, and complexity label where applicable.
- **Variant outputs:** selected indices for 0/1; integer quantities for bounded
  and unbounded; fractions for fractional; selections or quantities plus
  per-resource usage for multi-dimensional.
- **Serialization gap:** the result schema must preserve each variant's
  quantities and resource semantics instead of flattening all variants into
  selected indices.
- **Regression base:** variant domain, adapter, use-case, JSON, Burkardt, and
  OR-Library multi-knapsack tests.

### `nlp.continuous_local`

- **Input:** `domain/models/nlp/nlp_model.py`; schema v1 codec in
  `utility/nlp_json_io.py` validates continuous variables, restricted
  expressions, initial values, bounds, method, tolerance, and iterations.
- **Backend:** SciPy `minimize` through `ScipyNLPSolverAdapter`.
- **Statuses:** `Converged`, `IterationLimit`, `Failed`, `NotSolved`.
- **Diagnostics/output:** objective, local candidate values, iterations,
  evaluations, termination message, and convergence history.
- **Contract warning:** convergence is a local numerical outcome, never an
  `optimal` mathematical status or proof of global optimality.
- **Regression base:** NLP model, expression, JSON, adapter, use-case,
  reference-case, and presentation tests.

### `graph.shortest_path.dijkstra`

- **Input:** `domain/models/graph/shortest_path_model.py`; schema v1 codec in
  `utility/graph_json_io.py` validates vertices, directed/undirected edges,
  non-negative finite weights, source, and target.
- **Backend:** local deterministic `DijkstraSolverAdapter`; no optional solver
  dependency.
- **Statuses:** `PathFound`, `Unreachable`, `NotSolved`.
- **Output:** distance, path, settled-node order, settled distances, and message.
- **Regression base:** graph model, JSON, utility, adapter/use-case, assistant,
  and presentation tests.

### `ml.regression.linear`

- **Input:** `domain/models/regression/regression_model.py`; schema v1 codec in
  `utility/regression_json_io.py` validates feature names, rows, target,
  train/test split, and OLS/Ridge options.
- **Backend:** `NumpyRegressionAdapter` using NumPy.
- **Statuses:** `Trained`, `Failed`, `NotTrained`.
- **Output:** intercept, named coefficients, train/test MAE, MSE, RMSE and R2,
  plus row-level predictions and residuals.
- **Contract warning:** training success is not mathematical optimality,
  causality, production readiness, or out-of-sample guarantee.
- **Regression base:** regression model, JSON, utility, adapter/use-case,
  scientific reference cases, assistant prompts, and presentation tests.

### `ml.classification.binary_logistic`

- **Input:** `domain/models/classification/binary_classification_model.py`;
  schema v1 codec in `utility/classification_json_io.py` validates binary
  labels, feature rows, split, threshold, regularization, learning rate, and
  iteration options.
- **Backend:** `NumpyClassificationAdapter` using NumPy.
- **Statuses:** `Trained`, `Failed`, `NotTrained`.
- **Output:** labels, intercept, coefficients, train/test metrics, confusion
  matrices, probabilities, and row-level predictions.
- **Contract warning:** status and metrics describe an educational local model,
  not fairness, calibration, causal validity, or deployment suitability.
- **Regression base:** classification model, JSON, utility, adapter/use-case,
  reference cases, assistant prompts, error feedback, and presentation tests.

### `packing.single_container_3d`

- **Input:** `domain/models/packing/single_container_packing_model.py`; schema
  v1 codec in `utility/packing_json_io.py` validates container dimensions,
  scalar capacities, item quantities, orientations, selection and gravity
  policies, time limit, and MIP gap.
- **Backend:** OR-Tools linear solver through
  `OrtoolsSingleContainerPackingAdapter`; cancellation uses the backend
  interruption API when available.
- **Statuses:** requested and recovery solutions use MILP statuses `Optimal`,
  `Feasible`, `Infeasible`, `Unbounded`, and `NotSolved`.
- **Output:** requested result, optional maximum-feasible recovery result,
  placements, excluded instances, used volume, objective, bound, gap, and
  backend diagnostics.
- **Contract warning:** requested infeasibility and recovery feasibility must
  remain separate in every public envelope.
- **Regression base:** packing domain, JSON, complexity, adapter/use-case,
  OR-Library THPACK, rendering, and presentation-flow tests.

## Phase 1 Consequences

The LP pilot must introduce, without altering desktop behavior:

1. shared public enums for job status, mathematical status, and termination;
2. a versioned execution envelope and structured error value;
3. a serializer protocol owned by the application boundary;
4. an LP result codec that explicitly serializes optimal ranges and finite
   diagnostics;
5. tests proving that non-finite values and unsupported raw diagnostic objects
   never leak into JSON.

Capability registration, execution, CLI, HTTP, jobs, and semantic guidance are
deliberately outside Phase 1.
