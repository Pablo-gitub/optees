# Example: approval classification

Suppose an organization has past applications. Each historical row records two
numeric features:

- an applicant score;
- a debt ratio;

and the known outcome: `no` or `yes`.

The question is not "how large will a number become?" It is "which of two
classes is more plausible for a new observation?" This is a **binary
classification** problem.

## Small teaching dataset

Create two feature columns named `score, debt_ratio`, use `approved` as the
target name, and enter a balanced starting table such as:

| score | debt_ratio | approved |
|---:|---:|:---|
| 38 | 0.78 | no |
| 44 | 0.70 | no |
| 51 | 0.64 | no |
| 57 | 0.55 | no |
| 68 | 0.42 | yes |
| 74 | 0.35 | yes |
| 81 | 0.28 | yes |
| 88 | 0.19 | yes |

Keep the default seed and test fraction initially. Optees stratifies the
split, so both labels occur in both the training and held-out test partitions.
It standardizes each feature using the training rows only, fits local logistic
regression, and reports the test metrics on rows never used to fit the model.

## Reading the result

The second alphabetically sorted label is treated as the positive label. The
result shows its probability for every row; at 50% or above, that label is
predicted. In this example a positive coefficient for `score` tends to
increase the probability of `yes`, while a positive coefficient for
`debt_ratio` tends to increase it only if the data supports that relationship.

Use the confusion matrix to distinguish false positives from false negatives.
Which error matters more is a domain decision, not something accuracy can
decide automatically. The 2D chart, when shown, is a teaching visualization of
the 50% decision boundary, not proof that the boundary is reliable outside the
observed data.

## Important limitation

This compact example is intentionally too small for a real approval system.
Do not use it to make consequential decisions about people. Real deployment
requires representative data, careful feature governance, fairness and error
analysis, validation beyond one split, and appropriate human oversight.
