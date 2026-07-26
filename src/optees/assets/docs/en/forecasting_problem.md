# Time-series Forecasting

## What you are actually asking

Forecasting estimates the **future values** of one quantity from its own
**ordered past**. Optees works on a single univariate series: one timestamp
column and one numeric target, sampled at a regular frequency.

This is *not* the same problem as Linear Regression. Regression assumes rows
are independent and can be split at random. A time series is the opposite: the
order carries the information, and the future must never be used to predict the
past. Optees keeps these two capabilities separate on purpose.

## Temporal order and leakage

The single most important rule is that a model may only learn from data that
existed **before** the moment it predicts. Using any future observation while
fitting or evaluating — even indirectly, by shuffling rows or averaging across
the whole series — is called **leakage**. Leakage produces metrics that look
excellent in a study and collapse in reality.

Every Optees evaluation is *chronological*: each training window ends strictly
before the window it is scored on. Nothing is shuffled.

## The vocabulary

- **Observation** — one timestamp and one finite value.
- **Forecast origin** — the last observation the model is allowed to see.
- **Horizon** — how many future periods you ask for after the origin.
- **Season length** — how many observations make one full cycle (12 for
  monthly data with a yearly cycle, 7 for daily data with a weekly cycle).
- **Trend** — a persistent drift upward or downward.
- **Seasonality** — a pattern that repeats every season length.
- **Residual** — actual minus fitted; what the model did not explain.

## How each method computes a forecast

Notation: the training series is `y[1], y[2], ..., y[T]`, where `T` is the
forecast origin (the last observed period). A forecast `h` steps ahead is
written `yhat[T+h]`, and `m` is the season length.

### Naive

```
yhat[T+h] = y[T]        for every h = 1, 2, 3, ...
```

Every future value equals the last observed value. It carries the current level
forward and assumes no trend and no season. It is exact when the series is flat.

### Seasonal naive

```
yhat[T+h] = y[T + h - m * (floor((h - 1) / m) + 1)]
```

Each forecast repeats the value from the matching position in the most recent
complete season. With monthly data and `m = 12`, next January equals last
January. It needs at least two complete seasons of history.

### Holt-Winters (additive)

Three components are updated at each step with smoothing weights
`alpha, beta, gamma` in `[0, 1]`:

```
level     l[t] = alpha*(y[t] - s[t-m]) + (1 - alpha)*(l[t-1] + b[t-1])
trend     b[t] = beta *(l[t] - l[t-1]) + (1 - beta )*b[t-1]
season    s[t] = gamma*(y[t] - l[t-1] - b[t-1]) + (1 - gamma)*s[t-m]
forecast  yhat[T+h] = l[T] + h*b[T] + s[T + h - m*(floor((h-1)/m) + 1)]
```

The **level** tracks where the series is now, the **trend** how fast it moves,
and the **seasonal** terms the repeating offsets that are added on top. A larger
weight reacts faster to recent data; a smaller weight is smoother. Optees fits
`alpha, beta, gamma` deterministically through the statsmodels
`ExponentialSmoothing` estimator (additive trend and season only in this
version).

## Choosing a method

Optees ships three deterministic methods. A more complex method is **not**
automatically better.

- **Naive** repeats the last value. It is the honest baseline for a series with
  no trend and no stable season. If a fancier model cannot beat naive, the
  fancier model is not helping.
- **Seasonal naive** repeats the value from one season ago. When a fixed cycle
  dominates (weekly footfall, monthly demand), it is very hard to beat.
- **Holt-Winters (additive)** fits a level, an additive trend, and additive
  seasonality. Use it only when both a trend and a seasonal cycle are genuinely
  present; on a flat or purely seasonal series it can do *worse* than the
  baselines because it estimates parameters it does not need.

The metric **MASE** measures error relative to a naive baseline: a value below
1 means you beat naive, above 1 means you did worse.

## Evaluating honestly

- **Holdout** reserves the final periods as one test window and scores the
  forecast there.
- **Rolling origin** repeats that test over several moving windows, giving a
  more stable estimate on short series.
- **None** skips evaluation and only produces the future forecast.

Over the evaluated pairs of `actual` and `predicted` values, the metrics are:

```
MAE  = mean(|actual - predicted|)                 average error, same unit as y
RMSE = sqrt(mean((actual - predicted)^2))          penalizes large misses more
MAPE = 100 * mean(|(actual - predicted) / actual|) percent error; undefined if any actual = 0
MASE = MAE / mean(|y[t] - y[t-m]|)                 error relative to a naive step (m = 1, or the season length)
```

`MASE < 1` means you beat the naive baseline; `MASE > 1` means you did worse.

Reported metrics are recomputed **independently** from the public predictions
and observations, not taken on trust from the solver. MAPE is left **undefined**
when an actual value is zero (you cannot divide by it); Optees reports that
instead of inventing a number.

## Uncertainty is not a guarantee

A prediction interval describes a range with documented coverage semantics. It
is **method-specific**: when a method cannot justify an interval, Optees leaves
it out rather than drawing a comforting but meaningless band. An interval is an
estimate of uncertainty, never a promise.

## Forecasting is not causality

A forecast says "if the past pattern continues, this is the likely value." It
does **not** explain *why*, and it does not license a causal claim ("if we do X,
Y will follow"). Structural breaks — a new competitor, a price change, a
pandemic — can invalidate any model trained before them.

## Known limitations

- **Insufficient history**: with too few points, evaluation may be unavailable
  and metrics return an explicit "not available" state.
- **Outliers and structural breaks**: a single shock can dominate a short
  series; inspect the residual chart.
- **Missing periods**: irregular gaps are rejected unless an explicit policy is
  set. Optees never silently fills them.
- **No production guarantee**: these are educational, deterministic baselines.
  Passing the built-in checks verifies the recorded properties; it is not proof
  of real-world accuracy.
