# Targeted Forecasting Expansion Plan

## Work Unit

- **ID:** `OPT-DS-04`
- **State:** candidate planning only; `FC-C` reopened, implementation blocked
- **Type:** domain-neutral statistical forecasting expansion delivered through bounded micro-gates
- **Parent roadmap:** `ROADMAP.md`
- **Prerequisites:** `ROBUST-C`/`ROBUST-UI` satisfied by `OPT-DS-03`, `QP-I`/`QP-UI` and `OPT-DS-QP-H` satisfied by `OPT-DS-02`
- **Consumer:** Decision Simulator phase `DS-06`
- **Backend implementation owner:** Gemini
- **UI owner:** Claude, only at `OPT-DS-04F`
- **Review:** Codex after every micro-gate
- **Final integration gate:** `FC-H`

## Independent review and prerequisite

The original planning and contract-freeze claims are not accepted as execution
readiness. First supply baseline simulator evidence selecting the smallest useful
increment, complying with the authoritative [forecasting evidence protocol](forecasting-evidence-protocol.md).
No such evidence is attached to this plan. The statistical corrections
and unresolved decisions are maintained in
[the candidate decision document](../../contracts/targeted-forecasting-contract.md).
The sequence below is provisional, not an authorization to implement every candidate.

Review verification: 150 tests pass across the corrected decision probes and
`tests/data/`; focused Ruff checks and formatting pass. These checks establish
arithmetic counterexamples and existing fixture health, not `FC-C` completion.
No production code or UI changed; the full runtime/GUI suite was not rerun.

## Candidate objective

Deliver targeted, domain-neutral time-series forecasting increments motivated by
decision-simulation requirements, expanding beyond the baseline `naive`, `seasonal_naive`,
and `holt_winters_additive` capabilities:

1. **Random walk with drift**: baseline stochastic trend model with exact analytical estimation.
2. **Return transformation and forecasting**: explicit log-return or relative-difference
   modeling with strictly forward-mapped reconstruction to original level space, eliminating
   future data leakage.
3. **Transparent volatility estimation**: rolling standard deviation and exponentially
   weighted moving average (EWMA) volatility estimators providing explicit variance scales.
4. **Finite scenario and prediction interval generation**: candidate parametric and empirical
   quantile intervals, plus candidate finite scenarios requiring a consumer mapping to
   `scenario.linear.min_max_loss` and `scenario.linear.max_min_reward`.

Optees owns the statistical formulation, chronological validation, honest status reporting,
and independent verification. It must not acquire trading-specific entities, price tickers,
portfolio concepts, or claims of financial returns.

## Execution Discipline

This work unit follows the bounded micro-gate sequence established in `OPT-DS-03`:

- Only one micro-gate may be assigned at a time.
- Every micro-gate starts from its accepted predecessor commit.
- Planning, implementation, and review remain distinct task roles.
- Gemini implements domain, application, codecs, validators, transports, and fixtures.
- Claude exclusively implements the desktop presentation, visualization, and localization
  at `OPT-DS-04F`.
- Codex independently reviews each gate before the next gate is authorized.
- No live network, external API, deep neural model, broad AutoML search space, or native
  repackaging is authorized by this work unit.
- One local atomic commit per micro-gate with concise imperative message; no AI attribution;
  no remote push.

## Proposed Architectural Direction

- **Chronological integrity:** All training, estimation, and evaluation must respect strict
  time ordering. Shuffling, random splitting, and retroactive window recalculations are forbidden.
- **Domain neutrality:** Time-series observations remain generic `(timestamp, value)` pairs.
- **Downstream composability:** Forecasts are not optimization problems. A consumer-owned
  mapping must define variables, units, affine loss/reward coefficients and constraints
  before using `scenario.linear.*`; direct DTO compatibility is not established.
- **Independent verification:** Point forecasts, intervals, metrics, and scenario values
  must be verified by independent arithmetic and temporal checks.

---

## Micro-gate Sequence

### Micro-gate A — Statistical and Contract Decision (`OPT-DS-04A`)

#### Scope

Freeze, without production implementation:

- Mathematical formulations and parameter estimation for:
  - `random_walk_with_drift`;
  - log-return and percentage-change transformations and inverse level mapping;
  - rolling and EWMA volatility estimation;
  - quantile-based prediction intervals and finite scenario fan discretization.
- Public JSON DTO schemas:
  - Problem schema: input series, declared frequency, selected method, transform options,
    horizon, evaluation settings, and optional scenario discretization parameters.
  - Result schema: point forecasts, historical fitted values, evaluation metrics, prediction
    intervals, and explicit scenario objects.
- Strict rejection rules: non-increasing timestamps, non-finite values, negative values under
  log transforms, insufficient sample size, unsupported frequencies.
- Chronological evaluation semantics: holdout and rolling-origin metrics without leakage.
- Independent validation checks and tolerances.
- Canonical analytic reference cases.

#### Allowed changes

- `docs/roadmaps/case-study/05-targeted-forecasting-expansion.md`;
- `docs/contracts/targeted-forecasting-contract.md`;
- focused contract-decision probe tests;
- roadmap registration in `docs/roadmaps/README.md` and `docs/roadmaps/case-study/ROADMAP.md`.

#### Forbidden changes

- Production domain, application, adapter, composition, or transport code;
- UI, localization, or chart widgets;
- Simulator code or trading examples;
- Deep learning or external network dependencies.

**Gate `FC-C` (NOT achieved):** Baseline evidence, statistical decisions, executable
schema probes and independent review remain required. Existing analytical probes
are not implementation or interoperability evidence.

---

### Micro-gate B — Engine and Pure Evaluator (`OPT-DS-04B`)

Implement pure statistical domain models, estimation algorithms, walk-forward evaluators,
and transformation services.

#### Scope

- Pure domain entities and value objects for drift estimation, volatility, and scenarios.
- Numerical estimation using existing standard libraries (NumPy, SciPy, statsmodels).
- Evaluator computing MAE, RMSE, MAPE, and MASE over strictly past observations.
- Unit tests covering deterministic estimation, edge cases, and zero future leakage.

**Gate `FC-E`:** Domain models and estimators pass comprehensive unit tests and chronological
evaluations with verified zero leakage.

---

### Micro-gate C — Result Reconstruction and Independent Validation (`OPT-DS-04C`)

Implement independent solution validation and result reconstruction.

#### Scope

- Independent validator verifying:
  - Timestamp continuity and horizon alignment;
  - Point forecast arithmetic correctness;
  - Interval ordering ($l_t \le \hat{y}_t \le u_t$);
  - Scenario value consistency and probability normalization;
  - Metric recomputation from residuals.
- Honest reporting of validation statuses: `verified`, `partial`, `failed`.

**Gate `FC-V`:** Independent validator detects deliberate tampering in point forecasts,
intervals, and scenario values across all reference cases.

---

### Micro-gate D — Public Capability and Delivery (`OPT-DS-04D`)

Expose the new forecasting capability through the shared application layer and generic
interfaces.

#### Scope

- Capability registration in `local_agent.py`.
- Strict versioned input and result codecs.
- Interface parity across Application Service, CLI, HTTP REST, and MCP.
- End-to-end integration tests.

**Gate `FC-I`:** Capability discovery, input validation, execution, independent validation,
and normalized results have verified parity across CLI, REST, and MCP.

---

### Micro-gate E — Reference Fixtures and Consumer Handoff (`OPT-DS-04E`)

Publish a self-contained, frozen reference package for downstream consumers.

#### Scope

- Canonical reference cases covering all methods, edge cases, and validation probes.
- Consumer `README.md` detailing mathematical conventions and tolerance rules.
- Deterministic `manifest.json` with per-file SHA-256 and aggregate SHA-256.
- Fixture integrity tests verifying byte hashes, mutations, and non-deterministic field exclusion.

**Gate `FC-H`:** Downstream consumers (including the Decision Simulator) can execute and
verify forecasting policies against identical frozen fixtures without runtime dependencies
on the Optees codebase.

---

### Micro-gate F — Desktop Workflow (`OPT-DS-04F`, Claude)

Implement the accessible, bilingual PySide6 user interface.

#### Scope

- Series inspection, method selection, and transform parameter configuration.
- Result table presenting point forecasts, intervals, and evaluation metrics.
- Accessible chart widget displaying actual history, point forecast, uncertainty fan,
  and discrete scenarios.
- Complete English and Italian localization parity.

**Gate `FC-UI`:** PySide6 desktop workflow is bilingual, accessible, reviewed, and passes
all GUI tests without modifying mathematical or validation layers.

---

## Next Implementation Boundary

Only evidence collection adhering to [forecasting-evidence-protocol.md](forecasting-evidence-protocol.md)
and subsequent revision of the candidate statistical/contract decision may proceed.
`FC-C` remains NOT satisfied and must be independently accepted before `OPT-DS-04B` can be
assigned. No targeted forecasting production, solver, codec, or UI implementation is authorized.
