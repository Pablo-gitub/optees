# How Linear Regression Works

## The modeling question

Regression learns a numerical relationship from examples. For each observation
`i`, we record feature values `x_i` and one continuous target `y_i`. Examples
include price, energy consumption, delivery time, or demand.

The first Optees workflow accepts only finite numeric data. Categorical text,
missing values, and time-series forecasting assumptions are outside this
initial educational scope.

## Linear model

With `p` features, the model predicts:

```text
y_hat_i = beta_0 + beta_1 x_i1 + ... + beta_p x_ip
```

`beta_0` is the intercept and the other coefficients describe the fitted
linear contribution of each feature while the other features are held fixed.
They are not automatically causal effects.

## OLS objective

For training observations, OLS chooses coefficients that minimize:

```text
sum_i (y_i - y_hat_i)^2
```

Squaring makes large residuals count more and gives a convenient numerical
solution. Optees solves this local linear-algebra problem directly; it is not
an iterative black-box optimizer.

## Ridge objective

Ridge changes the training objective to:

```text
sum_i (y_i - y_hat_i)^2 + alpha * sum_j beta_j^2
```

The positive `alpha` discourages very large feature coefficients. The
intercept is excluded from the penalty. Ridge can be useful when features are
strongly correlated or when the training table is small relative to the number
of features, but it may also introduce bias.

## Honest evaluation

Before fitting, Optees uses the selected seed to split rows into training and
test partitions. The test rows are not used to choose coefficients.

- **MAE**: average absolute residual, in the target's unit.
- **MSE**: average squared residual, which emphasizes large errors.
- **RMSE**: square root of MSE, again in the target's unit.
- **R-squared**: improvement relative to predicting the test mean. It can be
  negative and is unavailable when the target is constant.

Compare methods only on the same dataset and split. For serious work, use more
data and repeated or cross-validated evaluation, inspect data quality, and
consider whether deployment data will have the same distribution.
