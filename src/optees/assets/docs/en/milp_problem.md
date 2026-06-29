# MILP Problem Description

Mixed-Integer Linear Programming (MILP) extends Linear Programming by adding one
fundamental requirement: some decision variables cannot take arbitrary real
values. They must be integer or binary.

In a continuous LP, the solver may choose a value such as `x = 2.37`. In a MILP
you can require a variable to be:

| Type | Meaning |
|---|---|
| Continuous | fractional values are allowed |
| Integer | only whole numbers are allowed |
| Binary / Boolean | only 0 or 1 is allowed |

This changes the nature of the problem. You are not only optimizing a linear
function; you are also choosing a feasible discrete combination.

## Mathematical form

A MILP can be written as:

```text
optimize    c^T x + alpha
subject to  A_ub x <= b_ub
            A_eq x  = b_eq
            l <= x <= u
            x_j in R        for continuous variables
            x_j in Z        for integer variables
            x_j in {0, 1}   for binary / Boolean variables
```

The first lines are the same as LP: linear objective, linear constraints, and
bounds. The difference is the variable domain.

A binary variable represents a logical choice:

```text
y = 1  choice active
y = 0  choice inactive
```

That is why MILP is useful for setup decisions, facility openings, assignments,
quantity blocks, thresholds, minimum batches, and alternative regimes.

## Geometric intuition

In LP, constraints define a continuous feasible region: a polyhedron. The solver
can move inside that region, and the optimum is found at a vertex or on a face.

In MILP, some coordinates must be integer. Not every point of the polyhedron is
usable. The solver sees two layers:

1. the continuous region of the LP relaxation;
2. the points that also satisfy integrality.

The LP relaxation may suggest a very good point, but if that point has a binary
variable equal to `0.43`, it is not feasible for the MILP.

## What Optees does when you click Optimize

When you click `Optimize MILP`, Optees converts the GUI model into a canonical
problem dictionary:

```text
sense         min or max
c             objective coefficients
A_ub, b_ub    <= constraints
A_eq, b_eq    = constraints
bounds        lower and upper bounds
integrality   C, I, B for each variable
var_names     variable names
```

Constraints of type `>=` are converted to `<=` by multiplying by `-1`. For
example:

```text
2 x + y >= 10
```

becomes:

```text
-2 x - y <= -10
```

Binary variables are normalized as:

```text
0 <= y <= 1
y integer
```

Optees then sends the problem to an OR-Tools backend:

- CP-SAT for integer/binary models with suitable integer-like data;
- CBC for mixed models or non-integer coefficients.

## How the algorithm reasons

The main teaching idea is this: the solver alternates between continuous
estimates and discrete choices.

First it solves or considers an LP relaxation, meaning the problem without
integrality. This relaxation gives a theoretical bound. If even the relaxation
cannot beat an already known feasible solution, that part of the search can be
discarded.

When a discrete variable has a fractional value, the solver branches. For
example, if the relaxation gives:

```text
y = 0.43
```

the solver can split the search into two subproblems:

```text
y = 0
y = 1
```

For an integer variable `x = 4.7`, it can split into:

```text
x <= 4
x >= 5
```

This is the basic logic of branch-and-bound.

## Incumbent, best bound, and MIP gap

During the search, the solver tracks two key quantities:

| Name | Meaning |
|---|---|
| Incumbent | best integer feasible solution found so far |
| Best bound | best theoretical bound still possible |

For a minimization problem:

- the incumbent is the value of an actual feasible solution;
- the best bound says how much the true optimum could still improve.

The MIP gap is the relative distance between incumbent and best bound. A small
gap means the current solution is close to being proven optimal. If the gap is
zero or within tolerance, the solver can report `Optimal`.

## How to read statuses

| Status | Meaning |
|---|---|
| Optimal | a feasible solution was found and proven optimal |
| Feasible | a feasible solution was found, but optimality was not proven |
| Infeasible | no solution satisfies all constraints |
| Unbounded | the objective can improve without limit |
| NotSolved | the solver did not return a usable solution |

The `Feasible` status is especially important in MILP. It is not a failure: it
means the solution satisfies the constraints, but the solver has not completed
the mathematical proof of optimality. This can happen with a time limit or with
hard combinatorial models.

## Conceptual example: production thresholds

If production scrap changes with quantity, the model contains a discrete block
choice. For example:

| Quantity produced | Scrap |
|---|---:|
| 0-999 | 8% |
| 1000+ | 4% |

The question is not only "how much do I produce?", but also "which production
block am I using?". That second question requires binary variables.

One possible formulation is:

```text
q_X = q_X1 + q_X2
0 <= q_X1 <= 999 y_X1
1000 y_X2 <= q_X2 <= M y_X2
y_X1 + y_X2 <= 1
y_X1, y_X2 in {0, 1}
```

The scrap minimization objective becomes:

```text
min 0.08 q_X1 + 0.04 q_X2
```

The solver decides at the same time:

- how much quantity to assign to each block;
- which block to activate;
- which combination minimizes total scrap while satisfying demand and other
  constraints.

## Important limit

MILP remains linear. The objective and constraints must be written as sums of
coefficients times variables. If the model contains products between variables,
powers, roots, or curved functions, then it is no longer a pure MILP and may
require nonlinear programming or a reformulation.
