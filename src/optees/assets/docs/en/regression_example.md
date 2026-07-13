# Linear Regression Example

## Goal

Estimate a continuous house price from measurable characteristics. This is a
supervised-learning problem: historical observations contain both the inputs
and the price that was actually observed.

| Floor area | Rooms | Price |
|---:|---:|---:|
| 40 | 1 | 100 |
| 50 | 2 | 130 |
| 60 | 2 | 150 |
| 70 | 3 | 180 |
| 80 | 3 | 200 |
| 90 | 4 | 235 |

In the formulation view, enter `floor_area, rooms` as the features and
`price` as the target. Each table row is one historical observation.

## Train and test split

With a test fraction of `0.33` and seed `42`, Optees deterministically holds
out part of the table. The fit uses only the remaining training rows. The
reported test MAE, MSE, RMSE, and R-squared are computed on the held-out rows.

Keeping the seed fixed lets a student reproduce the same split. Changing it
changes which observations are held out, so the metrics can change as well.

## OLS first

Start with **Ordinary Least Squares (OLS)**. It learns an equation of the form:

```text
predicted_price = intercept
                + beta_area * floor_area
                + beta_rooms * rooms
```

OLS chooses the coefficients that minimize the sum of squared residuals on
the training data. A residual is `actual price - predicted price`.

## When to try Ridge

Choose **Ridge regression** when several features convey overlapping
information, such as floor area and number of rooms. Ridge adds a positive
penalty controlled by `alpha` to shrink feature coefficients. The intercept is
not penalized. Compare its test metrics with OLS using the same split before
deciding whether the regularization helped.

## Reading the result

The solution view shows the learned coefficients, metrics for both partitions,
and every actual/predicted/residual value. With exactly one feature, it also
draws the fitted line and distinguishes training points from held-out test
points.

> A low error on this small table is not proof that the relation is causal or
> that it will generalize to future housing markets. It is evidence only for
> the chosen data and evaluation split.
