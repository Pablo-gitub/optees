# Targeted Forecasting: Candidate Decisions and Review

## Document status

- **Work Unit:** `OPT-DS-04`
- **Gate:** `FC-C` — NOT satisfied
- **State:** candidate design, not a frozen public contract
- **Implementation Status:** no targeted forecasting runtime implemented.
- Parent: [targeted forecasting plan](../roadmaps/case-study/05-targeted-forecasting-expansion.md).

The initial freeze in `2df5938` was not accepted by independent review.
Existing forecasting capabilities are unchanged. The proposed capability identifier
and version-1 DTOs are not registered or reserved public interfaces.
The original draft remains available in Git history, not as an implementation specification.

## Evidence prerequisite

Before selecting an expansion, record the simulator baseline episode, dataset and
policy identities, chronological evaluation, observed limitation, and smallest
increment addressing it. Analytical probes do not replace this evidence.
No engine, new capability, or UI work is authorized by this document.

## Mathematical corrections and candidate choices

### Model space and sample size

A random walk with drift in levels is not a random walk fitted to returns.
The latter models changes in returns; neither automatically establishes stationarity.
Choose the intended stochastic process explicitly before freezing a method.

For N observations z, the candidate level-space drift is
c = (z[N] - z[1]) / (N - 1). With estimated drift, residual variance uses
N - 2 degrees of freedom, requiring N >= 3. A return transformation loses an
observation, so that same candidate requires at least four original levels,
including at every evaluation origin.

Log returns require all positive levels. Relative differences require nonzero
denominators, including the final training level for forward evaluation.
Define fractional versus percentage units; do not silently multiply by 100.

### Multi-step uncertainty

For independent innovations of variance s² and the candidate estimated drift,
the model-space h-step forecast-error variance is
s² [h + h²/(N - 1)]. Normal multipliers are an approximation with estimated
variance, not evidence of empirical calibration.
Reference: [Hyndman and Athanasopoulos, prediction intervals](https://otexts.robjhyndman.com/fpp3/prediction-intervals.html).

If the random walk is fitted to log returns, reconstructing a level requires
summing correlated future returns. Its cumulative error variance is instead
s² [sum(j², j=1..h) + (h(h+1)/2)²/(N - 1)] under that same candidate model.
For h=2 the innovation contribution is 5s², not 2s².
Exponentiating a Gaussian cumulative return gives a median/geometric forecast,
not its arithmetic mean; the latter includes half the cumulative variance.
The initial draft incorrectly reused marginal return variance for the cumulative level.

A product of relative changes needs its own distributional treatment.
An additive level interval or the log-return formula cannot be reused for it.
Do not claim exact coverage, calibrated scenarios, or unbiased level means from
a telescoping reconstruction identity.

### Volatility and chronology

The initial EWMA initialization used the entire return sample to initialize its
first historical variance, leaking later observations into earlier estimates.
One causal candidate is v[1] = r[1]² and
v[t] = lambda*v[t-1] + (1-lambda)*r[t]², with 0 < lambda < 1.
This is a zero-mean second-moment estimator, not automatically a centered sample
variance. A centered alternative requires a separately specified causal mean.
Rolling variance needs a declared window and degrees of freedom.
Choose initialization, availability time, annualization (if any), and whether
volatility is diagnostic or feeds forecast uncertainty; these remain open.

Full-training fitted residuals may use full-training parameter estimates, but
must not be called historical out-of-sample predictions.
Every holdout/rolling origin must refit transformations and all statistics using
its own prefix. Freeze origin enumeration, minimum history, horizon weighting,
missing metrics and zero denominators before defining evaluation DTOs.

### Scenarios and optimization boundary

Forecast values are NOT a `scenario.linear.*` problem. That contract requires
decision variables, constraints, affine objective coefficients and constants.
It does not consume the draft's `probability_weight` / `values` entries.
A consumer-owned, tested mapping must specify units, horizon, loss/reward sign,
decision-variable meaning and any shared term. Keep trading semantics outside Optees.

Marginal quantiles at each horizon are not a calibrated joint path distribution.
Quantile locations alone do not determine probability masses or dependence
across horizons/resources. Robust min/max does not need scenario probabilities.
Rounded percent-based scenario IDs collide (e.g. 0.101 and 0.104);
use a collision-free canonical rule after selecting a scenario contract.

## Contract decisions still required

- [ ] Baseline evidence and bounded scope accepted.
- [ ] Reuse/extension versus a separate capability justified against current forecasting.
- [ ] Statistical model, transforms, supported uncertainty and validation limits selected.
- [ ] Exact UTC/frequency/calendar grid, month-end and missing-period rules.
- [ ] Strict problem/result schemas with cross-field constraints and status envelope.
- [ ] Invalid-input corpus: short transformed history, zero/nonpositive values,
  booleans/nonfinite numbers, lambda endpoints, unknown/conflicting options,
  duplicate quantiles, invalid horizons and rolling-origin settings.
- [ ] Actual schema validation of valid/invalid instances, not only JSON parsing.
- [ ] Independent nonzero-variance and chronological counterexamples.
- [ ] Consumer mapping tested through the real scenario codec, if selected.
- [ ] Independent review accepting `FC-C`.

The accompanying probes establish arithmetic counterexamples and draft status
only. They do not test a production estimator, codec, no-leakage implementation,
interval calibration, or downstream interoperability.
