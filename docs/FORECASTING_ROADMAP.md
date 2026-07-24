# Time-series Forecasting Roadmap

This document defines the sequential delivery plan for the first Optees
Forecasting capability. `docs/PROJECT_ROADMAP.md` remains authoritative for
cross-family priority; this roadmap owns Forecasting scope, gates, and handoff
requirements.

## Product Goal

Forecasting must help a user estimate future values from an ordered historical
series while making temporal assumptions, uncertainty, and evaluation evidence
visible. It is a separate AI & Machine Learning capability and must never reuse
the random-split Linear Regression contract as if rows were independent.

The first release is local, deterministic, univariate, and educational but
operationally useful. It accepts one timestamp column and one numeric target,
trains only on past observations, produces a finite future horizon, and exposes
the same validated result through desktop, CLI, REST, and MCP.

## Scope Boundaries

### Included in the first vertical slice

- one regularly ordered univariate time series;
- explicit timestamp, target, horizon, and frequency semantics;
- deterministic naive and seasonal-naive baselines;
- one maintained trend/seasonality forecasting adapter selected during Phase
  A0;
- chronological holdout and bounded rolling-origin evaluation;
- point forecasts, fitted values, residuals, evaluation metrics, and explicitly
  labelled uncertainty output when supported by the selected method;
- versioned JSON problem and result contracts;
- independent arithmetic and temporal validation;
- optional headless tables, charts, and report composition;
- capability discovery and execution through CLI, REST, MCP, and batch jobs;
- English and Italian desktop and educational content in Part B.

### Explicitly deferred

- multivariate or multiple-target forecasting;
- probabilistic model selection and automatic hyperparameter search;
- ARIMA/SARIMA, Prophet, neural networks, and arbitrary user code;
- irregular event streams without an explicit resampling policy;
- hierarchical, intermittent-demand, and grouped reconciliation;
- causal claims, scenario simulation, and direct optimization of downstream
  business decisions;
- automatic Forecasting-to-MILP orchestration. Agents may compose the two
  validated capabilities, but Optees will not silently invent that workflow.

## Frozen Terminology

- **Observation:** one timestamp and one finite target value.
- **Forecast origin:** the final observation available to a fitted model.
- **Horizon:** the number of future periods requested after the origin.
- **Season length:** the number of observations in one declared cycle.
- **Holdout:** the final contiguous historical segment reserved for evaluation.
- **Rolling origin:** repeated evaluation in which every training window ends
  before its corresponding validation window begins.
- **Prediction interval:** a method-specific or empirically calibrated range
  with documented coverage semantics. It is not a guarantee.

## Part A - Forecasting Engine And Public Service

Part A must be complete before desktop implementation or long-form educational
copy begins. It establishes the mathematical meaning that every presentation
surface must preserve.

### A0 - Freeze The Statistical Contract

- [x] Compare maintained local Python implementations for the first
  trend/seasonality method and document dependency, package-size, license, and
  native-packaging consequences.
- [x] Select the initial method set and assign stable method identifiers.
  `naive` and `seasonal_naive` are mandatory; the first trend/seasonality
  adapter must be explicitly chosen rather than inferred from UI wording.
- [x] Define supported frequency values, timestamp parsing, duplicate handling,
  sorting policy, minimum history, season-length requirements, and whether
  missing periods are rejected or filled only by an explicit policy.
- [x] Freeze evaluation metric definitions and zero-denominator behavior.
  Initial candidates are MAE, RMSE, MAPE with an explicit undefined state, and
  MASE when enough seasonal history exists.
- [x] Freeze uncertainty semantics. A field may be absent when a method cannot
  support a defensible interval; Optees must not fabricate a confidence band.
- [x] Record numerical tolerances, deterministic seed behavior, and expected
  failure/status vocabulary.

The frozen decisions are maintained in
`docs/FORECASTING_STATISTICAL_CONTRACT.md`.

**Exit criterion:** a reviewed contract note answers every ambiguity above and
the chosen dependency can be packaged on Windows, macOS, and Linux.

### A1 - Domain Model And Ports

- [x] Add immutable timestamped observations and a `ForecastingModel` containing
  target metadata, method, horizon, frequency, optional season length,
  evaluation strategy, and bounded method options.
- [x] Reject non-finite targets, duplicate or non-monotonic normalized
  timestamps, invalid horizons, insufficient history, unsupported frequency,
  and inconsistent seasonal settings.
- [x] Define result entities for fitted values, holdout predictions, future
  forecasts, residuals, metrics, interval bounds, model parameters,
  diagnostics, and mathematical status.
- [x] Define a Forecasting solver port independent from the selected numerical
  library and from Qt, HTTP, MCP, and filesystem code.
- [ ] Keep training, evaluation, and future forecasting as explicit operations
  in the use case even if one adapter performs them together.

### A2 - Baselines And Forecasting Adapter

- [x] Implement exact deterministic naive forecasting.
- [x] Implement exact deterministic seasonal-naive forecasting with a declared
  season length.
- [x] Implement the selected maintained trend/seasonality adapter behind the
  same port.
- [x] Preserve timestamp alignment and original scale in all returned rows.
- [x] Map numerical warnings and convergence failures to stable Optees
  diagnostics without leaking raw library exceptions into public contracts.
- [ ] Add cancellation and bounded runtime/options where the selected backend
  can perform iterative fitting.

### A3 - Temporal Evaluation And Independent Validation

- [ ] Implement chronological holdout without shuffling.
- [ ] Implement bounded rolling-origin evaluation with explicit origin count,
  step, horizon, and minimum training window.
- [ ] Recompute MAE, RMSE, and every other published metric independently from
  public predictions and observations.
- [ ] Validate that every fitted, holdout, and future timestamp belongs to the
  correct temporal segment and that no training row occurs after its evaluation
  target.
- [ ] Validate finite outputs, residual identities, interval ordering, horizon
  length, frequency progression, and method-specific invariants.
- [ ] Distinguish execution success, forecast availability, evaluation
  availability, and independent validation status.
- [ ] Tamper-test timestamps, predictions, residuals, metrics, intervals,
  parameters, and split accounting.

### A4 - Versioned JSON And Capability Registration

- [ ] Define problem schema version `1` and result schema version `1`.
- [ ] Implement strict codecs and importer validation with stable error codes.
- [ ] Include a complete example payload and result fixture in the capability
  descriptor rather than exposing only top-level field names.
- [ ] Register one public capability identifier under AI & Machine Learning,
  with supported methods and artifact inventory discoverable by agents.
- [ ] Expose validate, solve, job status, result retrieval, and bounded batch
  execution through the existing application services.
- [ ] Verify equivalent behavior through CLI, authenticated REST, and MCP.
- [ ] Add conservative rule-based assistant recognition in matched English and
  Italian tests; structured drafting remains limited to explicit timestamps and
  values and must never invent history from prose.

### A5 - Headless Result Artifacts And Reports

- [ ] Add a canonical forecast table containing timestamp, actual value where
  available, fitted/forecast value, residual, interval bounds, and segment.
- [ ] Add a headless actual-versus-fitted-versus-forecast chart with an explicit
  forecast-origin boundary and interval band when available.
- [ ] Add a residual-over-time diagnostic and avoid meaningless categorical
  charts for long series.
- [ ] Declare renderer limits and deterministic downsampling/truncation metadata
  for large histories.
- [ ] Register artifacts through the existing bounded storage, SHA-256,
  expiration, REST download, MCP resource, and Markdown/PDF report paths.
- [ ] Ensure renderers consume only the versioned problem/result pair and never
  refit the model.

### A6 - Reference Cases, Benchmarks, And Packaging

- [ ] Add analytic constant, linear-trend, seasonal-cycle, short-history,
  zero-valued, and noisy deterministic reference cases.
- [ ] Add tests proving that shuffled or leaked evaluation data is rejected.
- [ ] Select one redistributable public time-series benchmark only after source,
  license, expected protocol, checksum, and CI budget are documented in
  `docs/DATASETS.md`.
- [ ] Keep tiny references in normal CI and mark external or measured cases as
  `benchmark`.
- [ ] Add packaged capability discovery and solve smoke tests for Windows,
  macOS, and Linux.
- [ ] Verify that any new numerical dependency and artifact renderer are
  included in native installers and do not break headless startup.

## Part A Completion Gate

Part B may begin only when all of the following are true:

1. method assumptions and versioned schemas are frozen;
2. domain, adapter, use case, codec, and validator tests pass;
3. one complete forecast runs through CLI, REST, and MCP;
4. optional tables and charts are generated without Qt;
5. packaged smoke coverage includes the new capability;
6. reference fixtures and expected statuses are committed;
7. `docs/ARCHITECTURE.md`, `docs/TESTING.md`, and the algorithm catalogue
   describe the shipped engine honestly.

## Part B - Desktop, Teaching, And Examples

Part B is intentionally a separate workstream. It may be delegated to Claude
after the Part A handoff package is complete. The implementation must reuse the
frozen application services and may not redefine statistical behavior in view
code or documentation.

### B0 - Handoff Package

- [ ] Provide the frozen problem/result schemas and full valid JSON examples.
- [ ] Provide golden result fixtures for naive, seasonal, trend/seasonality,
  insufficient-history, invalid-frequency, and unavailable-interval cases.
- [ ] Provide a UI field matrix mapping every control to its contract field,
  validation rule, default, and localized label.
- [ ] Provide a solution-state matrix for success, warnings, partial evaluation,
  invalid input, fitting failure, and cancellation.
- [ ] Provide the registered artifact list and sample generated files.
- [ ] State explicitly which language may describe assumptions and which claims
  are forbidden.

### B1 - Navigation And Formulation View

- [ ] Add Forecasting under the existing AI & Machine Learning navigation menu,
  not as a new top-level menu item.
- [ ] Build timestamp/target table entry and versioned JSON import.
- [ ] Add method, horizon, frequency, season length, evaluation strategy, and
  bounded advanced options with controls appropriate to each value type.
- [ ] Dynamically show only method-relevant fields while preserving entered
  values when switching methods where safe.
- [ ] Make validation errors local, actionable, and synchronized in English and
  Italian.
- [ ] Use the established Optees info-button component and modal layout.

### B2 - Solution View

- [ ] Show forecast status, method, horizon, origin, evaluation strategy,
  metrics, parameters, diagnostics, and independent validation status.
- [ ] Present actual, fitted, holdout, and future rows in a sortable/readable
  table without implying that unavailable actual future values are zero.
- [ ] Reuse the headless chart semantics for the interactive desktop chart.
- [ ] Keep interval bands visually distinct and label their exact semantics.
- [ ] Handle long histories with stable dimensions, bounded rendering, and
  usable scrolling or sampling controls.
- [ ] Expose optional artifact/report generation through existing workflows
  rather than duplicating export logic in the view.

### B3 - Educational Content And Examples

- [ ] Write matched English and Italian problem-description pages explaining
  temporal order, horizon, trend, seasonality, holdout, rolling origin,
  residuals, uncertainty, leakage, and why forecasting is not causality.
- [ ] Write at least three worked examples: stable demand, trend, and seasonal
  demand. Each example must use a committed valid payload and verified result.
- [ ] Explain when naive or seasonal-naive is a stronger baseline than a more
  complex fitted model.
- [ ] Document insufficient history, structural breaks, outliers, missing
  periods, and interval limitations without promising production accuracy.
- [ ] Add JSON-format and solver-option information dialogs derived from the
  frozen contract.
- [ ] Update README, agent configuration guidance, and the website only after
  the released desktop and service behavior matches the copy.

### B4 - Presentation Verification

- [ ] Add focused navigation, manual-entry, JSON-import, solve, error,
  cancellation, localization, info-dialog, and result-view tests.
- [ ] Verify English and Italian layouts at supported desktop sizes.
- [ ] Verify table headers, long timestamps, chart legends, interval bands,
  focus order, and info-button visibility.
- [ ] Run targeted GUI tests during implementation and the release gates
  required by `docs/TESTING.md` before publication.
- [ ] Capture final dark-theme screenshots only from the verified release
  candidate for README and website use.

## Commit Strategy

Part A should use small commits in this order:

1. contract decision and domain;
2. baselines and solver adapter;
3. temporal evaluation and independent validator;
4. codecs, capability registration, and transports;
5. artifacts and reports;
6. references, benchmarks, packaging, and engine documentation.

Part B should remain independently reviewable:

1. handoff fixtures and UI skeleton;
2. formulation and import flow;
3. solution view and charts;
4. educational content, i18n, examples, and info dialogs;
5. presentation verification, screenshots, and release documentation.

Do not combine Part A and Part B into one release-sized commit. A desktop view
must never be used to compensate for an ambiguous or incomplete engine
contract.
