# 0/1 Knapsack Examples

The 0/1 knapsack problem is useful when you must choose a subset of items. Each
item can be selected once or excluded.

The goal is:

```text
maximize total value
without exceeding available capacity
```

---

## Example 1 - Teaching Instance

Capacity is `5`. Available items are:

| Item | Value | Weight |
|---|---:|---:|
| A | 3 | 2 |
| B | 4 | 3 |
| C | 5 | 4 |

Model:

```text
max z = 3 x_A + 4 x_B + 5 x_C

subject to:
  2 x_A + 3 x_B + 4 x_C <= 5

x_A, x_B, x_C in {0, 1}
```

The optimal solution is:

```text
x_A = 1
x_B = 1
x_C = 0
```

Total weight:

```text
2 + 3 = 5
```

Total value:

```text
3 + 4 = 7
```

So the best choice is `A` and `B`.

---

## Example 2 - Project Selection

You have a budget of `10` weeks and must decide which projects to build.

| Project | Expected value | Required weeks |
|---|---:|---:|
| Sales dashboard | 9 | 5 |
| Report automation | 6 | 4 |
| Customer portal | 12 | 8 |
| Core refactor | 7 | 3 |

Each project is either selected or not selected:

```text
max z = 9 x_1 + 6 x_2 + 12 x_3 + 7 x_4

subject to:
  5 x_1 + 4 x_2 + 8 x_3 + 3 x_4 <= 10

x_i in {0, 1}
```

The solver compares feasible project combinations and returns the one with the
largest total value within the budget.

---

## Example 3 - Van Loading

A van can carry at most `15` kg.

| Package | Profit | Weight |
|---|---:|---:|
| P1 | 20 | 4 |
| P2 | 30 | 6 |
| P3 | 35 | 7 |
| P4 | 12 | 3 |
| P5 | 3 | 1 |

Model:

```text
max z = 20 x_1 + 30 x_2 + 35 x_3 + 12 x_4 + 3 x_5

subject to:
  4 x_1 + 6 x_2 + 7 x_3 + 3 x_4 + x_5 <= 15

x_i in {0, 1}
```

The best solution is not necessarily "take the highest value item first". The
value/weight ratio helps intuition, but the exact problem depends on the full
combination of weights.

---

## How to Use It in Optees

1. Set the maximum capacity.
2. Add one row per item.
3. Enter item value.
4. Enter integer item weight.
5. Click `Optimize knapsack`.

The solution page shows selected items, total value, total weight and remaining
capacity.

