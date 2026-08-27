# Convex Quadratic Programming

## What this method solves

A quadratic programme keeps the constraints linear but lets the objective
curve. That single change covers a large family of real questions that linear
programming cannot express: minimizing risk, minimizing squared error,
minimizing deviation from a target, or smoothing a plan so that consecutive
periods do not swing wildly.

Optees writes the problem as

```
minimize    f(x) = ½ xᵀ Q x + cᵀ x + α
subject to  A x  (≤, =, ≥)  b
            l ≤ x ≤ u
```

with `x` a vector of continuous decision variables, `Q` a square symmetric
matrix, `c` a vector, and `α` a constant.

## Why the objective carries a ½

`Q` is read as the **Hessian** of the objective — the matrix of its second
derivatives. Under that convention the derivatives come out clean:

- the gradient is `∇f(x) = Q x + c`;
- the Hessian is `∇²f(x) = Q`.

The price of clean derivatives is the explicit ½ in the formula. A diagonal
entry `Qᵢᵢ` therefore contributes `½ Qᵢᵢ xᵢ²` to the objective, while a
symmetric off-diagonal pair `Qᵢⱼ = Qⱼᵢ` contributes `Qᵢⱼ xᵢ xⱼ` in total,
because it is counted twice.

So if you want the term `3 x₁²`, enter `Q₁₁ = 6`. If you want the cross term
`2 x₁ x₂`, enter `Q₁₂ = Q₂₁ = 1`.

## Symmetry

Only the symmetric part of `Q` can affect the objective value: `xᵀ Q x` and
`xᵀ Qᵀ x` are the same number. Optees still requires the matrix you submit to
be symmetric within a tight tolerance, and it never silently reshapes a matrix
you supplied. Making the change explicit is the point — a matrix you did not
intend is a modelling error worth seeing, not a rounding detail to absorb.

The desktop matrix editor mirrors each cell into its transposed position while
you type, so a matrix entered by hand is symmetric by construction.

## Convex, concave, and everything rejected in between

The **eigenvalues** of `Q` describe the curvature of the objective in every
direction.

- All eigenvalues zero or positive — `Q` is *positive semi-definite*. The
  surface is a bowl. Any local minimum is the global minimum. This is the case
  Optees solves when the sense is **minimize**.
- All eigenvalues zero or negative — `Q` is *negative semi-definite*. The
  surface is a dome, the mirror image, and Optees solves it when the sense is
  **maximize**.
- Mixed signs — `Q` is *indefinite*. The surface is a saddle: it curves up in
  one direction and down in another, and there can be many local optima with no
  reliable way to tell which is best.

Optees rejects the indefinite case before solving rather than returning a
number it cannot stand behind. A refusal you can act on is more useful than an
answer you cannot trust.

## Feasible versus optimal

Two questions are separate and stay separate in the result view.

- **Feasible** asks whether a point satisfies every constraint and bound. The
  set of all such points is the feasible region.
- **Optimal** asks whether, among the feasible points, this one has the best
  objective value.

A problem can be feasible but unbounded — the objective improves forever inside
the feasible region and no finite optimum exists. It can be infeasible, with no
point satisfying everything at once. And a run stopped by an iteration or time
limit may hold a feasible candidate that was never proven optimal. Optees
reports each of these as its own outcome instead of collapsing them into
"solved" and "not solved".

## Duals and the KKT conditions

When the backend supplies them, each constraint and each bound gets a **dual
multiplier**. Read it as a price: how much the objective would change per unit
change in that right-hand side or bound. A multiplier of zero means the
constraint is not currently limiting you.

The **KKT conditions** are the first-order test for optimality in a constrained
problem. They combine stationarity (the objective gradient is balanced by the
active constraints), complementary slackness (a constraint with slack has a
zero multiplier), and dual sign conditions. For a convex problem satisfying
them is sufficient for optimality — which is exactly why convexity is worth
insisting on.

## Independent validation

Optees does not take the backend's word for it. After a run, the candidate is
re-checked against the original problem: the vector shape, the bounds, every
constraint row, the objective recomputed from `Q`, `c`, and `α`, and — when
complete multipliers are present — the KKT conditions.

The report states honestly what it did and did not establish. If the duals were
missing, the KKT check is reported as unavailable rather than assumed. Passing
these checks confirms the recorded properties; it is not a second proof of
global optimality, and it says nothing about whether your formulation matches
the question you actually meant to ask.

## Limits of this version

- Variables and constraints are continuous; integers arrive with a later
  capability.
- Up to 500 variables and 1000 constraints.
- The matrix is dense in this schema version.
- OSQP is the only backend, so its numerical behaviour is the behaviour you
  get. Optees does not silently substitute another solver.
