# Continuous Nonlinear Programming

## Mathematical Problem

The first Nonlinear Programming (NLP) workflow in Optees solves:

```text
minimize or maximize    f(x)
subject to              l_i <= x_i <= u_i,  i = 1, ..., n
                         x in R^n
```

The decision vector `x` is continuous, as in LP. The difference is that the
objective `f(x)` can curve: it may contain powers, products, roots,
trigonometric functions, logarithms, or exponentials. This first slice has no
general nonlinear constraints; use lower and upper bounds to define a box.

## Why A Starting Point Matters

An LP has a special convex geometry: a finite optimum can be characterized by
vertices and an exact solver can prove it. A nonlinear landscape can have many
stationary points, valleys, and peaks. Numerical methods start from your initial
point and move according to local information.

For a non-convex function, two valid initial points can converge to two
different local minima. For that reason, the first NLP result state is
**Converged**, not **Optimal**:

- `Converged` means the selected method met a numerical stopping rule near the
  returned point.
- `Iteration limit` means the method stopped at the configured budget; its
  displayed candidate is useful but not certified as converged.
- `Failed` means the solver or objective could not produce a reliable finite
  candidate.

Neither state proves a global optimum. Repeat important non-convex runs from
several starts and compare the attained objective values.

## Methods Implemented In Optees

### BFGS

BFGS builds an approximation of curvature from objective evaluations and uses
it to propose improving directions. In this first release it is intended for
unbounded smooth problems. It is efficient on well-scaled, locally smooth
objectives such as nonlinear quadratics.

### Nelder-Mead

Nelder-Mead maintains a simplex of points and modifies it through reflection,
expansion, contraction, and shrink steps. It does not require a user-provided
derivative. It is a useful educational baseline when derivatives are awkward,
but it is still a local method and can be slow in higher dimensions.

### L-BFGS-B

L-BFGS-B is the bound-aware method in this workflow. It combines a
limited-memory curvature approximation with projection onto the declared box
`l <= x <= u`. Select it whenever at least one variable has a lower or upper
bound.

## What Happens When You Click Optimize

1. Optees validates variable names, bounds, initial point, method, and the
   restricted objective expression.
2. It evaluates the formula at the initial point. The value must be a finite
   scalar.
3. For maximization, Optees passes `-f(x)` to the minimization backend and
   converts the final value back to the original sense.
4. SciPy's `minimize` runs the selected numerical method.
5. The solution page reports method, termination message, iterations,
   evaluations, local candidate, original objective value, and captured
   objective trace.

The trace is evidence of the path taken by that run. It is not a proof that
every other region of the search space was explored.

## Safe Objective Language

The objective is parsed into a restricted expression tree. Optees never runs
the text as arbitrary Python. Allowed elements are declared variables, finite
numbers, arithmetic, powers, and `abs`, `sin`, `cos`, `tan`, `exp`, `log`, and
`sqrt` with one argument. Unknown names and unsafe syntax are rejected.

This rule protects both the desktop application and reproducibility: an imported
JSON file and manually typed objective follow exactly the same validation path.

## Limits Of This First Slice

The current NLP page intentionally does not model nonlinear equality or
inequality constraints, global optimization, least squares, quadratic
programming, or nonlinear min-max. These require different methods and more
careful result semantics. They are tracked in `docs/NLP_FEATURE_PLAN.md` rather
than being shown as available controls.
