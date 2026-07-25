# Testing Strategy

## Focused artifact gate

```bash
PYTHONPATH=src python -m pytest -q \
  tests/application/services/test_artifact_generation_service.py \
  tests/data/adapters/artifacts/test_canonical_table_renderer.py \
  tests/data/adapters/artifacts/test_categorical_chart_renderer.py \
  tests/data/adapters/artifacts/test_analytic_chart_renderer.py \
  tests/data/adapters/artifacts/test_packing_scene_renderer.py \
  tests/data/adapters/artifacts/test_local_artifact_store.py \
  tests/application/contracts/test_report_contracts.py \
  tests/application/services/test_report_composition_service.py \
  tests/interfaces/http/test_local_artifact_api.py \
  tests/interfaces/http/test_local_report_api.py \
  tests/interfaces/http/test_local_api.py \
  tests/interfaces/mcp/test_local_mcp_server.py
```

This gate covers asynchronous lifecycle, bounded storage, authorization, HTTP
contracts, and verified downloads. It requires the local-service HTTP extras
(`fastapi` and `httpx`); without them, HTTP modules are skipped while
application and storage tests still run.

The canonical renderer test is parameterized over every public capability and
checks stable table shapes, deterministic JSON, correctly escaped CSV, bounded
Markdown, MILP validation semantics, and machine-readable truncation metadata.
MCP coverage verifies metadata-first discovery, render polling, explicit
resource transfer, and rejection of unsafe opaque IDs. Report coverage verifies
strict safe-Markdown validation, deterministic composition, source provenance,
artifact pinning, explicit unsupported blocks, authenticated download, and
metadata-only MCP retrieval.

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
- `tests/application/validation/test_regression_solution_validator.py`:
  independent parameter, prediction, residual, split, and metric consistency
  checks, including tampered-result failures.
- `tests/composition/test_backend_health.py`: concrete optional-backend import
  probes and a trivial SciPy/HiGHS execution probe.
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
- `tests/application/contracts/test_batch_contracts.py`,
  `tests/application/services/test_local_job_service.py`, and transport tests:
  bounded batch contracts, atomic all-or-nothing submission, individual
  envelope retention, aggregate summaries, and exact-validation safeguards
  across REST, MCP, and the Ollama harness.
- `tests/data/adapters/artifacts/test_local_artifact_store.py`: private
  session-directory lifecycle, atomic bounded retention, SHA-256 verification,
  expiration and pinning, traversal rejection, symlink/byte tamper detection,
  deterministic eviction, and shutdown cleanup.
- `tests/data/adapters/artifacts/test_packing_scene_renderer.py`: Packing
  capacity accounting, five bounded headless camera modes, deterministic
  OBJ+MTL archives, safe geometry identifiers, and manifest semantics.
- `tests/data/adapters/reports/test_report_adapters.py`: bounded XLSX and
  OBJ+MTL report conversion, archive/geometry rejection, PDF backend
  diagnostics, fixed-command execution, and verified PDF output.
- Forecasting domain, codec, adapter, use-case, service, transport, artifact,
  and validator tests cover strict chronology, no-leakage training prefixes,
  deterministic naive baselines, statsmodels Holt-Winters, holdout and
  rolling-origin evaluation, independent metric recomputation, and versioned
  public behavior.
- `tests/utility/test_forecasting_reference_cases.py`: constant, trend,
  seasonal, short-history, zero-actual, and noisy deterministic reference
  cases in the normal fast gate.
- `tests/utility/test_forecasting_sunspots_benchmark.py`: checksummed
  public-domain annual Sunspots data under a fixed seasonal-naive temporal
  protocol in the measured `benchmark` gate.

Ruff is available through the `dev` extra and applies to new or modified
Python code. Whole-repository linting is not yet a CI gate because legacy
modules retain known lint debt. Use `python -m ruff check src tests packaging`
to audit that backlog separately.

## Commands
```bash
# install reproducible development test dependencies
python -m pip install -e ".[plot,local-service,test,dev]"

# lint the Python files changed by the current work unit
python -m ruff check path/to/changed.py path/to/changed_test.py

# fast local feedback: no full-window GUI, measured benchmarks, or sockets
PYTHONPATH=src python -m pytest -q -m "not gui and not benchmark and not tcp"

# presentation behavior (kept serial until isolation is measured)
PYTHONPATH=src python -m pytest -q -m gui

# scientific/external benchmark integrations
PYTHONPATH=src python -m pytest -q -m benchmark

# forecasting engine, deterministic references, and public benchmark
PYTHONPATH=src python -m pytest -q \
  tests/domain/test_forecasting_model.py \
  tests/domain/test_forecasting_solution.py \
  tests/application/codecs/test_forecasting_codecs.py \
  tests/adapters/test_forecasting_baseline_adapter.py \
  tests/adapters/test_holt_winters_forecasting_adapter.py \
  tests/application/usecases/test_forecast_time_series_usecase.py \
  tests/application/validation/test_forecasting_solution_validator.py \
  tests/utility/test_forecasting_reference_cases.py \
  tests/utility/test_forecasting_sunspots_benchmark.py

# real loopback transport and subprocess lifecycle
PYTHONPATH=src python -m pytest -q -m tcp

# local solver platform integration gate (contracts, codecs, services, CLI,
# REST, MCP, Ollama harness, server settings, and packaged entry points)
PYTHONPATH=src python -m pytest -q \
  tests/application/contracts \
  tests/application/codecs \
  tests/application/validation \
  tests/application/services \
  tests/cli \
  tests/interfaces \
  tests/presentation/test_local_server_settings.py \
  tests/test_local_server_entrypoint.py \
  tests/test_local_server_packaging_contract.py \
  tests/adapters/test_rule_based_assistant_adapter.py

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
`benchmark`, `gui`, and `tcp` groups. These groups are assigned centrally from
stable test ownership boundaries in `tests/conftest.py`; unknown markers fail
collection. The next measured run should compare the non-GUI subset serially,
with two workers, and with four workers using `--dist loadfile`. Full-window
tests remain serial until isolation is demonstrated. Over time they should use
narrower view/controller fixtures. Dependency-based selection remains
secondary because i18n files, datasets, assets, and dynamic composition are
material non-code inputs.

Candidate commands for the next measured comparison are intentionally not
configured as defaults:

```bash
PYTHONPATH=src python -m pytest -q -m "not gui and not benchmark" --durations=20
PYTHONPATH=src python -m pytest -q -m "not gui and not benchmark" -n 2 --dist loadfile --durations=20
PYTHONPATH=src python -m pytest -q -m "not gui and not benchmark" -n 4 --dist loadfile --durations=20
```

## Continuous Integration Gates

`.github/workflows/ci.yml` runs independently from release publication:

- the fast non-GUI, non-benchmark, non-TCP group runs on every pull request and
  push to `main`;
- GUI tests run under Xvfb on every pull request and push to `main`;
- real loopback and subprocess tests run in their own job;
- scientific benchmark tests run on the weekly schedule and through manual
  workflow dispatch.

The tagged release workflow has a separate authoritative gate. It checks out
the exact tagged commit, installs all test extras, runs the complete suite
under Xvfb, and only then permits the platform build matrix to start.
Each platform build must also complete a small continuous LP through its
packaged MCP companion and verify both the optimal result and independent
validation report. The packaged REST companion additionally executes additive
Holt-Winters Forecasting and renders its canonical Markdown table and PNG
forecast chart, proving that statsmodels and the headless renderer are present.
Capability listing alone is not considered a sufficient backend smoke test.

Headless artifact tests render LP, Forecasting, and Packing reference scenes
through Matplotlib Agg. They verify SVG structure and semantic labels, and
inspect PNG signatures, requested dimensions, and nonblank pixel variance.
Forecasting tests verify origin boundaries, timeline sampling, and residual
semantics. Packing tests also validate every named camera and the deterministic
OBJ/MTL/manifest archive. These checks intentionally avoid exact pixel
snapshots, which vary across rendering platforms without providing stronger
mathematical assurance.

Report tests use controlled fake Pandoc and Typst executables to verify command
boundaries and lifecycle semantics without making the local suite depend on
optional document tools. A release candidate that advertises PDF support must
also run the installed native smoke in `docs/RELEASING.md`; a mocked `%PDF-`
response does not validate real fonts, pagination, tables, links, captions, or
the bundled Typst template on a target platform.

## Reproducibility

* Pin Python and core dependencies in the project environment.
* Keep adapters deterministic; avoid hidden randomness.
* Store small datasets under `tests/data/...`; larger ones are documented with
  links, checksums, and an explicit runtime budget.
