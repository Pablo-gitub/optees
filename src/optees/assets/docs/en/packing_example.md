# Single-container 3D packing: worked example

Suppose a warehouse must load one container whose usable internal dimensions are **10 x 8 x 6**. Three indivisible item types are available:

| Item | Dimensions | Quantity | Value | Rotation |
|---|---:|---:|---:|---|
| Machine part | 6 x 4 x 3 | 1 | 12 | Keep upright |
| Supply box | 4 x 4 x 2 | 2 | 6 | Any orthogonal |
| Long case | 8 x 2 x 2 | 1 | 8 | Rotate around Z |

The container also has a maximum **weight** of 30. The unit consumptions are 16, 6, and 8 respectively.

## Entering the model

1. Enter the three internal container dimensions.
2. Add a capacity named `weight` with limit `30`.
3. Add one row per item type. Quantity creates distinct indivisible units.
4. Choose each rotation policy. Optees considers only axis-aligned rotations in multiples of 90 degrees.
5. Choose **Maximize loaded value** if excluding an item is allowed, or **Require every item** to test the complete loading request.
6. Keep **Simple gravity** to lower each item to its first geometric support, or choose **No gravity** to inspect the coordinates returned directly by the MILP.

## Reading the result

Each loaded unit receives coordinates `(x, y, z)`, an oriented size, and an orientation code. The coordinates identify its lower-left-bottom corner. Every box stays inside the container and every pair of loaded boxes is separated on at least one axis.

If the complete load is impossible, Optees labels it **infeasible** and separately computes a maximum-value feasible recovery. This distinction matters: the recovery does not make the original all-required request feasible.

## JSON equivalent

```json
{
  "version": "1",
  "problem_type": "packing",
  "variant": "single_container_3d",
  "selection_policy": "optional",
  "gravity_mode": "simple",
  "container": {
    "id": "container-1",
    "name": "Demo container",
    "dimensions": {"length": 10, "width": 8, "height": 6},
    "capacities": [{"name": "weight", "limit": 30}]
  },
  "items": [{
    "id": "machine", "name": "Machine part",
    "dimensions": {"length": 6, "width": 4, "height": 3},
    "quantity": 1, "value": 12,
    "rotation_policy": "keep_upright",
    "allowed_orientations": [],
    "consumptions": [{"name": "weight", "amount": 16}]
  }],
  "solver_options": {"time_limit": 60, "mip_gap": 0.01}
}
```
