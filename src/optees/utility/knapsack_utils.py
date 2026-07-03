# src/optees/utility/knapsack_utils.py
"""
Knapsack utilities.

Public API
----------
- solve_knapsack_01(values, weights, capacity) -> (best_value, selected_indices)
- solve_bounded_knapsack(values, weights, max_quantities, capacity)
  -> (best_value, quantities)
- solve_unbounded_knapsack(values, weights, capacity) -> (best_value, quantities)
- solve_fractional_knapsack(values, weights, capacity) -> (best_value, fractions)

Design
------
- Pure-Python dynamic programming with a 2D DP table (O(n * capacity) time
  and O(n * capacity) memory) for straightforward and deterministic
  reconstruction.
- Deterministic reconstruction: when ties occur, the selection follows the
  natural DP decisions (stable across runs), which is desirable for tests.

Caveats
-------
- This algorithm is pseudo-polynomial in the capacity. For very large
  capacities (e.g., > 1e6), consider an alternative approach (value-scaled
  DP, meet-in-the-middle for small n, or a MIP solver such as OR-Tools).
"""

from __future__ import annotations
from math import isfinite
from typing import List, Tuple


__all__ = [
    "solve_knapsack_01",
    "solve_bounded_knapsack",
    "solve_unbounded_knapsack",
    "solve_fractional_knapsack",
]


def solve_knapsack_01(
    values: List[float],
    weights: List[int],
    capacity: int,
) -> Tuple[float, List[int]]:
    """
    Solve the 0/1 knapsack problem via dynamic programming.

    Parameters
    ----------
    values : list[float]
        Profit/value per item. Length n.
    weights : list[int]
        Non-negative integer weight per item. Length n. Each entry must be an
        integer (or a float exactly equal to an integer, e.g. 2.0).
    capacity : int
        Non-negative integer capacity of the knapsack.

    Returns
    -------
    best_value : float
        Optimal objective value.
    selected_indices : list[int]
        Indices of chosen items in ascending order (deterministic).

    Raises
    ------
    ValueError
        - If `values` and `weights` have different lengths.
        - If `capacity` is negative or not an integer (or integer-like float).
        - If any weight is negative or not integer (or integer-like float).

    Notes
    -----
    - Time complexity:  O(n * capacity)
    - Space complexity: O(n * capacity)  (2D table used to keep the
      reconstruction simple and predictable).
    - The DP uses standard floating-point arithmetic on `values`. The
      backtracking checks `dp[i][w] != dp[i-1][w]` to detect whether an item
      was taken; if you pass values with pathological floating-point noise,
      consider pre-rounding your values or introducing a small tolerance
      in that comparison.
    """
    # ---------- Basic validation ----------
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length.")
    if capacity < 0:
        raise ValueError("capacity must be >= 0.")

    n = len(values)
    if n == 0 or capacity == 0:
        return 0.0, []

    # Ensure capacity is an int (or an integer-like float).
    if not isinstance(capacity, int):
        if isinstance(capacity, float) and capacity.is_integer():
            capacity = int(capacity)
        else:
            raise ValueError("capacity must be an integer.")

    # Ensure weights are non-negative integers (allow integer-like floats).
    w_ints: List[int] = []
    for w in weights:
        if isinstance(w, int):
            if w < 0:
                raise ValueError("weights must be non-negative.")
            w_ints.append(w)
        elif isinstance(w, float):
            if not w.is_integer():
                raise ValueError("weights must be integers.")
            iw = int(w)
            if iw < 0:
                raise ValueError("weights must be non-negative.")
            w_ints.append(iw)
        else:
            raise ValueError("weights must be integers.")

    # ---------- DP table ----------
    # dp[i][w] = best value attainable using the first i items with capacity w.
    # We allocate (n+1) x (capacity+1) for a simple and readable backtrack.
    dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]

    # Fill the table row by row (items 1..n).
    for i in range(1, n + 1):
        v_i = float(values[i - 1])  # value of item i-1
        w_i = w_ints[i - 1]         # weight of item i-1
        for w in range(0, capacity + 1):
            # Option 1: do not take item i-1
            best = dp[i - 1][w]
            # Option 2: take item i-1 if it fits
            if w_i <= w:
                cand = dp[i - 1][w - w_i] + v_i
                if cand > best:
                    best = cand
            dp[i][w] = best

    best_value = dp[n][capacity]

    # ---------- Reconstruction ----------
    # Walk back from (n, capacity) and detect which items were taken.
    # Tie-breaking is deterministic due to strict '>' in the DP update.
    selected: List[int] = []
    w = capacity
    for i in range(n, 0, -1):
        # If the value changed when adding item (i-1), then it was taken.
        if dp[i][w] != dp[i - 1][w]:
            selected.append(i - 1)
            w -= w_ints[i - 1]
    selected.reverse()

    return float(best_value), selected


def solve_bounded_knapsack(
    values: List[float],
    weights: List[int],
    max_quantities: List[int],
    capacity: int,
) -> Tuple[float, List[int]]:
    """Solve the bounded knapsack problem via dynamic programming.

    The model is:

        max sum_i value_i * x_i
        s.t. sum_i weight_i * x_i <= capacity
             x_i in {0, 1, ..., max_quantity_i}

    Returns the optimal value and one deterministic optimal quantity vector.
    Tie-breaking keeps the first quantity that reaches the best value, so lower
    quantities are preferred when alternatives are exactly tied.
    """
    if len(values) != len(weights) or len(values) != len(max_quantities):
        raise ValueError("values, weights and max_quantities must have the same length.")

    capacity_int = _normalize_non_negative_int(capacity, "capacity")
    weights_int = [
        _normalize_non_negative_int(weight, "weights")
        for weight in weights
    ]
    quantities_int = [
        _normalize_non_negative_int(quantity, "max_quantities")
        for quantity in max_quantities
    ]

    n = len(values)
    if n == 0:
        return 0.0, []

    dp = [[0.0] * (capacity_int + 1) for _ in range(n + 1)]
    choice = [[0] * (capacity_int + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        value_i = float(values[i - 1])
        weight_i = weights_int[i - 1]
        max_q_i = quantities_int[i - 1]

        for cap in range(0, capacity_int + 1):
            best = dp[i - 1][cap]
            best_q = 0

            if weight_i == 0:
                max_feasible_q = max_q_i
            else:
                max_feasible_q = min(max_q_i, cap // weight_i)

            for quantity in range(1, max_feasible_q + 1):
                candidate = dp[i - 1][cap - quantity * weight_i] + quantity * value_i
                if candidate > best:
                    best = candidate
                    best_q = quantity

            dp[i][cap] = best
            choice[i][cap] = best_q

    quantities = [0] * n
    cap = capacity_int
    for i in range(n, 0, -1):
        quantity = choice[i][cap]
        quantities[i - 1] = quantity
        cap -= quantity * weights_int[i - 1]

    return float(dp[n][capacity_int]), quantities


def solve_unbounded_knapsack(
    values: List[float],
    weights: List[int],
    capacity: int,
) -> Tuple[float, List[int]]:
    """Solve the unbounded knapsack problem via dynamic programming.

    The model is:

        max sum_i value_i * x_i
        s.t. sum_i weight_i * x_i <= capacity
             x_i in {0, 1, 2, ...}

    With positive weights the problem is finite and can be solved by a 1D DP:
    ``dp[c]`` stores the best value attainable with capacity ``c``. Because the
    same item may be reused, transitions read from the current DP row:
    ``dp[c - weight_i] + value_i``. If an item has zero weight and positive
    value, the mathematical objective is unbounded.
    """
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length.")

    capacity_int = _normalize_non_negative_int(capacity, "capacity")
    weights_int = [
        _normalize_non_negative_int(weight, "weights")
        for weight in weights
    ]
    values_float = [float(value) for value in values]

    n = len(values_float)
    if n == 0:
        return 0.0, []

    if any(weight == 0 and value > 0 for value, weight in zip(values_float, weights_int)):
        raise ValueError("problem is unbounded: zero-weight item with positive value")

    dp = [0.0] * (capacity_int + 1)
    choice = [-1] * (capacity_int + 1)

    for cap in range(0, capacity_int + 1):
        for index, (value_i, weight_i) in enumerate(zip(values_float, weights_int)):
            if weight_i <= 0 or weight_i > cap:
                continue
            candidate = dp[cap - weight_i] + value_i
            if candidate > dp[cap]:
                dp[cap] = candidate
                choice[cap] = index

    quantities = [0] * n
    cap = capacity_int
    while cap > 0 and choice[cap] != -1:
        index = choice[cap]
        quantities[index] += 1
        cap -= weights_int[index]

    return float(dp[capacity_int]), quantities


def solve_fractional_knapsack(
    values: List[float],
    weights: List[float],
    capacity: float,
) -> Tuple[float, List[float]]:
    """Solve the classic single-capacity fractional knapsack problem.

    The model is:

        max sum_i value_i * x_i
        s.t. sum_i weight_i * x_i <= capacity
             0 <= x_i <= 1

    Because the decision variables are continuous fractions, the exchange
    argument from operations research applies: an optimal solution takes items
    in non-increasing value density ``value_i / weight_i`` and, if needed,
    takes one final fractional item to exactly fill the remaining capacity.
    """
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length.")

    capacity_float = _normalize_non_negative_float(capacity, "capacity")
    values_float = [
        _normalize_non_negative_float(value, "values")
        for value in values
    ]
    weights_float = [
        _normalize_positive_float(weight, "weights")
        for weight in weights
    ]

    n = len(values_float)
    if n == 0:
        return 0.0, []

    fractions = [0.0] * n
    objective = 0.0
    remaining = capacity_float
    ordered = sorted(
        range(n),
        key=lambda i: (-(values_float[i] / weights_float[i]), i),
    )

    for index in ordered:
        if remaining <= 0:
            break

        weight = weights_float[index]
        value = values_float[index]
        fraction = 1.0 if weight <= remaining else remaining / weight
        fractions[index] = fraction
        objective += value * fraction
        remaining -= weight * fraction

    return float(objective), fractions


def _normalize_non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a non-negative integer")
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, float) and value.is_integer():
        normalized = int(value)
    else:
        raise ValueError(f"{label} must be a non-negative integer")

    if normalized < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return normalized


def _normalize_non_negative_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite non-negative number") from exc
    if not isfinite(normalized) or normalized < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    return normalized


def _normalize_positive_float(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite positive number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite positive number") from exc
    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return normalized
