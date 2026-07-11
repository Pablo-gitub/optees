# Nonlinear Programming Examples

Continuous nonlinear programming is appropriate when the decision variables are
real-valued but the objective is not linear. In this first Optees workflow you
provide a feasible starting point and solve an unconstrained or box-bounded
scalar problem.

The result is a **local numerical candidate**. Different starting points can
lead to different candidates when the landscape has several valleys or peaks.

## Rosenbrock Valley

The Rosenbrock function has a narrow curved valley:

```text
min f(x1, x2) = (1 - x1)^2 + 100 (x2 - x1^2)^2
```

Use `x1 = -1.2`, `x2 = 1`, blank bounds, **Nelder-Mead**, and:

```text
(1 - x1)**2 + 100 * (x2 - x1**2)**2
```

The selected basin contains the minimizer `(1, 1)` with `f = 0`. This example
shows why method choice matters: a derivative-free simplex method is a useful
baseline on a narrow valley, while finite-difference BFGS can report a
precision-related termination before declaring convergence.

## Bounded Nonlinear Quadratic

Minimize:

```text
min f(x1, x2) = (x1 - 5)^2 + (x2 - 1)^2
```

with `0 <= x1 <= 2` and `-2 <= x2 <= 2`. Start from `(0, 0)` and select
**L-BFGS-B**. The unconstrained minimizer would be `(5, 1)`, but `x1 = 5` is
not allowed. The constrained candidate is `(2, 1)` with objective `9`.

Bounds do not add a separate formula to the objective: they restrict the points
that the numerical method can consider as candidates.

## Nonlinear Maximization

Optees also accepts a maximization sense:

```text
max f(x1) = 10 - (x1 - 3)^2
```

Start at `x1 = 0`, leave bounds blank, and choose BFGS. The best local candidate
is `x1 = 3`, with original objective value `10`. Internally the backend
minimizes `-f(x1)`, but the result page always shows the original value.

## Expression Syntax

The objective box is a restricted mathematical language, not a Python console.
It accepts declared variable names, numeric literals, parentheses, `+`, `-`,
`*`, `/`, `**`, unary signs, and these one-argument functions:

```text
abs, sin, cos, tan, exp, log, sqrt
```

For example: `sqrt(x1**2 + x2**2) + exp(x1)`. Unknown names, imports,
attributes, indexes, comparisons, and Python code are rejected before solving.
Every evaluation must be finite: `log(-1)`, `sqrt(-1)`, division by zero, `NaN`,
and infinity are reported as failures rather than silently accepted.
