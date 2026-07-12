# Dijkstra Example: Delivery Route

Suppose a delivery starts at depot `A` and must reach customer `D`. Each directed
edge carries a travel cost:

| Edge | Weight |
| --- | ---: |
| A -> B | 4 |
| A -> C | 1 |
| C -> B | 2 |
| B -> D | 1 |
| C -> D | 8 |

The direct-looking route `A -> B -> D` costs `5`. Dijkstra instead discovers:

```text
A -> C -> B -> D
1 + 2 + 1 = 4
```

It settles `C` with tentative distance `1`, improves the known distance to `B`
from `4` to `3`, then settles `D` with final distance `4`.

Load `examples/shortest_path_delivery.json` to reproduce the graph. Try changing
the `C -> D` weight: the returned route changes only when its total cost becomes
smaller than `4`.

For an undirected road, clear **Directed edges**. One entered edge can then be
travelled in either direction.
