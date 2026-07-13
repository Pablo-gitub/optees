# How Binary Classification Works

## The modeling question

Binary classification learns from examples with one of two known labels. Each
observation has numeric features `x_i` and a categorical target `y_i`, for
example `no`/`yes`, `negative`/`positive`, or `not_spam`/`spam`.

The first Optees workflow intentionally accepts only two non-empty string
labels and finite numeric features. It does not perform text classification,
multiclass classification, missing-value imputation, automatic feature
selection, or causal inference.

## Logistic score and probability

For standardized feature vector `z_i`, logistic regression forms a linear
score:

```text
s_i = beta_0 + beta_1 z_i1 + ... + beta_p z_ip
```

and turns it into the probability of the positive label with the sigmoid:

```text
p_i = 1 / (1 + exp(-s_i))
```

Optees assigns the positive label when `p_i >= 0.5`; otherwise it assigns the
negative label. The positive label is the second label after alphabetical
sorting. A probability is a model output conditioned on this dataset and its
assumptions, not a guarantee about an individual case.

## Training objective

On training rows only, the implementation minimizes the regularized logistic
loss:

```text
mean_i[-y_i log(p_i) - (1-y_i) log(1-p_i)] + 0.5 * alpha * sum_j beta_j^2
```

Here the labels are encoded as `0` and `1`. The L2 term controlled by `alpha`
discourages large feature coefficients; the intercept is not penalized.
Optees uses deterministic full-batch gradient descent. The learning rate and
iteration limit control that numerical process. Convergence means the
algorithm's gradient criterion was met, not that the model is universally
correct.

## Honest evaluation

Before fitting, rows are split stratified by label using the configured seed.
Feature means and scales are computed **only on the training partition**, then
applied to test rows. This prevents test information from leaking into the
model fit.

- **Accuracy**: proportion of all correct predictions.
- **Precision**: proportion of predicted positives that were actually
  positive.
- **Recall**: proportion of actual positives that were found.
- **F1**: harmonic balance between precision and recall.

The confusion matrix makes the four outcomes explicit: true negative, false
positive, false negative, and true positive. Accuracy alone can be misleading,
especially when one class is rare. Compare training and test results, inspect
both error types, and use repeated validation for serious work.
