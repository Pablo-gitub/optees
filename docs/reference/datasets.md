# Datasets And Formats

Optees keeps solvers independent from external file formats. Dataset readers
live at the infrastructure boundary under `src/optees/utility/data_adapters/`;
they convert source files into the canonical dictionaries or domain models used
by the application.

Every in-repository dataset must have a source, a format description, an
expected outcome, and a test that consumes it. A small deterministic reference
case is useful for regression, but it is not labelled as a scientific benchmark
unless its origin and expected result are externally traceable.

## LP: LPnetlib

- **Source:** [SuiteSparse LPnetlib](https://sparse.tamu.edu/LPnetlib).
- **Files:** MATLAB `.mat` instances with the objective, matrix, row bounds,
  and variable bounds.
- **Included smoke instances:** `lp_afiro.mat` and `lp_25fv47.mat`.
- **Reader:** `load_lpnetlib_mat(path)`.
- **Tests:** `tests/utility/test_io_lpnetlib.py` and LP use-case tests.

## MILP: MIPLIB 2017

- **Source:** [MIPLIB 2017](https://miplib.zib.de/).
- **Files:** MPS/MPS.GZ instances plus `miplib2017-v31.solu`, the published
  status/objective table.
- **Included corpus:** `tests/data/miplib2017/`.
- **Tests:** `tests/utility/test_miplib_milp_e2e.py` discovers at most six small
  instances, imposes an on-disk-size filter, a short solver limit, and a hard
  per-instance timeout. It is optional when PuLP is unavailable.

The full MIPLIB directory is intentionally not a promise that every instance
is solvable by Optees' current adapter. It is a compatibility and parser
regression corpus; large instances are outside the standard exact-solver budget.

## 0/1 Knapsack: Burkardt KNAPSACK_01

- **Source:** [Burkardt KNAPSACK_01 dataset](https://people.sc.fsu.edu/~jburkardt/datasets/knapsack_01/knapsack_01.html).
- **Files per instance:**
  - `<instance>_c.txt`: integer capacity;
  - `<instance>_w.txt`: integer item weights;
  - `<instance>_p.txt`: item profits/values;
  - `<instance>_s.txt`: optional optimal 0/1 selection.
- **Included instances:** `p01`, `p02`, and `p08`.
- **Reader:** `load_knapsack_burkardt(dir_path, instance)`.
- **Tests:** `tests/utility/test_io_knapsack.py`,
  `tests/utility/test_io_knapsack_param.py`, and
  `tests/application/usecases/test_solve_knapsack_burkardt.py`.

`p01` and `p02` are standard exact regression cases. `p08` intentionally
exceeds the configured DP budget in the use-case test, proving that the UI can
report a bounded computational limit rather than claim an unproven optimum.

## Multi-Dimensional 0/1 Knapsack: OR-Library mknap1

- **Source:** [OR-Library multi-dimensional knapsack collection](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html), maintained by J. E. Beasley.
- **Original provenance:** the seven `mknap1` problems are the R&D-project
  selection instances reported by C. C. Petersen (1967). The source page also
  specifies the mathematical formulation and on-disk format.
- **Included source file:** `tests/data/knapsack/orlib/mknap1.txt`, with only
  trailing whitespace normalized from the source collection.
- **SHA-256:**
  `1e469c3ce6131f47bef6bd0af19e48d0f25bbe71c4eec76aa8cab43a24e01278`.
- **Reader:** `load_orlib_mknap(path, instance_index)`, where the index is
  1-based. It converts OR-Library's constraint-major coefficients into
  Optees' item-major `usage_matrix`.
- **Tests:** `tests/utility/test_orlib_mknap_adapter.py` validates parsing and
  orientation; `tests/application/usecases/test_solve_multi_dimensional_knapsack_orlib.py`
  verifies the published optima for instances 1--3.

The file holds instances with 6, 10, 15, 20, 28, 39, and 50 items. The current
exact branch-and-bound adapter has a conservative 32-item guard, and the
standard suite uses the first three to keep CI deterministic. The remaining
instances are retained as parser data and future performance-regression inputs,
not as a claim that the current exact adapter should solve them routinely.

## Bounded And Unbounded Knapsack Reference Cases

There is no small, redistributable external corpus currently included for these
two variants. Pisinger's academic code collection is an authoritative source
for the variants and test generators, but it does not provide a ready-made
small benchmark set suitable for vendoring here.

- **Source reference:** [David Pisinger's optimization codes](https://hjemmesider.diku.dk/~pisinger/codes.html), including the bounded `bouknap`
  algorithm and generators for related knapsack experiments.
- **Included cases:** `tests/data/knapsack/reference_cases.json`.
- **Purpose:** hand-checked, deterministic regression cases that assert the
  exact objective, quantity vector, and feasibility for the Bounded and
  Unbounded DP adapters.
- **Tests:** `tests/application/usecases/test_solve_knapsack_reference_cases.py`.

These cases are intentionally called **reference cases**, not external
benchmarks. When a suitable redistributable corpus with published optima is
identified, it should be added beside this file with its source, checksum, and
dedicated adapter if necessary.

## Continuous Convex QP Analytic Reference Cases

- **Included file:** `tests/data/qp/reference_cases.json`.
- **Cases:** unconstrained interior optimum, boundary optimum with active linear
  inequality, concave maximization with box bounds, combined equality and
  inequality constraints, contradictory infeasible constraints, and unbounded
  descent directions.
- **Contract:** canonical continuous quadratic minimization $\frac{1}{2} x^T Q x + c^T x + \alpha$
  with positive semidefinite $Q$.
- **Tests:** `tests/data/qp/test_qp_reference_cases.py`, plus domain, codec,
  adapter, use-case, validator, service, transport, and bilingual desktop UI tests.

These deterministic cases are verified against exact analytical optima and serve
as frozen handoff fixtures (`OPT-DS-QP-H`) for downstream consumers such as the
Decision Simulator.

## Continuous Convex QP: Maros–Mészáros Benchmark Collection

- **Source:** István Maros and Csaba Mészáros, *A repository of convex quadratic programming problems*,
  Optimization Methods and Software 11–12 (1999), pp. 671–681.
  Authoritative distribution: `http://www.doc.ic.ac.uk/~im/`.
- **Archives and Checksums:**
  - `00README.QP`: SHA-256 `cde81a616bbcb6379190ce845295be034c6676ca247e4484d5d8b7ead0daf4ce`
  - `QPDATA1.ZIP`: SHA-256 `1a851ba04d002c1e623367dd78a4c7d71730fc58f1296e7f83afa41e412b2323`
  - `QPDATA2.ZIP`: SHA-256 `8e96a76e3fcdac1999626926f3fa629fa7476b01a51b8d6cd312cc539e79994f`
  - `QPDATA3.ZIP`: SHA-256 `bc60bb823783ba10301ad48e4e8cca4d4af2a743ea739551ecb1c0ce40e21ed5`
- **Acquisition:** isolated script `scripts/fetch_maros_meszaros_benchmark.py` downloads
  and verifies files into `~/.cache/optees/benchmarks/maros_meszaros/` outside Git.
  Normal test runs and module imports make zero network calls.
- **Reader:** `load_qps_file(path)` in `optees.utility.data_adapters.qps_adapter`. Translates
  fixed/free QPS into `ContinuousConvexQPProblem` (v1 schema) preserving bounds,
  ranges, objective offsets ($c_0 = -\text{RHS}[\text{obj\_row}]$), and symmetric PSD Hessians.
- **Evaluated subset:** 14 representative convex instances (`HS21`, `QPTEST`, `TAME`,
  `ZECEVIC2`, `HS35`, `HS76`, `HS51`, `HS52`, `GENHS28`, `LOTSCHD`, `HS118`, `QAFIRO`,
  `CVXQP2_S`, `CVXQP3_S`) with $n \le 100$ and $m \le 75$.
- **Verification protocol:** solves through `create_local_optimization_service().solve("qp.continuous", payload)`.
  Asserts `optimal` status, finite solution, objective match within `rel=1e-4, abs=1e-4` against
  published BPMPD literature values, and passing independent validation report
  (`QPIndependentSolutionValidator`).
- **Tests:** unit adapter coverage in `tests/utility/test_qps_adapter.py` (fast gate);
  scientific benchmark execution in `tests/utility/test_qp_maros_meszaros_benchmark.py`
  (marked `@pytest.mark.benchmark`).

## Continuous NLP Analytic Reference Cases

- **Included file:** `tests/data/nlp/reference_cases.json`.
- **Cases:** Rosenbrock with Nelder-Mead, Himmelblau in the basin selected by
  the documented starting point, a bounded convex quadratic, and a concave
  maximization quadratic.
- **Tests:** `tests/utility/test_nlp_reference_cases.py`.

These are deterministic **analytic reference cases**, not a downloaded
scientific benchmark corpus. Each records an initial point, selected method,
iteration budget, expected local candidate, and numerical tolerance. This is
important for multi-modal functions: the test verifies the documented basin,
not an unsupported claim of global optimality.

External NLP benchmark integration is planned in the project roadmap's
benchmark-hardening phase. A corpus will be added only after its redistribution
terms, expected local/global contract, source metadata, and CI budget have been
reviewed. Until then, these cases are the required regression baseline for the
local SciPy methods implemented by Optees.

## Educational Regression Analytic Reference Cases

- **Included file:** `tests/data/regression/reference_cases.json`.
- **Cases:** exact affine relations with one feature and with two independent
  features.
- **Tests:** `tests/utility/test_regression_reference_cases.py`.

These deterministic cases are not a predictive benchmark. They verify the
local OLS implementation against known intercepts, feature coefficients, and
held-out metrics under a fixed train/test split. Future dataset additions for
clustering must be redistributable, documented, and kept separate from
performance claims.

## Educational Binary Classification Reference Cases

- **Included file:** `tests/data/classification/reference_cases.json`.
- **Case:** a small, two-feature linearly separable dataset with two labels and
  documented expected training and held-out accuracy under a fixed stratified
  split.
- **Tests:** `tests/utility/test_classification_reference_cases.py` plus
  domain, JSON, use-case, adapter, presentation, and bilingual assistant tests.

This is a deterministic implementation regression, not a scientific predictive
benchmark. It checks the local logistic-regression contract, class-preserving
split, metrics, and 2D visualization inputs. A future external classification
dataset must be redistributable, documented with its intended evaluation
protocol, and kept separate from fairness or real-world deployment claims.

## Univariate Forecasting Reference Cases

- **Included file:** `tests/data/forecasting/reference_cases.json`.
- **Cases:** constant demand, a linear trend measured with a naive baseline, an
  exact seasonal cycle, minimum valid history, a zero holdout actual, and a
  deterministic noisy series.
- **Tests:** `tests/utility/test_forecasting_reference_cases.py`, plus domain,
  codec, adapter, use-case, validator, service, transport, artifact, and
  assistant tests.

These tiny cases run in normal CI. They verify exact future values, metric
semantics, edge-case status, and independent validation. They are reference
fixtures, not evidence of general forecasting accuracy.

## Univariate Forecasting: Statsmodels Sunspots

- **Upstream distribution:** statsmodels `datasets.sunspots`, sourced from the
  National Geophysical Data Center.
- **Usage terms:** the statsmodels dataset module declares the data public
  domain.
- **Data:** 309 annual observations from 1700 through 2008.
- **File used:** the `sunspots.csv` installed with the selected statsmodels
  runtime; Optees does not vendor a second copy.
- **SHA-256:** `f67889b1d9002cd5227f0e0ef54e35b419cdd85a31279adef6f73fb41e5c0a9b`.
- **Protocol:** seasonal-naive forecasting with an 11-year season, a final
  22-year chronological holdout, and an 11-year future horizon. No row is
  shuffled and no future observation enters a training prefix.
- **Expected holdout metrics:** MAE `38.47272727272727`, RMSE
  `45.02725437291992`, MAPE `98.8100019183094`, and MASE
  `1.7262160400683966`.
- **Test:** `tests/utility/test_forecasting_sunspots_benchmark.py`.
- **CI budget:** no network, 309 input rows, and less than five seconds on the
  supported CI Python runtime. It is marked `benchmark` and therefore runs in
  the scheduled/manual scientific gate rather than the fast push gate.

This benchmark verifies a public temporal protocol and reproducible arithmetic;
it does not claim that seasonal naive is an accurate sunspot model or that one
dataset establishes production forecasting quality.

## Graph Theory: Dijkstra Reference Cases

The first shortest-path workflow uses small hand-built directed, undirected,
and unreachable graphs directly in the test suite, plus
`examples/shortest_path_delivery.json` as a reusable UI example. These are
deterministic regression cases, not a downloaded graph benchmark corpus.

An external graph dataset will be evaluated in the benchmark-hardening phase.
It must provide a redistributable source, known reference paths or distances,
and a bounded CI subset before it is added here.

## Single-Container 3D Packing: OR-Library thpack1

- **Included file:** `tests/data/packing/orlib/thpack1.txt`.
- **Source:** J. E. Beasley's OR-Library, contributed by M. S. W. Ratcliff.
- **Reference:** E. E. Bischoff and M. S. W. Ratcliff, *Issues in the
  Development of Approaches to Container Loading*, OMEGA 23(4), 1995.
- **Contract:** single rectangular container, rectangular box types, allowed
  vertical orientations, and volume-utilization maximization.
- **Tests:** source-format parsing plus an exact two-copy smoke subset derived
  from problem 1, type 1.

The complete first instance contains 112 physical boxes. Normal CI does not
run the quadratic pairwise MILP on that full instance. The derived subset has
an analytic expected objective equal to twice the source box volume; this is
an implementation regression and is not represented as a published optimum.
The source URL, checksum, and this distinction are recorded in
`tests/data/packing/README.md`.

## Test Data Layout

```text
tests/data/
  lp/lpnetlib_mat/
    lp_afiro.mat
    lp_25fv47.mat
  miplib2017/
    miplib2017-v31.solu
    instances/
  knapsack/
    p01/, p02/, p08/                # Burkardt 0/1
    orlib/mknap1.txt                # OR-Library multi-dimensional 0/1
    reference_cases.json            # Bounded/Unbounded regression cases
  nlp/
    reference_cases.json            # Analytic continuous NLP regressions
  qp/
    reference_cases.json            # Analytic convex QP regressions and edge cases
  regression/
    reference_cases.json            # Analytic OLS regression cases
  classification/
    reference_cases.json            # Logistic-regression reference case
  forecasting/
    reference_cases.json            # Deterministic temporal reference cases
  packing/
    orlib/thpack1.txt                # Bischoff/Ratcliff single-container data
```

## Adding A Dataset

1. Verify the original source, usage terms, file checksum, and published
   outcome before copying files into the repository.
2. Add a dedicated reader when the format is not already supported; keep it out
   of the solver itself.
3. Add a parsing test and an end-to-end test that checks feasibility and a
   published optimum or an explicitly documented reference outcome.
4. Keep normal CI fast. Put expensive cases behind a marker or an explicit
   opt-in command, and document the expected machine/runtime budget.
