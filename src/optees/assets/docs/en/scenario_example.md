# Example: robust production allocation

A producer must allocate ten units between products `x1` and `x2`. Market
conditions are uncertain, so the same allocation is evaluated under three
cost scenarios.

| Variable | Lower bound | Constraint |
| --- | ---: | --- |
| `x1` | 0 | `x1 + x2 = 10` |
| `x2` | 0 | `x1 + x2 = 10` |

| Scenario | Cost expression |
| --- | --- |
| Regime 1 | `2 x1 - x2 + 5` |
| Regime 2 | `-x1 + 3 x2 + 2` |
| Regime 3 | `x1 + x2 - 4` |

Select **Minimize the maximum loss**. Optees finds the feasible allocation
whose largest scenario cost is as small as possible. The binding scenarios in
the result explain which regimes prevent the guarantee from improving.

To explore the opposite semantics, select **Maximize the minimum reward** and
enter scenario coefficients as rewards. Do not reuse loss coefficients without
changing their meaning: the two orientations answer different questions.

Use **Export JSON** to inspect the versioned document, then import it again to
verify that variable and scenario order are preserved.
