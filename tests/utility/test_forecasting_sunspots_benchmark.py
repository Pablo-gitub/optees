from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path

import pytest
import statsmodels

from optees.application.contracts.capability_ids import FORECASTING_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import create_local_optimization_service


SUNSPOTS_SHA256 = "f67889b1d9002cd5227f0e0ef54e35b419cdd85a31279adef6f73fb41e5c0a9b"


def _sunspots_csv() -> Path:
    return (
        Path(statsmodels.__file__).resolve().parent
        / "datasets"
        / "sunspots"
        / "sunspots.csv"
    )


def _problem() -> dict[str, object]:
    dataset = _sunspots_csv()
    observations: list[dict[str, object]] = []
    with dataset.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            year = int(float(row["YEAR"]))
            observations.append(
                {
                    "timestamp": datetime(year, 1, 1).isoformat(),
                    "value": float(row["SUNACTIVITY"]),
                }
            )
    return {
        "version": "1",
        "problem_type": "univariate_forecasting",
        "target_name": "annual_sunspot_activity",
        "frequency": "yearly",
        "horizon": 11,
        "method": "seasonal_naive",
        "season_length": 11,
        "missing_period_policy": "reject",
        "observations": observations,
        "evaluation": {"strategy": "holdout", "holdout_size": 22},
    }


def test_public_sunspots_seasonal_naive_benchmark() -> None:
    dataset = _sunspots_csv()
    assert hashlib.sha256(dataset.read_bytes()).hexdigest() == SUNSPOTS_SHA256

    outcome = create_local_optimization_service().solve(
        FORECASTING_CAPABILITY_ID,
        _problem(),
    )

    assert isinstance(outcome, ExecutionEnvelope)
    assert outcome.validation is not None
    assert outcome.validation.status.value == "verified"
    assert outcome.result["metrics"] == pytest.approx(
        {
            "mae": 38.47272727272727,
            "rmse": 45.02725437291992,
            "mape": 98.8100019183094,
            "mase": 1.7262160400683966,
        }
    )
    future = [
        point["predicted"]
        for point in outcome.result["points"]
        if point["segment"] == "future"
    ]
    assert future == pytest.approx(
        (64.3, 93.3, 119.6, 111.0, 104.0, 63.7, 40.4, 29.8, 15.2, 7.5, 2.9)
    )
