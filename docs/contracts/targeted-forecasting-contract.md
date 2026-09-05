# Targeted Time-Series Forecasting Contract

## Document Status

- **Work Unit:** `OPT-DS-04`
- **Gate:** `FC-C`
- **State:** frozen specification
- **Capability ID:** `forecasting.timeseries.targeted`
- **Contract Version:** `1`
- **Problem Schema Version:** `1`
- **Result Schema Version:** `1`
- **Parent roadmap:** `docs/roadmaps/case-study/05-targeted-forecasting-expansion.md`
- **Implementation Status:** contract and semantic decision frozen by `OPT-DS-04A`.

This contract defines and freezes the mathematical formulation, statistical estimators,
evaluation semantics, public JSON Data Transfer Objects (DTOs), independent validation guarantees,
and downstream scenario composability for targeted time-series forecasting in Optees.

---

## 1. Mathematical Scope and Statistical Estimators

### 1.1 Input Time Series Semantics

Let $Y = (y_1, y_2, \dots, y_T)^T \in \mathbb{R}^T$ be a univariate sequence of $T \ge 3$
observations recorded at strictly increasing ISO 8601 timestamps $t_1 < t_2 < \dots < t_T$.

- **Timestamps:** Each timestamp $t_i$ must be a valid ISO 8601 date or date-time string.
  Mixed timezone-aware and timezone-naive timestamps are rejected with
  `forecasting.mixed_timezones`. Timestamps out of order or duplicate timestamps are
  rejected with `forecasting.timestamps_out_of_order`.
- **Declared Frequency:** The series requires an explicit regular frequency token $\nu \in
  \{\text{"hourly"}, \text{"daily"}, \text{"weekly"}, \text{"monthly"}, \text{"quarterly"}, \text{"yearly"}\}$.
  Observations missing declared period intervals or off-grid timestamps are rejected
  with `forecasting.irregular_timestamps`. Schema version `1` does not impute or interpolate missing periods.
- **Finite values:** All observations $y_i$ must be finite real numbers. NaN, $\pm\infty$,
  and booleans are rejected with `forecasting.non_finite_value`.

### 1.2 Return Space Transformations and Inverse Level Mapping

To support stationary modeling and relative changes, the contract specifies two explicit
forward transformations and their exact inverse mappings back to the original level space:

#### 1.2.1 Logarithmic Returns (`transform: "log_return"`)

Requires strictly positive series observations: $y_t > 0$ for all $t = 1, \dots, T$.
If any $y_t \le 0$, the payload is rejected with `forecasting.non_positive_value`.

- **Forward transform:**
  \[
  r_t = \ln(y_t) - \ln(y_{t-1}) = \ln\left(\frac{y_t}{y_{t-1}}\right), \quad t = 2, \dots, T
  \]
  producing $T - 1$ return observations.
- **Point forecast inversion (geometric path):**
  Given forecasted returns $\hat{r}_{T+1}, \hat{r}_{T+2}, \dots, \hat{r}_{T+h}$ for horizon $h \ge 1$:
  \[
  \hat{y}_{T+h|T} = y_T \cdot \exp\left(\sum_{k=1}^h \hat{r}_{T+k}\right)
  \]
  Because $\sum_{k=1}^h r_{T+k} = \ln(y_{T+h}) - \ln(y_T)$, the telescoping sum guarantees
  exact consistency with historical realizations when evaluated on in-sample steps.

#### 1.2.2 Relative Percentage Change (`transform: "percentage_change"`)

Requires non-zero lag observations: $y_{t-1} \ne 0$ for all $t = 2, \dots, T$.

- **Forward transform:**
  \[
  \rho_t = \frac{y_t - y_{t-1}}{y_{t-1}}, \quad t = 2, \dots, T
  \]
- **Point forecast inversion:**
  Given forecasted percentage changes $\hat{\rho}_{T+1}, \dots, \hat{\rho}_{T+h}$:
  \[
  \hat{y}_{T+h|T} = y_T \cdot \prod_{k=1}^h (1 + \hat{\rho}_{T+k})
  \]

#### 1.2.3 Identity / Level (`transform: "none"`)

No transformation is applied; estimation operates directly on $y_t$.

---

### 1.3 Random Walk with Drift (`method: "random_walk_with_drift"`)

The random walk with drift model defines the process:
\[
z_t = z_{t-1} + c + \varepsilon_t, \quad \varepsilon_t \sim \text{i.i.d.} \mathcal{N}(0, \sigma^2)
\]
where $z_t$ is either the raw series $y_t$ (when `transform: "none"`) or the transformed series.

#### Analytical Parameter Estimation
For $N$ observations $z_1, \dots, z_N$ (where $N = T$ for raw series, or $N = T-1$ for returns):
- **Drift parameter $\hat{c}$:**
  \[
  \hat{c} = \frac{1}{N - 1} \sum_{t=2}^N (z_t - z_{t-1}) = \frac{z_N - z_1}{N - 1}
  \]
- **In-sample fitted values:**
  \[
  \hat{z}_t = z_{t-1} + \hat{c}, \quad t = 2, \dots, N
  \]
- **Residuals and sample variance:**
  \[
  e_t = z_t - \hat{z}_t, \quad s^2 = \frac{1}{N - 2} \sum_{t=2}^N e_t^2 = \frac{1}{N - 2} \sum_{t=2}^N \left((z_t - z_{t-1}) - \hat{c}\right)^2
  \]
- **Point forecast for horizon step $h \ge 1$:**
  \[
  \hat{z}_{N+h|N} = z_N + h \cdot \hat{c}
  \]
- **Forecast error variance and standard deviation:**
  \[
  \sigma_h^2 = h \cdot s^2 \left(1 + \frac{h}{N - 1}\right), \quad \sigma_h = s \sqrt{h \left(1 + \frac{h}{N - 1}\right)}
  \]

---

### 1.4 Volatility Estimation

When volatility estimation is requested (`volatility_estimation`), Optees computes explicit,
transparent variance estimates over the stationary return series $r_2, \dots, r_T$:

#### 1.4.1 Rolling Standard Deviation (`volatility_model: "rolling"`)
Given window size $W$ ($2 \le W \le T - 1$):
\[
\bar{r}_{t, W} = \frac{1}{W} \sum_{i=0}^{W-1} r_{t-i}, \quad
\hat{\sigma}_t = \sqrt{\frac{1}{W - 1} \sum_{i=0}^{W-1} (r_{t-i} - \bar{r}_{t, W})^2}, \quad t = W+1, \dots, T
\]

#### 1.4.2 Exponentially Weighted Moving Average (`volatility_model: "ewma"`)
Using decay factor $\lambda \in (0, 1)$ (RiskMetrics standard default $\lambda = 0.94$):
\[
\sigma_t^2 = \lambda \sigma_{t-1}^2 + (1 - \lambda) r_t^2, \quad t = 3, \dots, T
\]
with deterministic sample variance initialization: $\sigma_2^2 = \frac{1}{T-2} \sum_{t=2}^T (r_t - \bar{r})^2$.

---

### 1.5 Prediction Intervals

For each horizon step $h \in \{1, \dots, H\}$, when prediction intervals are requested at
confidence level $1 - \alpha \in (0, 1)$ (e.g., $0.95$ with critical value $z_{1-\alpha/2} \approx 1.95996$):
\[
l_{T+h} = \hat{y}_{T+h|T} - z_{1-\alpha/2} \cdot \sigma_h, \quad
u_{T+h} = \hat{y}_{T+h|T} + z_{1-\alpha/2} \cdot \sigma_h
\]
When modeling in log-return space, the interval bounds are mapped exponentially to guarantee
non-negative boundaries:
\[
l_{T+h} = y_T \cdot \exp\left(\sum_{k=1}^h \hat{r}_{T+k} - z_{1-\alpha/2} \cdot \sigma_h\right), \quad
u_{T+h} = y_T \cdot \exp\left(\sum_{k=1}^h \hat{r}_{T+k} + z_{1-\alpha/2} \cdot \sigma_h\right)
\]
Invariant: $l_{T+h} \le \hat{y}_{T+h|T} \le u_{T+h}$ must strictly hold within numeric tolerance $\varepsilon = 10^{-7}$.

---

### 1.6 Finite Scenario Discretization (Composability with `scenario.linear.*`)

To enable zero-glue programmatic pipelining into `scenario.linear.min_max_loss` and
`scenario.linear.max_min_reward`, the result object optionally provides a set of $K \ge 2$
deterministic scenarios $\{s_1, \dots, s_K\}$ discretized from the predictive distribution:

- **Quantile Specification:** Given declared quantiles $0 < q_1 < q_2 < \dots < q_K < 1$
  (e.g., standard 3-scenario fan: $[0.10, 0.50, 0.90]$, or 5-scenario fan: $[0.05, 0.25, 0.50, 0.75, 0.95]$).
- **Deterministic Scenario Identifiers:** Scenario IDs are generated deterministically as
  `"scen_q{int(round(q * 100)):02d}"` (e.g., `"scen_q10"`, `"scen_q50"`, `"scen_q90"`).
- **Scenario Values across Horizon:** For each step $h \in \{1, \dots, H\}$:
  \[
  v_k(h) = \hat{y}_{T+h|T} + \Phi^{-1}(q_k) \cdot \sigma_h
  \]
  (or in log space: $v_k(h) = y_T \exp(\sum \hat{r} + \Phi^{-1}(q_k) \sigma_h)$).
- **Downstream Format Parity:** Each scenario entry declares:
  - `scenario_id`: unique string ID;
  - `probability_weight`: normalized empirical or assigned weight ($p_k > 0$, $\sum p_k = 1.0$);
  - `values`: ordered numeric vector $(v_k(1), \dots, v_k(H))$ matching the horizon variable sequence.

---

## 2. Chronological Evaluation Semantics (Zero Future Leakage)

Evaluation reserves historical observations strictly according to temporal order:

1. **Holdout Evaluation (`evaluation.strategy: "holdout"`):**
   - Given holdout size $H_{eval} \ge 1$, the training window is strictly $t = 1, \dots, T - H_{eval}$.
   - The test window is strictly $t = T - H_{eval} + 1, \dots, T$.
   - The model is fitted once using only the training window.
   - Under no circumstances may any statistic (mean, drift, sample variance, or EWMA) be computed
     using test observations.
2. **Rolling-Origin Evaluation (`evaluation.strategy: "rolling_origin"`):**
   - Given origin count $N_{orig} \ge 1$ and step size $\Delta \ge 1$:
   - For each origin $j \in \{1, \dots, N_{orig}\}$, the cutoff index $T_j$ satisfies $T_j \le T - H_{eval}$.
   - Training history is restricted to $t \le T_j$; predictions are made for $t = T_j + 1, \dots, T_j + H_{eval}$.
3. **Evaluation Metrics:**
   Computed on test window residuals $e_t = y_t - \hat{y}_t$:
   - $\text{MAE} = \frac{1}{H_{eval}} \sum_{t=1}^{H_{eval}} |y_t - \hat{y}_t|$
   - $\text{RMSE} = \sqrt{\frac{1}{H_{eval}} \sum_{t=1}^{H_{eval}} (y_t - \hat{y}_t)^2}$
   - $\text{MAPE} = \frac{100}{H_{eval}} \sum_{t=1}^{H_{eval}} \left|\frac{y_t - \hat{y}_t}{y_t}\right|$ (unavailable if any test $y_t = 0$)
   - $\text{MASE} = \frac{\text{MAE}}{\frac{1}{T_{train}-1} \sum_{t=2}^{T_{train}} |y_t - y_{t-1}|}$ (unavailable if denominator is zero).

---

## 3. Public JSON Data Transfer Objects

### 3.1 Problem DTO Schema v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TargetedForecastingProblem",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "problem_type", "series", "frequency", "horizon", "method"],
  "properties": {
    "version": { "type": "string", "const": "1" },
    "problem_type": { "type": "string", "const": "targeted_forecasting" },
    "series": {
      "type": "array",
      "minItems": 3,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["timestamp", "value"],
        "properties": {
          "timestamp": { "type": "string" },
          "value": { "type": "number" }
        }
      }
    },
    "frequency": {
      "type": "string",
      "enum": ["hourly", "daily", "weekly", "monthly", "quarterly", "yearly"]
    },
    "horizon": { "type": "integer", "minimum": 1, "maximum": 1000 },
    "method": {
      "type": "string",
      "enum": ["random_walk_with_drift"]
    },
    "transform": {
      "type": "string",
      "enum": ["none", "log_return", "percentage_change"],
      "default": "none"
    },
    "volatility_estimation": {
      "type": "object",
      "additionalProperties": false,
      "required": ["model"],
      "properties": {
        "model": { "type": "string", "enum": ["rolling", "ewma"] },
        "rolling_window": { "type": "integer", "minimum": 2 },
        "ewma_lambda": { "type": "number", "exclusiveMinimum": 0.0, "maximum": 1.0 }
      }
    },
    "prediction_intervals": {
      "type": "object",
      "additionalProperties": false,
      "required": ["confidence_level"],
      "properties": {
        "confidence_level": { "type": "number", "exclusiveMinimum": 0.5, "exclusiveMaximum": 1.0 }
      }
    },
    "scenario_discretization": {
      "type": "object",
      "additionalProperties": false,
      "required": ["quantiles"],
      "properties": {
        "quantiles": {
          "type": "array",
          "minItems": 2,
          "maxItems": 100,
          "items": { "type": "number", "exclusiveMinimum": 0.0, "exclusiveMaximum": 1.0 }
        }
      }
    },
    "evaluation": {
      "type": "object",
      "additionalProperties": false,
      "required": ["strategy"],
      "properties": {
        "strategy": { "type": "string", "enum": ["none", "holdout", "rolling_origin"] },
        "holdout_size": { "type": "integer", "minimum": 1 }
      }
    }
  }
}
```

### 3.2 Result DTO Schema v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TargetedForecastingResult",
  "type": "object",
  "additionalProperties": false,
  "required": ["forecast_origin", "horizon", "method", "forecasts"],
  "properties": {
    "forecast_origin": { "type": "string" },
    "horizon": { "type": "integer" },
    "method": { "type": "string" },
    "drift_parameter": { "type": ["number", "null"] },
    "forecasts": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["step", "timestamp", "point_forecast"],
        "properties": {
          "step": { "type": "integer", "minimum": 1 },
          "timestamp": { "type": "string" },
          "point_forecast": { "type": "number" },
          "lower_bound": { "type": ["number", "null"] },
          "upper_bound": { "type": ["number", "null"] }
        }
      }
    },
    "fitted_values": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["timestamp", "fitted_value", "residual"],
        "properties": {
          "timestamp": { "type": "string" },
          "fitted_value": { "type": "number" },
          "residual": { "type": "number" }
        }
      }
    },
    "volatility": {
      "type": ["object", "null"],
      "additionalProperties": false,
      "required": ["model", "latest_volatility"],
      "properties": {
        "model": { "type": "string" },
        "latest_volatility": { "type": "number" }
      }
    },
    "scenarios": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["scenario_id", "quantile", "probability_weight", "values"],
        "properties": {
          "scenario_id": { "type": "string" },
          "quantile": { "type": "number" },
          "probability_weight": { "type": "number" },
          "values": {
            "type": "array",
            "items": { "type": "number" }
          }
        }
      }
    },
    "metrics": {
      "type": ["object", "null"],
      "additionalProperties": false,
      "properties": {
        "mae": { "type": ["number", "null"] },
        "rmse": { "type": ["number", "null"] },
        "mape": { "type": ["number", "null"] },
        "mase": { "type": ["number", "null"] }
      }
    }
  }
}
```

---

## 4. Canonical Analytical Examples

### 4.1 Example 1: `random_walk_with_drift` on Pure Linear Series

- **Input:** $T = 5$ observations at daily frequency:
  $y_1 = 10.0$, $y_2 = 12.0$, $y_3 = 14.0$, $y_4 = 16.0$, $y_5 = 18.0$.
- **Analytical Drift:**
  \[
  \hat{c} = \frac{18.0 - 10.0}{5 - 1} = \frac{8.0}{4} = 2.0
  \]
- **In-sample Fitted Values and Residuals:**
  - $\hat{y}_2 = 10.0 + 2.0 = 12.0 \implies e_2 = 0.0$
  - $\hat{y}_3 = 12.0 + 2.0 = 14.0 \implies e_3 = 0.0$
  - $\hat{y}_4 = 14.0 + 2.0 = 16.0 \implies e_4 = 0.0$
  - $\hat{y}_5 = 16.0 + 2.0 = 18.0 \implies e_5 = 0.0$
  - $s^2 = 0.0$, $\sigma_h = 0.0$.
- **Point Forecasts for $H = 2$:**
  - $h=1$: $\hat{y}_6 = 18.0 + 1 \cdot 2.0 = 20.0$
  - $h=2$: $\hat{y}_7 = 18.0 + 2 \cdot 2.0 = 22.0$

### 4.2 Example 2: Log-Return Transformation and Scenario Fan

- **Input:** $T = 4$ observations: $y_1 = 100.0$, $y_2 = 105.0$, $y_3 = 102.0$, $y_4 = 110.0$.
- **Log Returns:**
  - $r_2 = \ln(105/100) \approx 0.04879016$
  - $r_3 = \ln(102/105) \approx -0.02898754$
  - $r_4 = \ln(110/102) \approx 0.07550756$
- **Drift of Returns:**
  \[
  \hat{c}_r = \frac{r_4 - r_2}{3 - 1} = \frac{0.07550756 - 0.04879016}{2} \approx 0.01335870
  \]
- **1-step Forecast in Return Space:**
  $\hat{r}_5 = r_4 + \hat{c}_r \approx 0.07550756 + 0.01335870 = 0.08886626$.
- **1-step Inverted Level:**
  $\hat{y}_5 = 110.0 \cdot \exp(0.08886626) \approx 120.222$.
- **Quantile Scenarios ($q \in [0.10, 0.50, 0.90]$):**
  - Discretized into `"scen_q10"`, `"scen_q50"`, `"scen_q90"`.
  - Normalized probabilities: $p = [0.25, 0.50, 0.25]$.

---

## 5. Independent Validation Guarantees

The independent solution validator verifies:
1. `forecasting.timestamps`: Timestamps are strictly sequential without gaps.
2. `forecasting.point_forecast_arithmetic`: Level forecasts match inverted transformation of underlying model forecasts within tolerance $\varepsilon_{abs} = 10^{-7}$.
3. `forecasting.intervals_ordering`: Interval lower bound $\le$ point forecast $\le$ upper bound.
4. `forecasting.scenarios_structure`: Scenario probabilities sum to $1.0 \pm 10^{-7}$, scenario IDs match declared quantiles, values match evaluation.
5. `forecasting.evaluation_metrics`: Metrics match recomputed test residual formulas.

---

## 6. Status Mappings

- `job_status`: `queued`, `running`, `completed`, `failed`, `cancelled`.
- `mathematical_status`:
  - `forecasted`: Point forecast and all requested components estimated successfully.
  - `partial`: Point forecast estimated, but optional interval or evaluation metric unavailable (e.g. MAPE undefined due to actual zero).
  - `failed`: Estimation failure (e.g., non-positive series under log return).
- `validation_status`: `verified`, `partial`, `failed`.
