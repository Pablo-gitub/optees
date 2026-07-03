# Knapsack - Problem Description

Knapsack is a family of optimization models where limited resources must be
allocated by selecting items or item quantities. The common structure is:

```text
maximize value
subject to one or more capacities
```

The variants differ in the domain of the decision variables.

---

## General Form

For each item `i`, you know:

| Symbol | Meaning |
|---|---|
| `v_i` | unit value |
| `w_i` | single-resource consumption |
| `a_{i,r}` | consumption of resource `r` in the multi-dimensional case |
| `C` | single capacity |
| `C_r` | capacity of resource `r` |

The variable `x_i` states how much of item `i` is selected. Its domain depends
on the variant:

| Variant | Domain |
|---|---|
| 0/1 | `x_i in {0, 1}` |
| Bounded | `x_i in {0, ..., u_i}` |
| Unbounded | `x_i in {0, 1, 2, ...}` |
| Fractional | `0 <= x_i <= 1` or `0 <= x_i <= u_i` |

---

## 0/1 Knapsack

The 0/1 model is:

```text
max sum_i v_i x_i

subject to:
  sum_i w_i x_i <= C

x_i in {0, 1}
```

Each item enters entirely or not at all. You cannot take 30% of an item. This
variant fits project selection, package loading and feature selection under a
budget.

### Algorithm

Optees uses exact dynamic programming:

```text
dp[i][c] = best value using the first i items and capacity c
```

For each item, it compares:

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

The complexity is pseudo-polynomial:

```text
time  O(n * C)
space O(n * C)
```

---

## Bounded Knapsack

Bounded knapsack allows several copies of an item, up to a maximum limit:

```text
max sum_i v_i x_i

subject to:
  sum_i w_i x_i <= C

x_i in {0, 1, ..., u_i}
```

The limit `u_i` can represent stock, maximum lots or an accepted upper quantity.

### Algorithm

Optees uses dynamic programming and tests every admissible quantity from `0` to
`u_i` for each item. It is exact for integer weights and capacity, but can grow
quickly when capacities or limits are large.

---

## Unbounded Knapsack

In unbounded knapsack each item represents a repeatable type:

```text
x_i in {0, 1, 2, ...}
```

The model is:

```text
max sum_i v_i x_i

subject to:
  sum_i w_i x_i <= C

x_i non-negative integer
```

It is useful for standard lots, repeatable material cuts and replicable
packages.

### Algorithm

Optees uses dynamic programming while allowing the same item type to be reused.
The solver is exact for integer weights and capacity.

---

## Fractional Knapsack

Fractional knapsack allows a fraction of each item:

```text
0 <= x_i <= 1
```

The model is:

```text
max sum_i v_i x_i

subject to:
  sum_i w_i x_i <= C
  0 <= x_i <= 1
```

In the classic single-resource case, sorting by density `v_i / w_i` is optimal:
take the highest density first and fill the remaining capacity.

This property does not automatically hold when there are several resources.

---

## Multi-dimensional Knapsack

In multi-dimensional knapsack, every item consumes a vector of resources:

```text
max sum_i v_i x_i

subject to:
  sum_i a_{i,r} x_i <= C_r    for every resource r
```

Examples of resources:

- weight;
- volume;
- machine hours;
- budget;
- energy;
- memory.

The 0/1 version uses:

```text
x_i in {0, 1}
```

Optees solves it with a dedicated branch-and-bound: it explores binary choices,
prunes branches that violate a resource and keeps the best feasible solution.

---

## Multi-dimensional with Variable Domain

In the Multi-dimensional view you can choose the quantity domain:

| Domain | Model |
|---|---|
| 0/1 | `x_i in {0, 1}` |
| Bounded integer | `x_i in {0, ..., u_i}` |
| Unbounded integer | `x_i integer, x_i >= 0` |
| Fractional | `x_i continuous, 0 <= x_i <= u_i` |

Integer variants are mapped to a MILP. The fractional variant is mapped to a
continuous linear model. This matters: with several resources, value/weight
greedy is not enough because there is no single notion of "weight".

---

## Relationship with MILP and LP

Many Knapsack variants are special cases of LP or MILP:

```text
max v^T x
subject to A x <= b
x_i binary, integer or continuous
```

The Knapsack view is more didactic because it uses the language of the problem:
items, values, capacities, resources and quantities. The MILP view remains more
general when you need arbitrary constraints outside the Knapsack structure.

---

## Reading the Solution

| Field | Meaning |
|---|---|
| Status | `Optimal` when the solution is proven optimal |
| Best value | total value of the solution |
| Selected | item included in the 0/1 case |
| Quantity | number of copies or continuous quantity |
| Fraction | selected share in single-resource fractional knapsack |
| Resource usage | total consumption of each capacity |
| Remaining | unused capacity |

If status is `Optimal`, the displayed solution is the best possible solution for
the model entered.
