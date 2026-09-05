# Decision Simulator Forecasting Evidence Protocol

## Status and purpose

- Work unit: `OPT-DS-04` prerequisite evidence.
- State: reviewed protocol; no simulator evidence package exists yet.
- Gate `FC-C`: NOT satisfied.
- Production implementation `OPT-DS-04B`: blocked.
- Related plans: [case-study roadmap](ROADMAP.md),
  [targeted forecasting](05-targeted-forecasting-expansion.md), and
  [candidate mathematical decisions](../../contracts/targeted-forecasting-contract.md).

This protocol says what evidence the Decision Simulator must return before
Optees selects a forecasting increment. It does not assert in advance that an
increment is needed, rank candidates, or freeze statistical acceptance
thresholds without an experimental design.

## Existing Optees baseline

The evidence package must first exercise the shipped
`ml.forecasting.univariate` capability rather than reimplement it.

| Surface | Current behavior | Source |
| --- | --- | --- |
| Contract | Problem/result schema version 1 | `src/optees/application/codecs/forecasting_*_codec.py` |
| Methods | `naive`, `seasonal_naive`, `holt_winters_additive` | `src/optees/domain/value_objects/forecasting/forecasting_method.py` |
| Calendar | Regular hourly through yearly grids; missing-policy `reject` | `src/optees/domain/models/forecasting/forecasting_model.py` |
| Evaluation | `none`, chronological holdout, rolling origin | same model and forecasting use case |
| Metrics | MAE, RMSE, MAPE, MASE | `src/optees/domain/entities/forecasting/solution.py` |
| Output | Fitted/evaluation/future points, residuals and diagnostics | forecasting solution/result codec |
| Intervals | DTO slot exists; current baseline methods return no interval | result codec and validator |
| Validation | Temporal structure, arithmetic and method-specific invariants | `src/optees/application/validation/forecasting_solution_validator.py` |

Holt-Winters validation is deliberately partial because the independent
validator does not refit its nonlinear estimator. Existing chronological
splitting, metrics, naive baselines, regular calendars and transports must be
reused. Market holidays, trading actions and portfolio semantics remain in the
consumer.

These facts identify candidate gaps; they do not prove that prices require a
particular transform, that returns are stationary, that volatility clustering
exists, or that a richer forecast improves decisions.

## Required evidence package

### Immutable provenance

Every run must record:

- exact Optees and simulator commit hashes;
- capability ID and problem/result schema versions;
- dataset snapshot ID, canonical manifest hash, normalized-observation hash and
  source/licence identity (not merely the raw-file hash);
- episode definition ID/hash, run ID, calendar and policy version ID/hash;
- resource/series mapping and units;
- execution-cost and valuation rules;
- deterministic seed where any candidate is stochastic.

### Origin-level chronology

For every forecast origin, retain:

- knowledge cutoff and the hashes of observations eligible at that cutoff;
- training indices/timestamps and evaluation timestamps;
- method and complete parameters;
- forecast horizon and generated values;
- actual values only when they later become eligible;
- validation report and failure/unsupported status;
- the downstream decision and its solver receipt, when one exists.

A prefix-invariance probe must mutate future observations and prove identical
preprocessing, fitted parameters and outputs at the earlier origin. Rolling
evaluation must refit every data-dependent transformation on its own training
prefix. Results must distinguish expanding from fixed windows and single-step
from overlapping multi-step errors.

### Four separate result families

Report these independently; none substitutes for another.

1. **Forecast quality:** per-origin and aggregate MAE/RMSE/MASE, directional
   accuracy only when ties are defined, and comparison with the same-origin
   naive baseline.
2. **Mathematical validity:** support, finite values, chronological integrity,
   sample-size requirements, validator status and explicit limitations.
3. **Decision utility:** optimization feasibility, binding constraints/scenarios,
   allocation differences, turnover and sensitivity to changed inputs.
4. **Paper outcome:** equity/PnL, drawdown and transaction costs under identical
   execution assumptions.

Sharpe, Sortino, annualization, tail measures and statistical significance are
optional until their return convention, risk-free rate, sampling frequency,
dependence treatment, episode aggregation and uncertainty method are frozen.
A better PnL or a lower in-sample error alone cannot authorize a forecasting
feature.

### Comparative design before numerical thresholds

Before collecting evidence, freeze in the Simulator plan:

- assets/resources, episodes and regimes;
- origins, horizons and windows;
- primary and secondary metrics;
- baseline and candidate comparison;
- treatment of overlapping forecast errors and multiple comparisons;
- minimum practically relevant effect;
- uncertainty estimate or confidence procedure;
- failure and missing-data handling;
- acceptance, inconclusive and no-go rules.

Do not retrofit thresholds after results are visible. Fixed counts such as
“30 origins”, fixed p-values, or a universal coverage tolerance are not part of
this protocol; they depend on the frozen design and dependence structure.

## Candidate decision matrix

No candidate is preselected or rejected here.

| Candidate | Evidence that could motivate it | Main risk | No-go signal |
| --- | --- | --- | --- |
| Level random walk with drift | Persistent out-of-sample bias of naive level forecasts | Endpoint-sensitive drift and negative extrapolation | No material chronological improvement |
| Mean/drift model in log-return space | Positive multiplicative series and useful return forecast | Bias after exponentiation; distribution assumption | Returns have no useful predictable mean |
| Relative-change transform | Consumer requires fractional-change semantics that log returns cannot satisfy | Zero denominators and asymmetric products | No distinct consumer need |
| Rolling volatility | Static dispersion fails across frozen regimes | Window instability | Worse out-of-sample variance/coverage diagnostics |
| Causal EWMA | Recency weighting improves a frozen volatility target | Initialization/tuning leakage | No stable improvement across episodes |
| Prediction intervals | A decision consumes uncertainty and point forecasts are insufficient | Uncalibrated tails and wrong multi-step variance | Coverage/sharpness not useful under frozen protocol |
| Finite joint paths | Robust decisions change materially with coherent paths | Marginal quantiles are not joint trajectories | Consumer cannot define a valid compiler |
| Bounded AR/ARIMA | Prefix residuals retain forecastable autocorrelation | Selection bias and convergence failures | No out-of-sample gain over simpler baseline |

Stationarity, autocorrelation or heteroskedasticity tests may be diagnostics,
not automatic feature-selection rules. Their hypotheses, lag/order choice and
multiple-testing treatment must be specified before use.

## Mathematical constraints carried forward

- A random walk in levels is distinct from a model for returns around a mean,
  and both are distinct from a random walk of returns.
- A drifted random walk fitted to `N` model-space observations requires enough
  residual degrees of freedom; transforming `N` levels yields `N-1` returns.
- Multi-step uncertainty must follow the selected stochastic process. The
  weighted cumulative-return variance documented in the candidate decision
  applies only if future returns themselves follow a drifted random walk; it
  must not be reused for an iid-return mean model.
- Exponentiating a Gaussian log forecast yields its median; an arithmetic mean
  needs the stated distribution and variance adjustment.
- EWMA initialization and any lambda selection must use only the training prefix.
- Marginal quantiles do not define joint paths or probability masses.
- Scenario identifiers use canonical exact input or stable indices, never
  rounded floating-point percentages.
- A telescoping transform identity proves arithmetic reconstruction, not
  predictive quality or calibration.

## Forecast-to-optimization boundary

A forecast is not a `scenario.linear.*` problem. The Simulator owns an explicit,
versioned compiler that supplies:

- decision variables and units;
- bounds, budget/conservation constraints and decision horizon;
- one coherent trajectory per scenario, including cross-time/resource dependence;
- affine loss or reward coefficients and constants with declared sign;
- min-max versus max-min orientation;
- links back to the source forecast/path evidence.

The current robust min-max/max-min capabilities do not consume probability
weights. If a future stochastic objective needs probabilities, it requires a
different frozen contract.

## Handoff and authorization

A compliant package may be accepted, rejected or judged inconclusive. Only an
independent review may then select the smallest coherent Optees increment and
re-freeze `FC-C`. Until that happens:

- the current forecasting capability remains unchanged;
- no targeted forecasting engine, codec, transport or UI is authorized;
- `OPT-DS-04B` remains blocked.
