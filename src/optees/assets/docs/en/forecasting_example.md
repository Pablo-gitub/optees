# Forecasting Examples

Each example below uses a committed, valid payload and the result verified by
the Optees reference tests. Paste any payload into **Import JSON** to reproduce
it, or type the observations into the table.

## 1. Stable demand — Naive

A flat series with no trend and no season. The last value simply repeats, so
the naive baseline is exact.

| Timestamp | Value |
|---|---:|
| 2026-01-01 | 5 |
| 2026-01-02 | 5 |
| 2026-01-03 | 5 |
| 2026-01-04 | 5 |

```json
{
  "version": "1",
  "problem_type": "univariate_forecasting",
  "target_name": "constant_demand",
  "frequency": "daily",
  "horizon": 2,
  "method": "naive",
  "observations": [
    {"timestamp": "2026-01-01", "value": 5},
    {"timestamp": "2026-01-02", "value": 5},
    {"timestamp": "2026-01-03", "value": 5},
    {"timestamp": "2026-01-04", "value": 5}
  ],
  "evaluation": {"strategy": "holdout", "holdout_size": 1}
}
```

**Verified result:** forecast `[5, 5]`; MAE, RMSE and MAPE all `0`; independent
validation `verified`. When the series is flat, no fancier method can do better.

## 2. Growing demand — Naive as a baseline

A clean upward trend of `+2` per day. Naive can only repeat the last value, so
it systematically lags a trend. This is the case where a trend-aware method
should earn its place.

| Timestamp | Value |
|---|---:|
| 2026-01-01 | 2 |
| 2026-01-02 | 4 |
| 2026-01-03 | 6 |
| 2026-01-04 | 8 |
| 2026-01-05 | 10 |

```json
{
  "version": "1",
  "problem_type": "univariate_forecasting",
  "target_name": "trend_demand",
  "frequency": "daily",
  "horizon": 2,
  "method": "naive",
  "observations": [
    {"timestamp": "2026-01-01", "value": 2},
    {"timestamp": "2026-01-02", "value": 4},
    {"timestamp": "2026-01-03", "value": 6},
    {"timestamp": "2026-01-04", "value": 8},
    {"timestamp": "2026-01-05", "value": 10}
  ],
  "evaluation": {"strategy": "holdout", "holdout_size": 2}
}
```

**Verified result:** forecast `[10, 10]`; MAE `3`, RMSE `3.16`, MAPE `32.5%`,
**MASE `1.5`**. MASE above `1` confirms naive underperforms the in-sample
baseline here — a signal to try Holt-Winters, which can follow the trend.

## 3. Seasonal demand — Seasonal naive

A repeating three-month cycle `10, 20, 30`. With `season_length = 3`, seasonal
naive copies the value from one season ago and reproduces the cycle exactly.

| Timestamp | Value | | Timestamp | Value |
|---|---:|---|---|---:|
| 2025-01-01 | 10 | | 2025-06-01 | 30 |
| 2025-02-01 | 20 | | 2025-07-01 | 10 |
| 2025-03-01 | 30 | | 2025-08-01 | 20 |
| 2025-04-01 | 10 | | 2025-09-01 | 30 |
| 2025-05-01 | 20 | | | |

```json
{
  "version": "1",
  "problem_type": "univariate_forecasting",
  "target_name": "seasonal_demand",
  "frequency": "monthly",
  "horizon": 3,
  "method": "seasonal_naive",
  "season_length": 3,
  "observations": [
    {"timestamp": "2025-01-01", "value": 10},
    {"timestamp": "2025-02-01", "value": 20},
    {"timestamp": "2025-03-01", "value": 30},
    {"timestamp": "2025-04-01", "value": 10},
    {"timestamp": "2025-05-01", "value": 20},
    {"timestamp": "2025-06-01", "value": 30},
    {"timestamp": "2025-07-01", "value": 10},
    {"timestamp": "2025-08-01", "value": 20},
    {"timestamp": "2025-09-01", "value": 30}
  ],
  "evaluation": {"strategy": "holdout", "holdout_size": 3}
}
```

**Verified result:** forecast `[10, 20, 30]`; MAE, RMSE and MAPE all `0`;
validation `verified`. When a fixed cycle dominates, seasonal naive is a very
strong baseline.

## Reading edge cases

- **Too little history**: with only a couple of points, evaluation can be
  unavailable and the metrics return `not available` rather than a guess.
- **A zero actual value**: MAPE is left **undefined** because it would divide by
  zero; MAE and RMSE are still reported.
- **Future actuals**: the solution table shows future rows with no actual value.
  An empty actual means "not yet observed" — never `0`.
