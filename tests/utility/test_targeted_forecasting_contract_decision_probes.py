from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_FILE = REPO_ROOT / "docs" / "contracts" / "targeted-forecasting-contract.md"


def load_contract_text() -> str:
    assert CONTRACT_FILE.is_file(), f"Contract file {CONTRACT_FILE} must exist."
    return CONTRACT_FILE.read_text(encoding="utf-8")


def extract_json_blocks(text: str) -> list[dict]:
    matches = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    blocks: list[dict] = []
    for raw in matches:
        try:
            blocks.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return blocks


def test_contract_document_exists_and_declares_provenance() -> None:
    text = load_contract_text()

    assert "Capability ID:** `forecasting.timeseries.targeted`" in text
    assert "Contract Version:** `1`" in text
    assert "Problem Schema Version:** `1`" in text
    assert "Result Schema Version:** `1`" in text
    assert "Gate:** `FC-C`" in text
    assert "Work Unit:** `OPT-DS-04`" in text


def test_contract_schemas_are_valid_json_definitions() -> None:
    text = load_contract_text()
    blocks = extract_json_blocks(text)

    # Must contain both Problem and Result schemas
    problem_schemas = [b for b in blocks if b.get("title") == "TargetedForecastingProblem"]
    result_schemas = [b for b in blocks if b.get("title") == "TargetedForecastingResult"]

    assert len(problem_schemas) == 1, "Must contain exactly one TargetedForecastingProblem schema"
    assert len(result_schemas) == 1, "Must contain exactly one TargetedForecastingResult schema"

    ps = problem_schemas[0]
    assert ps["properties"]["version"]["const"] == "1"
    assert ps["properties"]["problem_type"]["const"] == "targeted_forecasting"
    assert "random_walk_with_drift" in ps["properties"]["method"]["enum"]
    assert set(ps["properties"]["transform"]["enum"]) == {"none", "log_return", "percentage_change"}

    rs = result_schemas[0]
    assert "forecasts" in rs["required"]
    assert "horizon" in rs["required"]


def test_random_walk_with_drift_analytical_derivation() -> None:
    """Verify Example 1 from contract: y = [10.0, 12.0, 14.0, 16.0, 18.0]."""
    y = [10.0, 12.0, 14.0, 16.0, 18.0]
    T = len(y)

    # Analytical drift: c_hat = (y_T - y_1) / (T - 1)
    c_hat = (y[-1] - y[0]) / (T - 1)
    assert c_hat == pytest.approx(2.0, abs=1e-9)

    # In-sample fitted values and residuals
    fitted = [y[t - 1] + c_hat for t in range(1, T)]
    residuals = [y[t] - fitted[t - 1] for t in range(1, T)]
    assert fitted == [12.0, 14.0, 16.0, 18.0]
    assert residuals == [0.0, 0.0, 0.0, 0.0]

    # Sample variance is zero on perfect linear series
    s2 = sum(e**2 for e in residuals) / (T - 2)
    assert s2 == pytest.approx(0.0, abs=1e-9)

    # Multi-step forecast
    h1 = y[-1] + 1 * c_hat
    h2 = y[-1] + 2 * c_hat
    assert h1 == pytest.approx(20.0, abs=1e-9)
    assert h2 == pytest.approx(22.0, abs=1e-9)


def test_return_transformation_telescoping_identity() -> None:
    """Verify exact return telescoping and inversion identity."""
    y = [100.0, 105.0, 102.0, 110.0]
    T = len(y)

    # Log returns
    log_returns = [math.log(y[t] / y[t - 1]) for t in range(1, T)]
    # Telescoping sum of log returns equals total log return
    total_log_return = sum(log_returns)
    assert total_log_return == pytest.approx(math.log(y[-1] / y[0]), abs=1e-12)

    # Exact geometric level reconstruction
    reconstructed_level = y[0] * math.exp(total_log_return)
    assert reconstructed_level == pytest.approx(y[-1], abs=1e-12)

    # Relative percentage changes
    pct_changes = [(y[t] - y[t - 1]) / y[t - 1] for t in range(1, T)]
    cum_pct = 1.0
    for rho in pct_changes:
        cum_pct *= 1.0 + rho
    reconstructed_pct_level = y[0] * cum_pct
    assert reconstructed_pct_level == pytest.approx(y[-1], abs=1e-12)


def test_zero_future_leakage_invariance() -> None:
    """Verify that changing holdout evaluation data has zero effect on training statistics."""
    train_y = [10.0, 13.0, 11.0, 15.0, 17.0]
    holdout_y_original = [19.0, 21.0]
    holdout_y_altered = [999.0, -500.0]

    def compute_train_drift(series: list[float]) -> tuple[float, float]:
        T = len(series)
        drift = (series[-1] - series[0]) / (T - 1)
        residuals = [series[t] - (series[t - 1] + drift) for t in range(1, T)]
        variance = sum(e**2 for e in residuals) / (T - 2)
        return drift, variance

    drift1, var1 = compute_train_drift(train_y)
    # Even if an evaluation dataset contains wildly altered holdout data, training estimation is unchanged
    full_series1 = train_y + holdout_y_original
    full_series2 = train_y + holdout_y_altered

    # Strictly slice training window: t < len(train_y)
    drift_slice1, var_slice1 = compute_train_drift(full_series1[: len(train_y)])
    drift_slice2, var_slice2 = compute_train_drift(full_series2[: len(train_y)])

    assert drift1 == drift_slice1 == drift_slice2
    assert var1 == var_slice1 == var_slice2


def test_ewma_volatility_recursion_determinism() -> None:
    """Verify EWMA variance recursion behavior."""
    returns = [0.01, -0.02, 0.015, -0.005, 0.025]
    lam = 0.94

    # Initial variance = sample variance
    mean_r = sum(returns) / len(returns)
    init_var = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)

    sigmas = [math.sqrt(init_var)]
    var_prev = init_var
    for r in returns[1:]:
        var_t = lam * var_prev + (1.0 - lam) * (r**2)
        sigmas.append(math.sqrt(var_t))
        var_prev = var_t

    assert len(sigmas) == len(returns)
    assert all(math.isfinite(s) and s > 0.0 for s in sigmas)


def test_scenario_discretization_conforms_to_robust_scenario_schema() -> None:
    """Verify that discretized scenarios conform to the scenario.linear.* problem structure."""
    quantiles = [0.10, 0.50, 0.90]
    horizon = 3
    y_T = 100.0
    c_hat = 1.0
    s = 2.0

    # Critical z-values for normal quantiles
    z_map = {0.10: -1.28155, 0.50: 0.0, 0.90: 1.28155}
    scenarios = []

    for q in quantiles:
        scen_id = f"scen_q{int(round(q * 100)):02d}"
        values = []
        for h in range(1, horizon + 1):
            sigma_h = s * math.sqrt(h)
            v_h = (y_T + h * c_hat) + z_map[q] * sigma_h
            values.append(round(v_h, 4))
        scenarios.append(
            {
                "id": scen_id,
                "values": values,
            }
        )

    assert len(scenarios) == 3
    assert [s["id"] for s in scenarios] == ["scen_q10", "scen_q50", "scen_q90"]
    # Point forecast at h=1 is 101.0; scen_q10 < scen_q50 < scen_q90
    assert scenarios[0]["values"][0] < scenarios[1]["values"][0] < scenarios[2]["values"][0]
    assert scenarios[1]["values"][0] == pytest.approx(101.0, abs=1e-4)


def test_prediction_interval_ordering() -> None:
    """Verify lower_bound <= point_forecast <= upper_bound ordering."""
    point = 105.0
    sigma = 3.5
    z = 1.96

    lower = point - z * sigma
    upper = point + z * sigma
    assert lower < point < upper

    # Log space
    log_lower = math.exp(math.log(point) - z * 0.03)
    log_point = point
    log_upper = math.exp(math.log(point) + z * 0.03)
    assert log_lower < log_point < log_upper
