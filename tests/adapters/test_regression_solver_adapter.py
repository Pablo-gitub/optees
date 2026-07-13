from __future__ import annotations

from typing import Any, Dict

from optees.data.adapters.regression.numpy_regression_adapter import NumpyRegressionAdapter


def test_adapter_exposes_the_local_regression_result(monkeypatch) -> None:
    expected = {"status": "Trained", "intercept": 2.0, "coefficients": {"size": 3.0}}

    def fake_solve(problem: Dict[str, Any]) -> Dict[str, Any]:
        assert problem["method"] == "OLS"
        return expected

    monkeypatch.setattr(
        "optees.data.adapters.regression.numpy_regression_adapter.solve_regression",
        fake_solve,
    )

    assert NumpyRegressionAdapter().solve({"method": "OLS"}) == expected


def test_adapter_maps_utility_failures_to_a_failed_training_result(monkeypatch) -> None:
    def fail(_: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("numerical failure")

    monkeypatch.setattr(
        "optees.data.adapters.regression.numpy_regression_adapter.solve_regression",
        fail,
    )

    result = NumpyRegressionAdapter().solve({})

    assert result["status"] == "Failed"
    assert result["coefficients"] == {}
    assert result["extras"]["message"] == "numerical failure"
