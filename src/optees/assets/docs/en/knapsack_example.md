# Knapsack Examples

The Knapsack family is useful when you must choose items or item quantities in
order to maximize value while respecting one or more capacities. The variants
differ in the meaning of the decision variable `x_i`.

| Variant | Meaning of `x_i` |
|---|---|
| 0/1 | item excluded or selected once |
| Bounded | integer quantity with a maximum limit |
| Unbounded | integer quantity with no explicit limit |
| Fractional | continuous quantity or fraction |
| Multi-dimensional | one or more resources: weight, volume, time, budget |

---

## 1. 0/1 Knapsack - Item Selection

Capacity is `5`.

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

Total weight is `2 + 3 = 5`, total value is `3 + 4 = 7`.

Use this variant when each item can be selected at most once: loading a van,
selecting projects, choosing features under a budget.

---

## 2. Bounded Knapsack - Limited Integer Quantities

A warehouse must prepare a promotional kit. Each item has value, weight and a
maximum available quantity.

| Item | Value | Weight | Max quantity |
|---|---:|---:|---:|
| Pen | 2 | 1 | 4 |
| Mug | 8 | 3 | 2 |
| Notebook | 5 | 2 | 3 |

Capacity: `7`.

Model:

```text
max z = 2 x_1 + 8 x_2 + 5 x_3

subject to:
  1 x_1 + 3 x_2 + 2 x_3 <= 7

x_1 in {0, 1, 2, 3, 4}
x_2 in {0, 1, 2}
x_3 in {0, 1, 2, 3}
```

One feasible solution is:

```text
x_1 = 1
x_2 = 2
x_3 = 0

weight = 1 + 2*3 = 7
value = 2 + 2*8 = 18
```

Use this variant when several copies of the same type may be selected, but
availability is limited.

---

## 3. Unbounded Knapsack - Repeatable Integer Quantities

An application fills a cache with repeatable block types.

| Block | Value | Weight |
|---|---:|---:|
| A | 3 | 1 |
| B | 5 | 3 |
| C | 9 | 4 |

Capacity: `7`.

Model:

```text
max z = 3 x_A + 5 x_B + 9 x_C

subject to:
  1 x_A + 3 x_B + 4 x_C <= 7

x_A, x_B, x_C in {0, 1, 2, ...}
```

The solver can reuse the same block type several times, limited only by
capacity.

Use this variant for repeatable item types: standard lots, material cuts,
replicable packages.

---

## 4. Fractional Knapsack - Divisible Items

Suppose you have divisible raw materials.

| Material | Value | Weight |
|---|---:|---:|
| A | 60 | 10 |
| B | 100 | 20 |
| C | 120 | 30 |

Capacity: `50`.

Model:

```text
max z = 60 x_A + 100 x_B + 120 x_C

subject to:
  10 x_A + 20 x_B + 30 x_C <= 50

0 <= x_A, x_B, x_C <= 1
```

For the single-capacity fractional case, value/weight density is optimal:

```text
A: 60 / 10 = 6
B: 100 / 20 = 5
C: 120 / 30 = 4
```

The solver takes all of `A`, all of `B`, and part of `C`:

```text
x_A = 1
x_B = 1
x_C = 2/3

value = 60 + 100 + 80 = 240
```

Use this variant when items are truly divisible: liquids, raw materials,
financial allocation, allocable time.

---

## 5. Multi-dimensional 0/1 - Several Resources

Each item consumes more than one resource. For example weight and volume.

| Item | Value | Weight | Volume |
|---|---:|---:|---:|
| A | 8 | 4 | 1.5 |
| B | 9 | 5 | 2 |
| C | 14 | 6 | 4.5 |
| D | 7 | 3 | 2 |

Capacities:

```text
weight <= 10
volume <= 6
```

Model:

```text
max z = 8 x_A + 9 x_B + 14 x_C + 7 x_D

subject to:
  4 x_A + 5 x_B + 6 x_C + 3 x_D <= 10
  1.5 x_A + 2 x_B + 4.5 x_C + 2 x_D <= 6

x_i in {0, 1}
```

The solution must satisfy both capacities. A set may fit by weight and violate
volume, so a single resource is not enough.

---

## 6. Multi-dimensional with Quantities

Inside the multi-dimensional variant you can change the domain of `x_i`.

### Bounded Integer

```text
x_i in {0, ..., u_i}
```

Example: choose how many boxes of each product to load, with stock limits.

### Unbounded Integer

```text
x_i in {0, 1, 2, ...}
```

Example: choose how many standard lots to produce, limited only by machine time
and raw material.

### Fractional

```text
0 <= x_i <= u_i
```

Example: choose kilograms of ingredients with weight, volume and budget
constraints. With several resources, the value/weight greedy rule is no longer
enough: the model becomes a continuous LP.

---

## How to Use These Models in Optees

1. Choose the Knapsack variant.
2. Choose the domain when using Multi-dimensional.
3. Enter capacities, resources and items.
4. Enter maximum limits when needed.
5. Click `Optimize knapsack`.

The solution page shows optimal value, selected items or quantities, resource
usage and remaining capacities.
