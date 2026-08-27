# Worked Examples

Three small problems, each with an answer you can verify by hand. Enter them in
the formulation page and compare.

## 1. An interior optimum

No constraints at all. The bowl has a bottom, and the bottom is the answer.

```
minimize  ½ (2x₁² + 2x₂² + 2x₁x₂) − 4x₁ − 6x₂
```

Enter it as:

| Field | Value |
| --- | --- |
| Sense | Minimize |
| Q | `[[2, 1], [1, 2]]` |
| c | `[-4, -6]` |
| α | `0` |
| Bounds | both blank (unbounded) |
| Constraints | none |

Setting the gradient `Qx + c` to zero gives the exact optimum

```
x* = (2/3, 8/3) ≈ (0.6667, 2.6667)      f(x*) = −28/3 ≈ −9.3333
```

Both variables land in the **Interior** state: nothing is pushing back on them.

## 2. A boundary optimum

Now the constraint does the work.

```
minimize  ½ (x₁² + x₂²)
subject to  x₁ + x₂ ≥ 2,  x₁ ≥ 0,  x₂ ≥ 0
```

| Field | Value |
| --- | --- |
| Sense | Minimize |
| Q | `[[1, 0], [0, 1]]` |
| c | `[0, 0]` |
| Bounds | lower `0` for both |
| Constraint | `1·x₁ + 1·x₂ ≥ 2` |

The unconstrained minimum is the origin, but the origin is not feasible. The
answer is the closest feasible point to it:

```
x* = (1, 1)      f(x*) = 1
```

The constraint row shows **Binding** with zero slack, and it carries a nonzero
dual multiplier: relaxing the right-hand side would improve the objective. With
two variables the chart shows this directly — concentric contours pushed up
against the constraint line, touching it at exactly one point.

## 3. Concave maximization

The mirror case. `Q` is negative definite, so the surface is a dome.

```
maximize  −½ (2x₁² + 2x₂²) + 4x₁ + 6x₂
subject to  x₁ ≥ 0,  x₂ ≥ 0
```

| Field | Value |
| --- | --- |
| Sense | Maximize |
| Q | `[[-2, 0], [0, -2]]` |
| c | `[4, 6]` |
| Bounds | lower `0` for both |

```
x* = (2, 3)      f(x*) = 13
```

Note that the same matrix with **Minimize** selected is rejected: a dome has no
minimum, and the message names the curvature as the reason.

## Two informative failures

Worth reproducing deliberately — the refusal is the lesson.

**Infeasible.** Add both `x₁ + x₂ ≤ 1` and `x₁ + x₂ ≥ 3` to any problem. No
point satisfies both. The result is `Infeasible`, with no candidate vector.

**Unbounded.** Minimize with `Q = [[1, 0], [0, 0]]` and `c = [0, −2]`, with
both variables bounded below by zero and unbounded above. `x₂` costs nothing to
increase and pays −2 per unit forever. The result is `Unbounded`.

**Indefinite.** Try `Q = [[1, 2], [2, 1]]` with Minimize. Its eigenvalues are
3 and −1: a saddle. The problem is rejected before solving, because this
capability makes no claim about non-convex objectives.

## Importing and exporting

Every problem here can be saved with **Export JSON** and reopened with
**Import JSON**. It is the same document the command line and the local API
accept, so a problem you build on this page can be replayed in a script without
retyping it.
