"""Safe scalar expressions for continuous nonlinear optimization.

This module accepts a deliberately small mathematical language. It parses the
input with :mod:`ast`, validates every node, and evaluates the resulting tree
recursively. It never compiles or executes user text with ``eval`` or ``exec``.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass
from typing import Callable, Mapping


class NLPExpressionError(ValueError):
    """Base error for an invalid or non-evaluable NLP expression."""


class NLPExpressionSyntaxError(NLPExpressionError):
    """Raised when an expression uses syntax outside the supported language."""


class NLPExpressionEvaluationError(NLPExpressionError):
    """Raised when valid syntax cannot produce a finite scalar value."""


_UnaryOperator = Callable[[float], float]
_BinaryOperator = Callable[[float, float], float]

_UNARY_OPERATORS: dict[type[ast.unaryop], _UnaryOperator] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_BINARY_OPERATORS: dict[type[ast.operator], _BinaryOperator] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "abs": abs,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "sqrt": math.sqrt,
}
ALLOWED_FUNCTION_NAMES = frozenset(_FUNCTIONS)
_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class SafeNLPExpression:
    """A validated objective expression bound to a set of variable names."""

    source: str
    variable_names: tuple[str, ...]
    _tree: ast.Expression

    @classmethod
    def compile(
        cls,
        source: object,
        variable_names: tuple[str, ...] | list[str],
    ) -> "SafeNLPExpression":
        if not isinstance(source, str) or not source.strip():
            raise NLPExpressionSyntaxError("objective expression must be a non-empty string")

        names = tuple(variable_names)
        if len(names) != len(set(names)):
            raise NLPExpressionSyntaxError("variable names must be unique")
        if any(
            not isinstance(name, str) or not _VARIABLE_NAME.fullmatch(name)
            for name in names
        ):
            raise NLPExpressionSyntaxError("variable names must be valid identifiers")
        if any(name in ALLOWED_FUNCTION_NAMES for name in names):
            raise NLPExpressionSyntaxError("variable names must not shadow supported functions")

        try:
            tree = ast.parse(source.strip(), mode="eval")
        except SyntaxError as exc:
            location = f" at column {exc.offset}" if exc.offset else ""
            raise NLPExpressionSyntaxError(f"invalid objective expression{location}") from exc

        _ExpressionValidator(frozenset(names)).visit(tree)
        return cls(source=source.strip(), variable_names=names, _tree=tree)

    def evaluate(self, values: Mapping[str, object]) -> float:
        missing = [name for name in self.variable_names if name not in values]
        if missing:
            raise NLPExpressionEvaluationError(
                f"missing value for variable {missing[0]!r}"
            )

        normalized_values = {
            name: _as_finite_float(values[name], f"value for variable {name!r}")
            for name in self.variable_names
        }
        return _evaluate_node(self._tree.body, normalized_values)


class _ExpressionValidator(ast.NodeVisitor):
    def __init__(self, variable_names: frozenset[str]) -> None:
        self._variable_names = variable_names

    def generic_visit(self, node: ast.AST) -> None:
        raise NLPExpressionSyntaxError(
            f"unsupported syntax: {type(node).__name__}"
        )

    def visit_Expression(self, node: ast.Expression) -> None:
        self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> None:
        _as_finite_float(node.value, "numeric constant")

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self._variable_names:
            raise NLPExpressionSyntaxError(f"unknown variable {node.id!r}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if type(node.op) not in _UNARY_OPERATORS:
            raise NLPExpressionSyntaxError(
                f"unsupported unary operator: {type(node.op).__name__}"
            )
        self.visit(node.operand)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if type(node.op) not in _BINARY_OPERATORS:
            raise NLPExpressionSyntaxError(
                f"unsupported binary operator: {type(node.op).__name__}"
            )
        self.visit(node.left)
        self.visit(node.right)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise NLPExpressionSyntaxError("unsupported function call")
        if node.keywords or len(node.args) != 1:
            raise NLPExpressionSyntaxError(
                f"function {node.func.id!r} requires exactly one positional argument"
            )
        self.visit(node.args[0])


def _evaluate_node(node: ast.AST, values: Mapping[str, float]) -> float:
    try:
        if isinstance(node, ast.Constant):
            return _as_finite_float(node.value, "numeric constant")
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.UnaryOp):
            operation = _UNARY_OPERATORS[type(node.op)]
            return _as_finite_float(operation(_evaluate_node(node.operand, values)), "result")
        if isinstance(node, ast.BinOp):
            operation = _BINARY_OPERATORS[type(node.op)]
            left = _evaluate_node(node.left, values)
            right = _evaluate_node(node.right, values)
            return _as_finite_float(operation(left, right), "result")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = _FUNCTIONS[node.func.id]
            argument = _evaluate_node(node.args[0], values)
            return _as_finite_float(function(argument), "result")
    except (ArithmeticError, OverflowError, ValueError, KeyError) as exc:
        raise NLPExpressionEvaluationError(f"objective evaluation failed: {exc}") from exc

    raise NLPExpressionEvaluationError(f"unsupported validated node: {type(node).__name__}")


def _as_finite_float(value: object, description: str) -> float:
    if isinstance(value, bool):
        raise NLPExpressionEvaluationError(f"{description} must be a finite number")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise NLPExpressionEvaluationError(f"{description} must be a finite number") from exc
    if not math.isfinite(result):
        raise NLPExpressionEvaluationError(f"{description} must be a finite number")
    return result
