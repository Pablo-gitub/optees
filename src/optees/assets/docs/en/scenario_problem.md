# Min-Max / Max-Min Optimization

This workflow chooses one set of decision variables and evaluates it under
every scenario you explicitly provide. It does not assign probabilities or
optimize an average outcome.

## Min-max loss

Use **minimize maximum loss** when scenario values represent costs, losses, or
penalties. Optees minimizes the largest scenario value, producing an upper
bound that no listed scenario exceeds.

## Max-min reward

Use **maximize minimum reward** when scenario values represent rewards,
benefits, or payoffs. Optees maximizes the smallest scenario value, producing a
lower bound that every listed scenario reaches.

Each scenario is linear in the same ordered variables. Variable bounds and
shared constraints define the feasible decisions. An optional shared linear
term is added to every scenario. Continuous problems use a linear program;
integer or binary variables select the corresponding mixed-integer reduction.

The result reports the guaranteed value, every scenario evaluation, and all
binding scenarios. Optees independently reconstructs these values from the
original problem before marking the result as verified.

This is robust optimization over a finite list, not probabilistic forecasting.
The guarantee covers only the scenarios and constraints you supplied.
