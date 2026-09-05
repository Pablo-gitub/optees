"""Candidate-design counterexamples, not production forecasting validation."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

CONTRACT_FILE = (
    Path(__file__).resolve().parents[2] / "docs/contracts/targeted-forecasting-contract.md"
)


def test_contract_does_not_authorize_an_unreviewed_runtime() -> None:
    text = CONTRACT_FILE.read_text(encoding="utf-8")
    assert "NOT satisfied" in text
    assert "not a frozen public contract" in text
    assert "No engine, new capability, or UI work is authorized" in text


def test_transformed_history_needs_four_levels_for_drift_variance() -> None:
    for level_count, degrees_of_freedom in [(3, 0), (4, 1)]:
        returns_count = level_count - 1
        assert returns_count - 2 == degrees_of_freedom


def test_two_step_cumulative_return_variance_is_not_marginal_variance() -> None:
    # Independent unit shocks: return errors e1 and e1+e2 have covariance 1.
    shocks = [(a, b) for a in (-1, 1) for b in (-1, 1)]
    marginal = [a + b for a, b in shocks]
    cumulative = [2 * a + b for a, b in shocks]
    assert sum(x * x for x in marginal) / 4 == 2
    assert sum(x * x for x in cumulative) / 4 == 5
    # Estimation uncertainty also accumulates drift weights: (1+2)^2.
    n = 5
    assert 5 + 9 / (n - 1) == 7.25
    assert 2 + 4 / (n - 1) == 3


def test_exp_of_log_mean_is_not_arithmetic_level_mean() -> None:
    # Exact symmetric two-point example; no distributional approximation.
    levels = [100 * math.exp(-0.2), 100 * math.exp(0.2)]
    geometric = math.sqrt(levels[0] * levels[1])
    assert geometric == pytest.approx(100)
    assert sum(levels) / 2 > geometric


def test_full_sample_ewma_seed_depends_on_future_suffix() -> None:
    def sample_variance(values: list[float]) -> float:
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / (len(values) - 1)

    assert sample_variance([0.01, 0.02, 0.03]) != sample_variance([0.01, 0.02, 10.0])


def test_candidate_causal_ewma_prefix_is_suffix_invariant() -> None:
    def candidate(values: list[float]) -> list[float]:
        variance = values[0] ** 2
        result = [variance]
        for value in values[1:]:
            variance = 0.94 * variance + 0.06 * value**2
            result.append(variance)
        return result

    assert candidate([0.01, -0.02, 0.03])[:2] == candidate([0.01, -0.02, 10.0])[:2]


def test_rounded_quantile_identifiers_collide() -> None:
    quantiles = [0.101, 0.104]
    assert len(set(quantiles)) == 2
    assert len({f"scen_q{int(round(q * 100)):02d}" for q in quantiles}) == 1


def test_return_reconstruction_identity_is_only_arithmetic_evidence() -> None:
    levels = [100.0, 105.0, 102.0, 110.0]
    returns = [math.log(b / a) for a, b in zip(levels, levels[1:])]
    assert levels[0] * math.exp(sum(returns)) == pytest.approx(levels[-1])
