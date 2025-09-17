# src/optees/utility/knapsack_utils.py
"""
0/1 Knapsack utilities.

Public API
----------
- solve_knapsack_01(values, weights, capacity) -> (best_value, selected_indices)

Design
------
- Pure-Python dynamic programming (O(n * capacity) time and memory).
- Deterministic reconstruction: when ties occur, it prefers the solution
  found by standard DP (which is consistent and stable for tests).
"""

from __future__ import annotations
from typing import List, Tuple
import math


__all__ = ["solve_knapsack_01"]


def solve_knapsack_01(
    values: List[float],
    weights: List[int],
    capacity: int,
) -> Tuple[float, List[int]]:
    """
    Solve the 0/1 knapsack problem.

    Parameters
    ----------
    values : list of float
        Item profits/values, one per item.
    weights : list of int
        Item weights (non-negative integers), one per item.
    capacity : int
        Knapsack capacity (non-negative integer).

    Returns
    -------
    (best_value, selected_indices)
        best_value : float
            Optimal objective value.
        selected_indices : list[int]
            Indices of chosen items (sorted ascending).

    Notes
    -----
    - This is a baseline DP (O(n * capacity)) with a 2D table to keep
      the reconstruction straightforward and predictable.
    - Input validation is minimal but catches the most common mistakes.
    """
    # --- basic validation ---
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length.")
    if capacity < 0:
        raise ValueError("capacity must be >= 0.")
    n = len(values)
    if n == 0 or capacity == 0:
        return 0.0, []

    # Ensure weights/capacity are integers and non-negative
    if any((w < 0) for w in weights):
        raise ValueError("weights must be non-negative.")
    if not isinstance(capacity, int):
        # allow floats that are integers (e.g., 10.0)
        if isinstance(capacity, float) and capacity.is_integer():
            capacity = int(capacity)
        else:
            raise ValueError("capacity must be an integer.")
    # normalize potential float-ints in weights (e.g., 2.0)
    w_ints: List[int] = []
    for w in weights:
        if isinstance(w, float):
            if not w.is_integer():
                raise ValueError("weights must be integers.")
            w_ints.append(int(w))
        elif isinstance(w, int):
            w_ints.append(w)
        else:
            raise ValueError("weights must be integers.")

    # --- DP table: dp[i][w] = best value using first i items within capacity w ---
    dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        v_i = float(values[i - 1])
        w_i = w_ints[i - 1]
        for w in range(0, capacity + 1):
            # not take item i-1
            best = dp[i - 1][w]
            # take item i-1 if it fits
            if w_i <= w:
                cand = dp[i - 1][w - w_i] + v_i
                if cand > best:
                    best = cand
            dp[i][w] = best

    best_value = dp[n][capacity]

    # --- reconstruction (stable) ---
    selected: List[int] = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            # item i-1 was taken
            selected.append(i - 1)
            w -= w_ints[i - 1]
    selected.reverse()

    return float(best_value), selected
