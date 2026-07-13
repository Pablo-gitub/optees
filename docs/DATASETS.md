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
classification and clustering must be redistributable, documented, and kept
separate from performance claims.

## Graph Theory: Dijkstra Reference Cases

The first shortest-path workflow uses small hand-built directed, undirected,
and unreachable graphs directly in the test suite, plus
`examples/shortest_path_delivery.json` as a reusable UI example. These are
deterministic regression cases, not a downloaded graph benchmark corpus.

An external graph dataset will be evaluated in the benchmark-hardening phase.
It must provide a redistributable source, known reference paths or distances,
and a bounded CI subset before it is added here.

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
  regression/
    reference_cases.json            # Analytic OLS regression cases
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
