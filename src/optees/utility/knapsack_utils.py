# src/optees/utility/knapsack_utils.py
"""
0/1 Knapsack utilities.

Public API
----------
- solve_knapsack_01(values, weights, capacity) -> (best_value, selected_indices)

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
from typing import List, Tuple


__all__ = ["solve_knapsack_01"]


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
