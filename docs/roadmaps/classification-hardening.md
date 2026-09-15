# Binary Classification Hardening Roadmap

## Document Status

- **State:** planned
- **Workstream:** `CLASS-H`
- **Capability:** `ml.classification.binary_logistic`
- **Evidence source:** imbalanced operational classification with externally
  managed temporal validation and observed non-convergence at default settings
- **Current limitation:** no independent validator, mandatory internal
  stratified holdout, fixed-step gradient descent only, no class weights, and
  no probabilistic or calibration metrics
- **Implementation authorization:** none; a versioned statistical contract must
  be reviewed first

## Goal

Turn the existing educational binary logistic classifier into a rigorously
validated, still transparent local capability suitable for bounded operational
experiments. Preserve honest limits: it remains binary tabular classification,
not AutoML, causal inference, fairness certification, or automatic deployment.

## Contract Direction

The changes are interdependent and require a new reviewed problem/result schema
rather than scattered optional fields with ambiguous version-1 behavior.

Candidate problem concepts are:

- explicit evaluation strategy: `stratified_holdout` or `none`;
- optimizer distinct from the statistical model identity;
- explicit or `balanced` class weights;
- bounded convergence tolerance and iteration budget;
- declared decision threshold, if threshold configurability is accepted.

Candidate result concepts are:

- train and optional test partitions represented honestly;
- convergence and termination diagnostics;
- regularized objective and gradient norm;
- classification and probabilistic metrics with defined undefined states;
- enough prediction and scaling evidence for independent recomputation.

## Phase 0 — Statistical And Versioned Contract (`CLASS-C`)

- [ ] Freeze the regularized binary logistic objective, intercept treatment,
  standardization, probability calculation, and numerical clipping.
- [ ] Define `evaluation.strategy` and the exact no-holdout semantics; do not
  overload `test_fraction = 0` as an undocumented mode.
- [ ] Define explicit-label and `balanced` class-weight formulas and whether
  weighted metrics are reported separately from ordinary sample metrics.
- [ ] Compare fixed-step gradient descent with a maintained convex optimizer
  already compatible with Optees dependencies, initially SciPy L-BFGS.
- [ ] Freeze convergence, iteration-limit, numerical-failure, and finite-
  optimum semantics, including separable unregularized data.
- [ ] Define log-loss, Brier score, ROC-AUC, and average precision, including
  ties, missing classes, clipping, and undefined results.
- [ ] Treat calibration as a separate contract decision covering bin edges,
  empty bins, counts, observed frequency, mean probability, and any aggregate
  calibration error.
- [ ] Decide compatibility and migration between schema v1 and the new version.

**Gate `CLASS-C`:** formulas, schema shapes, tolerances, status mappings, and
reference probes are independently reviewed before engine work.

## Phase 1 — Independent Validator (`CLASS-V`)

- [ ] Register a dedicated validator for the public Classification result.
- [ ] Verify labels, row identity, partition membership, counts, uniqueness,
  and completeness against the original problem.
- [ ] Recompute training-only feature means and scales.
- [ ] Recompute logits, probabilities, thresholded predictions, confusion
  matrices, and every published metric.
- [ ] Recompute regularized loss and gradient from the original training rows,
  coefficients, intercept, scaling, and class weights.
- [ ] Distinguish arithmetic verification from stationarity evidence.
- [ ] Return `partial` when outputs are internally verified but convergence or
  finite-optimum evidence is insufficient; return `failed` for tampering or
  contradictions.
- [ ] Add deliberate tampering tests for every result family and diagnostic.

**Gate `CLASS-V`:** production execution no longer returns `not_available`,
and every validation claim states exactly what was independently recomputed.

## Phase 2 — Evaluation And Optimization (`CLASS-E`)

- [ ] Implement `evaluation.strategy = none` with all rows used for training
  and absent—not fabricated—test evaluation.
- [ ] Preserve deterministic stratified holdout behavior for compatible v1
  requests.
- [ ] Add the selected robust optimizer through the existing solver port.
- [ ] Keep fixed-step gradient descent only if it remains a clearly named,
  tested educational option.
- [ ] Apply class weights consistently to objective, gradient, convergence,
  diagnostics, and validator calculations.
- [ ] Return explicit termination reason, iterations/evaluations, objective,
  gradient norm, and optimizer identifier.
- [ ] Test convergence, iteration limit, separability, constant features,
  severe imbalance, regularization, and numerical overflow boundaries.

**Gate `CLASS-E`:** the new engine is deterministic under its declared inputs,
handles the operational imbalance fixture, and never presents an iteration-
limited candidate as a verified stationary solution.

## Phase 3 — Metrics And Calibration (`CLASS-M`)

- [ ] Add independently recomputed log-loss and Brier score.
- [ ] Add ROC-AUC with a frozen tie-handling rule.
- [ ] Add average precision for imbalanced datasets.
- [ ] Preserve threshold metrics and confusion matrices separately from
  probability-quality metrics.
- [ ] Add calibration bins and an aggregate calibration measure only after the
  calibration contract is accepted.
- [ ] Require minimum sample evidence and explicit warnings before presenting a
  sparse calibration diagram.
- [ ] Extend canonical tables and headless charts without truncating or
  relabelling authoritative values.

**Gate `CLASS-M`:** every metric has an equation, edge-case policy, independent
recomputation, and deterministic analytic references.

## Phase 4 — Scientific And Operational Evidence (`CLASS-B`)

- [ ] Freeze a small analytic balanced reference before external datasets.
- [ ] Add deterministic imbalanced and no-holdout fixtures derived without
  confidential business data.
- [ ] Audit one redistributable binary-classification dataset for source,
  license, checksum, split protocol, and bounded CI use.
- [ ] Compare optimizers on convergence and objective consistency rather than
  claiming general superiority from one dataset.
- [ ] Publish negative results, undefined metrics, calibration limitations,
  and runtime measurements alongside successful cases.

**Gate `CLASS-B`:** benchmark evidence supports the documented scope but makes
no generalized fairness, causal, or production-readiness claim.

## Phase 5 — Desktop And Consumer Handoff (`CLASS-UI`)

- [ ] Expose evaluation strategy, optimizer, class weights, and bounded
  controls without making the default form overwhelming.
- [ ] Show convergence, validation, threshold, imbalance, and no-holdout
  limitations prominently.
- [ ] Separate threshold metrics, probabilistic metrics, and calibration
  graphics visually and semantically.
- [ ] Keep English and Italian resources synchronized.
- [ ] Publish versioned examples and migration guidance for CLI, REST, MCP, and
  Python consumers.

**Gate `CLASS-UI`:** desktop and headless surfaces preserve the reviewed
contract and pass the same reference and tampering evidence.

## Stop Conditions

Stop if the validator would reuse opaque solver outputs instead of recomputing
them, class weighting changes only the displayed metrics but not training, a
no-holdout run fabricates test evidence, calibration is presented without a
minimum-evidence rule, or v1 compatibility cannot be represented honestly.

## Completion Standard

Classification hardening is complete when convergence and evaluation modes are
explicit, imbalanced training is supported, probabilistic metrics are defined
and independently verified, the public capability returns an honest validation
report, and every delivery surface preserves the same semantics.
