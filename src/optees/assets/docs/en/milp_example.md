# MILP Examples

MILP is useful when a linear model has decisions that must be whole numbers or
Boolean yes/no choices. Use variable type `Binary / Boolean (0/1)` for decisions
such as open/closed, chosen/not chosen, active/inactive.

## Assignment problem

Two workers must be assigned to two jobs. Let:

| Variable | Meaning | Type |
|---|---|---|
| x11 | worker 1 does job 1 | binary |
| x12 | worker 1 does job 2 | binary |
| x21 | worker 2 does job 1 | binary |
| x22 | worker 2 does job 2 | binary |

Minimize cost:

```text
min z = 1 x11 + 2 x12 + 2 x21 + 1 x22
```

Each worker gets exactly one job:

```text
x11 + x12 = 1
x21 + x22 = 1
```

Each job is covered exactly once:

```text
x11 + x21 = 1
x12 + x22 = 1
```

The optimal assignment is `x11 = 1`, `x22 = 1`, with objective `z = 2`.

## Facility opening with shipment

Suppose you can ship from a facility only if you decide to open it. Let:

| Variable | Meaning | Type |
|---|---|---|
| y | open the facility | binary |
| x | units shipped | continuous or integer |

The linking constraint is:

```text
0 <= x <= 120 y
y in {0, 1}
```

If `y = 0`, the facility is closed and therefore `x = 0`. If `y = 1`, shipment
can range up to 120 units. A typical objective minimizes fixed and variable cost:

```text
min z = 800 y + 6 x
```

## Production scrap with quantity blocks

MILP is useful when unit scrap depends on both product type and production
quantity block. You must decide how much to produce and which block each product
belongs to.

For product `X`, suppose:

| Quantity produced | Unit scrap |
|---|---:|
| 0-999 | 8% |
| 1000+ | 4% |

Split production into block variables:

```text
q_X = q_X1 + q_X2
```

| Variable | Meaning | Type |
|---|---|---|
| q_X1 | quantity of X in block 0-999 | continuous or integer |
| q_X2 | quantity of X in block 1000+ | continuous or integer |
| y_X1 | block 0-999 is used | binary |
| y_X2 | block 1000+ is used | binary |

Block constraints:

```text
0 <= q_X1 <= 999 y_X1
1000 y_X2 <= q_X2 <= M y_X2
y_X1 + y_X2 <= 1
y_X1, y_X2 in {0, 1}
```

If the goal is minimizing produced scrap:

```text
min z = 0.08 q_X1 + 0.04 q_X2
```

If you must satisfy a net demand `d_X`, meaning good pieces after scrap, add:

```text
0.92 q_X1 + 0.96 q_X2 >= d_X
```

For multiple products, repeat the same structure for each product `i` and each
block `k`:

```text
min sum_i sum_k scrap_i,k q_i,k
```

with demand constraints:

```text
sum_k yield_i,k q_i,k >= demand_i
```

and binary constraints that select at most one production block for each product.
