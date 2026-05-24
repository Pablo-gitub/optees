# LP — Practical Examples

Use these examples as templates when modelling your own linear optimization problem.
Each one can be entered directly using the LP form.

---

## Example 1 — Production Mix (Maximization)

**Scenario:** A workshop produces chairs (**X₁**) and tables (**X₂**).

| Resource | Chairs (X₁) | Tables (X₂) | Available |
|----------|-------------|-------------|-----------|
| Machine hours | 2 | 4 | ≤ 80 |
| Storage slots | 1 | 1 | ≤ 30 |
| **Profit / unit** | **30** | **50** | — |

**Objective:** maximize **z = 30 X₁ + 50 X₂**

**Constraints:**

- 2 X₁ + 4 X₂ ≤ 80  *(machine hours)*
- X₁ + X₂ ≤ 30  *(storage)*

**Bounds:** X₁ ≥ 0, X₂ ≥ 0  *(continuous — fractional output allowed)*

**Optimal solution:** X₁ = 10, X₂ = 15, **z\* = 1050**

```python
# SciPy's linprog always minimizes — negate the objective to maximize
c      = [-30, -50]             # maximize 30·X₁ + 50·X₂
A_ub   = [[2, 4], [1, 1]]
b_ub   = [80, 30]
bounds = [(0, None), (0, None)]
```

---

## Example 2 — Diet / Blending (Minimization)

**Scenario:** Find the cheapest mix of two ingredients that meets nutritional targets.
Let **X₁** = kg of ingredient A, **X₂** = kg of ingredient B.

**Objective:** minimize **z = 4 X₁ + 7 X₂**

**Constraints (minimum requirements):**

- 3 X₁ + X₂ ≥ 12  *(proteins ≥ 12 g)*
- X₁ + 2 X₂ ≥ 10  *(vitamins ≥ 10 mg)*

**Bounds:** X₁ ≥ 0, X₂ ≥ 0

> **Tip — entering ≥ constraints:** multiply both sides by −1 to convert to ≤ form:
> - −3 X₁ − X₂ ≤ −12
> - −X₁ − 2 X₂ ≤ −10

```python
c      = [4, 7]                   # minimize cost
A_ub   = [[-3, -1], [-1, -2]]    # ≥ constraints flipped to ≤
b_ub   = [-12, -10]
bounds = [(0, None), (0, None)]
```

---

## Example 3 — Multiple Optimal Solutions

When the objective is **parallel** to an active constraint, the entire edge is optimal
rather than a single vertex.

**Model:** maximize **z = X₁ + X₂** subject to X₁ + X₂ ≤ 6, X₁ ≥ 0, X₂ ≥ 0

Every point on the edge **X₁ + X₂ = 6** is optimal → z\* = 6.

Optees detects this automatically and reports:

```
X₁ ∈ [0, 6]   (free to vary at the optimum)
X₂ ∈ [0, 6]   (free to vary at the optimum)
→ Infinitely many optimal solutions
```

---

## Example 4 — Three-Variable Model

**Model:** maximize **z = X₁ + X₂ + X₃** subject to X₁ + X₂ + X₃ ≤ 6, Xᵢ ≥ 0

The feasible set is a 3D simplex (tetrahedron).
The optimal face is the triangle where X₁ + X₂ + X₃ = 6, giving **z\* = 6**
with infinitely many optimal solutions.

```
Optees output:
  Objective   z* = 6.0
  X₁ ∈ [0, 6]   X₂ ∈ [0, 6]   X₃ ∈ [0, 6]
  Status: Infinitely many optimal solutions
```

*Try it:* add 3 variables, set one constraint `X₁ + X₂ + X₃ ≤ 6`, and press **Optimize**.
