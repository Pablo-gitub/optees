# 0/1 Knapsack - Problem Description

The 0/1 knapsack problem is a classic operations research model. You have a
limited capacity and must decide which items to include.

The defining rule is:

```text
each item is selected or excluded
```

You cannot take 30% of an item. That is the `0/1` part.

---

## Mathematical Form

For each item `i`, you know:

| Symbol | Meaning |
|---|---|
| `v_i` | item value |
| `w_i` | item weight |
| `C` | maximum capacity |

Introduce a binary variable:

```text
x_i = 1  item i is selected
x_i = 0  item i is excluded
```

The model is:

```text
max z = sum_i v_i x_i

subject to:
  sum_i w_i x_i <= C

x_i in {0, 1}
```

The objective maximizes selected value. The constraint keeps total selected
weight within capacity.

---

## Why Value/Weight Sorting Is Not Enough

Sorting by `value / weight` is optimal for fractional knapsack, where fractions
of items are allowed. It is not guaranteed optimal for 0/1 knapsack.

In the 0/1 model, an item enters completely or does not enter at all, so the
best solution depends on how weights combine.

Example:

```text
capacity = 10

A: value 60, weight 10
B: value 35, weight 6
C: value 30, weight 4
```

The combination `B + C` has weight 10 and value 65, so it beats `A`.

---

## Algorithm Implemented in Optees

The first implementation uses exact dynamic programming.

It builds a table:

```text
dp[i][c]
```

where:

- `i` is the number of items considered;
- `c` is a capacity from `0` to `C`;
- `dp[i][c]` is the best value reachable with the first `i` items and capacity
  `c`.

For each item there are two choices:

```text
1. exclude the item
2. include the item, if it fits
```

The recurrence is:

```text
dp[i][c] = max(
    dp[i-1][c],
    dp[i-1][c - w_i] + v_i
)
```

The second option is available only when `w_i <= c`.

At the end, the optimal value is:

```text
dp[n][C]
```

Optees then reconstructs the selected items by walking backward through the
table.

---

## Complexity

Dynamic programming is exact, but its complexity is:

```text
time  O(n * C)
space O(n * C)
```

This is pseudo-polynomial complexity: it depends on the numeric value of
capacity, not only on the number of digits used to write it.

For this reason, Optees applies a practical limit to the DP table size. If an
instance is too large for this implementation, the solution is reported as
`NotSolved` with a diagnostic message.

---

## Relationship with MILP

0/1 knapsack is also a special MILP:

```text
max v^T x
subject to w^T x <= C
x_i in {0, 1}
```

A MILP solver can solve it, but a dedicated Knapsack view is faster and clearer
when the problem is exactly: items, values, weights and capacity.

