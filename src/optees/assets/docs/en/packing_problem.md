# Mathematical description of orthogonal 3D packing

Single-container 3D packing asks whether and where rectangular, indivisible units can be placed inside one rectangular container. Optees implements **orthogonal packing**: every edge remains parallel to a container axis, so rotations are multiples of 90 degrees and diagonal placement is excluded.

## Decisions

For each unit `i`, the model decides:

- whether it is loaded, through a binary variable `s_i`;
- one permitted orientation;
- continuous coordinates `(x_i, y_i, z_i)` for its lower corner;
- for every pair of units, which spatial separation relation prevents overlap.

With oriented dimensions `(l_i, w_i, h_i)` and container dimensions `(L, W, H)`, containment requires:

```text
0 <= x_i <= L - l_i
0 <= y_i <= W - w_i
0 <= z_i <= H - h_i
```

For two loaded units `i` and `j`, at least one disjunction must hold: `i` is left/right, before/behind, or below/above `j`. The MILP linearizes these alternatives with binary variables and valid big-M constants derived from the container dimensions.

## Objective and capacities

In optional mode the objective is:

```text
maximize sum(value_i * s_i)
```

An additional resource `r` creates:

```text
sum(consumption_ir * s_i) <= capacity_r
```

In all-required mode, every `s_i = 1`. If that exact request is infeasible, Optees performs a second, explicitly labelled optional solve to identify the best recoverable load.

## Gravity modes

**No gravity** displays the coordinates returned by the MILP. **Simple gravity** performs a deterministic geometric post-processing step: it keeps X/Y and orientation fixed and lowers each box until it reaches the floor or the highest box with an overlapping horizontal footprint below it. Since boxes only move downward and preserve their horizontal footprint, containment and non-overlap remain valid.

Simple gravity is comparable to downward compaction in a block puzzle. Any positive footprint overlap is treated as support. It does not enforce minimum support area, balance, centre of gravity, material strength, or load-bearing limits.

## Why the problem is difficult

The number of pairwise non-overlap decisions grows quadratically with the number of units, while orientations and assignments are discrete. Exact solve time can therefore increase sharply. A feasible result at a time limit is useful but is not an optimality proof; the reported MIP gap quantifies the remaining bound when available.

## Geometric scope

The implemented model assumes rectangular boxes, one rectangular container, axis-aligned placement, and no physical simulation. Stability, center of gravity, support area, loading sequence, cylinders, and free-angle rotations are separate constraints and are not silently approximated.
