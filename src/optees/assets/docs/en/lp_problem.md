# Linear Programming — Theory & Algorithms

## What is Linear Programming?

A **Linear Program (LP)** is an optimization problem where both the objective
and all constraints are **linear functions** of continuous decision variables.

LP is the backbone of modern operations research and is used in supply chains,
production planning, finance, diet optimization, transportation, and much more.

---

## Mathematical Standard Form

The general LP written in matrix notation:

```
minimize (or maximize)    z = c₁x₁ + c₂x₂ + … + cₙxₙ + offset

subject to:
  a₁₁x₁ + a₁₂x₂ + … + a₁ₙxₙ  ≤  b₁     ← inequality constraints (A_ub x ≤ b_ub)
  a₂₁x₁ + …                   ≤  b₂
  …
  e₁₁x₁ + …                   =  d₁     ← equality constraints  (A_eq x = b_eq)
  lbᵢ  ≤  xᵢ  ≤  ubᵢ                    ← variable bounds
```

**Key notation:**

- **x ∈ ℝⁿ** — decision variables (can be fractional)
- **c ∈ ℝⁿ** — objective coefficients (profit or cost per unit)
- **A_ub, b_ub** — inequality constraint matrix and right-hand side vector
- **A_eq, b_eq** — equality constraint matrix and right-hand side vector
- **lb, ub** — lower and upper bounds (use −∞ / +∞ for unbounded)
- **offset** — constant term added to the objective (does not affect the optimum)

> **Maximization → Minimization:** every maximization LP can be solved as a
> minimization by negating the objective: max cᵀx  =  min (−c)ᵀx

---

## Geometry: Feasible Region and Optimal Face

The constraint set defines a **convex polyhedron** — the feasible region.
A linear objective always attains its optimum on a **face** of this polyhedron.

| Optimal face | Dimension | Meaning |
|---|---|---|
| Single vertex | 0 | **Unique** optimal solution |
| Edge (1-D face) | 1 | Infinitely many optima along a segment |
| k-dimensional face | k ≥ 2 | Infinitely many optima on a k-D surface |

**Key theorem (Fundamental theorem of LP):**
If a feasible LP has a finite optimum, then at least one **vertex** of the polyhedron
is an optimal solution. This is the mathematical foundation of the Simplex algorithm.

---

## The Simplex Algorithm (Dantzig, 1947)

The Simplex method moves from vertex to vertex along the edges of the polyhedron,
always improving the objective:

```
Algorithm Simplex:
  1. Find an initial basic feasible solution (a vertex)
  2. Compute reduced costs for all non-basic variables
  3. If all reduced costs ≥ 0  →  current vertex is optimal  (STOP)
  4. Select entering variable  (most negative reduced cost)
  5. Select leaving variable   (minimum ratio test)
  6. Perform basis exchange (pivot)  →  move to adjacent vertex
  7. Go to step 2
```

**Pivot in detail:**

- A *basis* is a set of n linearly independent active constraints (n = number of variables)
- A *basic feasible solution* is the unique vertex defined by a basis
- The **entering variable** is chosen to decrease the objective most rapidly
- The **leaving variable** ensures the new solution remains feasible (no variable exceeds its bound)

Simplex is **exponential** in the worst case (theory) but runs in near-linear time
on virtually all practical problems.

---

## Interior-Point Methods (Karmarkar, 1984)

Instead of walking along edges, interior-point methods travel through the
**interior** of the feasible region along a curved path toward the optimum:

```
Algorithm (barrier/central-path):
  1. Start from a strictly feasible interior point
  2. Follow the central path (minimize objective + barrier function)
  3. Reduce the barrier weight → solution converges to the optimal face
  4. Stop when the duality gap < tolerance
```

- **Complexity:** O(n³ · L) — provably polynomial in problem size
- Preferred for very large or numerically ill-conditioned problems
- Used internally by HiGHS for certain problem classes

---

## HiGHS Solver (used by Optees)

Optees calls **[HiGHS](https://highs.dev)** — a state-of-the-art open-source LP/MIP solver —
through `scipy.optimize.linprog`:

```python
from scipy.optimize import linprog

result = linprog(
    c,                              # objective coefficients (minimization)
    A_ub=A_ub, b_ub=b_ub,         # inequality constraints
    A_eq=A_eq, b_eq=b_eq,         # equality constraints (optional)
    bounds=list(zip(lb, ub)),      # variable bounds
    method="highs",                 # HiGHS back-end
)

# result.status codes:
#   0  Optimal solution found
#   2  Problem is infeasible
#   3  Problem is unbounded
#   4  Iteration / time limit reached
```

HiGHS automatically selects the most effective algorithm (Simplex or interior-point).
The raw status code is then mapped by Optees to: **Optimal / Infeasible / Unbounded / Not Solved**.

---

## Duality

Every LP has an associated **dual problem** that provides complementary information:

```
Primal:  min cᵀx   s.t. Ax ≥ b,  x ≥ 0
Dual:    max bᵀy   s.t. Aᵀy ≤ c, y ≥ 0
```

**Key duality results:**

- **Weak duality:** dual objective ≤ primal objective (for min/max pair)
- **Strong duality:** at optimality, primal value = dual value
- **Shadow prices (dual variables yᵢ):** the rate of change of z\* per unit increase in bᵢ

Shadow prices tell you how much it is worth relaxing each constraint.

---

## Optimal Variable Ranges (Optees Feature)

After finding the optimal value **z\***, Optees computes the range of each variable
across **all** optimal solutions using a post-processing algorithm:

```
Algorithm — Optimal Range Analysis:
  1. Solve LP  →  obtain optimal value z*
  2. Add equality constraint:  cᵀx = z*   (lock objective at its optimum)
  3. For each decision variable xᵢ  (i = 1 … n):
       solve LP_min:  min xᵢ   subject to original constraints + cᵀx = z*
       solve LP_max:  max xᵢ   subject to original constraints + cᵀx = z*
       → optimal range of xᵢ  =  [min xᵢ,  max xᵢ]
  4. If  min xᵢ < max xᵢ  for any i  →  multiple optimal solutions exist
```

This is a **post-processing step** only: 2n additional LP solves, each cheap
because the constraint matrix is reused from the original problem.

**Interpretation:**

- Range = `[a, a]` (single point): variable is **fixed** at the optimum
- Range = `[a, b]` with a < b: variable is **free to vary** — infinitely many optima exist
