# Forecasting Statistical Contract

This note freezes the statistical meaning of Forecasting schema version `1`.
Presentation, codecs, solver adapters, and educational material must preserve
these decisions. Planned behavior is identified explicitly.

## Initial Method Set

| Stable ID | Meaning | Backend | Prediction interval |
| --- | --- | --- | --- |
| `naive` | Every future value equals the latest training value. | Internal deterministic baseline | Unavailable |
| `seasonal_naive` | Each future value repeats the corresponding value from the latest complete season. | Internal deterministic baseline | Unavailable |
| `holt_winters_additive` | Additive level, trend, and seasonality estimated with Holt-Winters exponential smoothing. | statsmodels `ExponentialSmoothing` | Unavailable in the first adapter |

The maintained trend/seasonality implementation is statsmodels. Version 0.14.6
provides Python 3.12 wheels, uses a three-clause BSD license, and exposes a
complete Holt-Winters implementation. It adds a numerical package and its
transitive dependencies to native bundles, so Phase A2 must add dependency and
packaged smoke coverage together. SciPy is already bundled but offers
detrending and signal primitives rather than a maintained full Holt-Winters
forecasting estimator. Implementing the estimator inside Optees would create a
second statistical library to maintain and is therefore rejected.

Only additive trend and seasonality are included initially. Multiplicative,
damped, Box-Cox, ETS model selection, ARIMA, and automatic hyperparameter
search are deferred.

## Input Time Semantics

- Schema version `1` accepts a single finite numeric target observed at unique
  ISO 8601 timestamps.
- Domain observations use `datetime`. Public codecs will accept ISO dates or
  datetimes and preserve whether the series is timezone-naive or
  timezone-aware.
- A timezone-aware series is normalized to UTC. A series may not mix aware and
  naive timestamps.
- Input order is authoritative. Optees never sorts observations silently.
  Timestamps must be strictly increasing after normalization.
- Supported frequencies are `hourly`, `daily`, `weekly`, `monthly`,
  `quarterly`, and `yearly`.
- Every observation must lie on the sequence generated from the first
  timestamp at the declared frequency. Monthly, quarterly, and yearly
  frequencies use calendar arithmetic anchored to the first observation;
  impossible days are clamped to the last day of the target month without
  changing the original anchor.
- Duplicate timestamps, missing periods, and extra off-frequency timestamps
  are rejected. Schema version `1` supports only `missing_period_policy:
  "reject"`; no value is interpolated or imputed.

## History And Seasonality

- Every model requires at least two observations and a positive horizon.
- `seasonal_naive` and `holt_winters_additive` require an integer season length
  of at least two and at least two complete seasons in the training history.
- `naive` does not accept a season length.
- Evaluation removes observations from the fitting history. Each resulting
  training window must still meet the method-specific minimum.

## Evaluation

Supported strategies are:

- `none`: fit all history and produce only fitted/future output;
- `holdout`: reserve one final contiguous segment and never train on it;
- `rolling_origin`: evaluate a bounded number of chronological origins, each
  strictly earlier than the values it predicts.

Holdout size, rolling-origin count, step, evaluation horizon, and minimum
training window are explicit bounded integers. No random split or shuffling is
permitted.

Metrics use unrounded values:

- `MAE = mean(abs(actual - predicted))`;
- `RMSE = sqrt(mean((actual - predicted)^2))`;
- `MAPE = 100 * mean(abs((actual - predicted) / actual))`, unavailable when
  any evaluated actual value is zero;
- `MASE = MAE / mean(abs(y[t] - y[t-m]))`, where `m` is one for non-seasonal
  methods and the declared season length otherwise. It is unavailable when
  the training history is too short or the denominator is zero.

Unavailable metrics are represented as absent values, never as zero, infinity,
or a fabricated fallback.

## Uncertainty

Prediction intervals are optional method output. The first three methods do
not publish intervals in schema version `1`. A future method may provide them
only with a documented coverage level and calibration procedure. Lower and
upper bounds must either both be present or both be absent.

## Determinism, Tolerances, And Status

- Baselines are exact and deterministic.
- Holt-Winters uses deterministic initialization and optimization settings;
  no random seed is involved in the initial method set.
- Public finite-value and timestamp identities use an absolute tolerance of
  `1e-9` unless a capability descriptor states a stricter value.
- Stable mathematical statuses are `forecasted`, `partial`, `failed`, and
  `cancelled`. Job lifecycle and independent validation remain separate.
- Adapter warnings are mapped to stable diagnostics. Raw backend exceptions
  are not public result messages.

## References

- statsmodels 0.14.6,
  `statsmodels.tsa.holtwinters.ExponentialSmoothing`
- Hyndman and Athanasopoulos, *Forecasting: Principles and Practice*, third
  edition
