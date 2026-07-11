from __future__ import annotations

import math

import pytest

from optees.utility.nlp_expression import (
    NLPExpressionEvaluationError,
    NLPExpressionSyntaxError,
    SafeNLPExpression,
)


def test_evaluates_supported_arithmetic_and_functions() -> None:
    expression = SafeNLPExpression.compile(
        "(x1 - 2)**2 + sqrt(x2) + sin(x1) + abs(-x2)",
        ["x1", "x2"],
    )

    actual = expression.evaluate({"x1": 2.0, "x2": 4.0})

    assert actual == pytest.approx(2.0 + math.sin(2.0) + 4.0)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("x1 + missing", "unknown variable"),
        ("x1 // 2", "unsupported binary operator"),
        ("x1 > 0", "unsupported syntax"),
        ("__import__('os').system('whoami')", "unsupported function call"),
        ("(lambda value: value)(x1)", "unsupported function call"),
        ("sin(x1, x2)", "requires exactly one positional argument"),
        ("1 if x1 else 0", "unsupported syntax"),
    ],
)
def test_rejects_unsafe_or_unsupported_syntax(source: str, message: str) -> None:
    with pytest.raises(NLPExpressionSyntaxError, match=message):
        SafeNLPExpression.compile(source, ["x1", "x2"])


def test_rejects_missing_variable_value() -> None:
    expression = SafeNLPExpression.compile("x1 + x2", ["x1", "x2"])

    with pytest.raises(NLPExpressionEvaluationError, match="missing value"):
        expression.evaluate({"x1": 1.0})


@pytest.mark.parametrize("source", ["log(-1)", "sqrt(-1)", "exp(10000)", "x1 / 0"])
def test_rejects_invalid_or_non_finite_evaluations(source: str) -> None:
    expression = SafeNLPExpression.compile(source, ["x1"])

    with pytest.raises(NLPExpressionEvaluationError):
        expression.evaluate({"x1": 1.0})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
def test_rejects_non_finite_or_boolean_variable_values(value: object) -> None:
    expression = SafeNLPExpression.compile("x1", ["x1"])

    with pytest.raises(NLPExpressionEvaluationError, match="finite number"):
        expression.evaluate({"x1": value})
