# Continuous Convex Quadratic Programming (QP) Handoff Fixtures

## Overview

This directory contains deterministic reference fixtures, edge cases, and handoff evidence for
continuous convex quadratic programming in Optees (`qp.continuous`).

These fixtures serve as the frozen handoff baseline for downstream consumers, including the
Optees Decision Simulator, enabling independent verification and regression testing without
runtime dependencies on the Optees codebase.

## Supported Mathematical Scope

Optees defines a continuous Quadratic Program in canonical minimization form:

$$\operatorname{minimize}_{x \in \mathbb{R}^n} \quad \frac{1}{2} x^T Q x + c^T x + \alpha$$
$$\text{subject to} \quad A_{eq} x = b_{eq}, \quad A_{ineq} x \le b_{ineq}, \quad l \le x \le u$$

- **Decision variables**: $x \in \mathbb{R}^n$ continuous dense variables with finite or infinite box bounds ($l_j \le x_j \le u_j$).
- **Quadratic objective matrix**: $Q \in \mathbb{R}^{n \times n}$ symmetric positive semi-definite (PSD) Hessian matrix ($Q \succeq 0$).
- **Linear coefficients**: $c \in \mathbb{R}^n$ linear cost vector.
- **Offset**: $\alpha \in \mathbb{R}$ scalar constant offset (default $0.0$).
- **Constraints**: Optional linear equality ($A_{eq} x = b_{eq}$) and linear inequality ($A_{ineq} x \le b_{ineq}$) constraints.
- **Maximization**: Supported by negating objective coefficients to equivalent minimization of $-\frac{1}{2} x^T Q x - c^T x - \alpha$ where $Q \preceq 0$ (negative semi-definite).

### The $\frac{1}{2}$ Factor Objective Convention

The objective formulation uses the explicit $\frac{1}{2}$ factor:
$$f(x) = \frac{1}{2} x^T Q x + c^T x + \alpha$$
Under this convention, $\nabla f(x) = Q x + c$ and $\nabla^2 f(x) = Q$. Diagonal elements contribute $\frac{1}{2} Q_{ii} x_i^2$, and symmetric off-diagonal elements contribute $Q_{ij} x_i x_j$.

## Covered Files and Location

The manifest (`manifest.json`) catalogs all covered files using repository-root relative paths (`path_base: "repository_root"`):

1. **`tests/data/qp/reference_cases.json`**:
   - Analytical reference cases:
     - `unconstrained_interior_optimum`: strictly convex 2D unconstrained problem with interior optimum ($x^* = (2/3, 8/3)$).
     - `constrained_boundary_optimum`: boundary optimum with active inequality constraint $x_1 + x_2 \ge 2$.
     - `concave_maximization`: concave quadratic maximization problem with box bounds.
     - `equality_and_inequality_box`: combined linear equality, inequality, and box bounds.
   - Mathematical edge cases without primal candidates:
     - `infeasible_problem`: contradictory linear constraints yielding empty feasible set (`mathematical_status: "infeasible"`).
     - `unbounded_problem`: linear descent direction with zero quadratic curvature and no upper bound (`mathematical_status: "unbounded"`).
   - Independent validation expectations:
     - `verified`: candidate satisfies bounds, constraints, and KKT first-order optimality conditions within tolerances.
     - `partial`: the available primal checks pass, but dual data is absent and
       the independent KKT/stationarity check is not performed. This status
       alone does not certify optimality, including for an interior candidate.
     - `not_available`: no primal candidate is available for independent validation (infeasible or unbounded).

2. **`examples/qp_resource_allocation_2variables.json`**:
   - Standalone problem definition demonstrating resource allocation with equality budget constraint $\sum w_i = 1$ and box bounds $0 \le w_i \le 1$.
   - This file is an input specification example, not a golden expected result artifact. When solved with default options, it converges to an optimal solution with status `optimal`.

3. **`tests/data/qp/README.md`**:
   - This normative documentation describing scope, conventions, tolerances, and verification procedures.

## Numerical Comparison Rules and Tolerances

- **Floating-point comparisons**:
  Continuous optimization results (`objective`, variable values, dual multipliers, KKT residuals) are subject to floating-point solver tolerances. Assertions in reference tests use relative and absolute tolerances (`abs=1e-4, rel=1e-4`), matching `test_qp_reference_cases.py`.
- **No bitwise cross-platform guarantee**:
  The reference solver backend (OSQP) uses operator splitting (ADMM). Solutions may vary slightly across operating systems, CPU architectures, and BLAS/LAPACK implementations within solver convergence criteria (`tolerance: 1e-7`).

## Required Environment and Backend

- **Backend**: OSQP (`osqp>=0.6.3,<1.0`) on Python 3.12+.
- **Missing dependency failure**:
  When OSQP is not installed, Optees reports an explicit, honest dependency failure:
  - In discovery: `available: false`, `unavailable_reason: "OSQP is required by the continuous convex QP backend."`.
  - In job execution: status `failed` with error code `dependency_unavailable`.

## Checksum Verification

Every file in the bundle is listed in `manifest.json`.

1. **Individual file hashes**:
   Each digest is a lowercase SHA-256 computed over raw file bytes from the repository root:
   ```bash
   sha256sum examples/qp_resource_allocation_2variables.json tests/data/qp/README.md tests/data/qp/reference_cases.json
   ```
2. **Aggregate manifest hash**:
   The `aggregate_sha256` in `manifest.json` is computed as the SHA-256 digest of the lexicographically ordered file entries formatted as:
   ```
   <sha256>  <relative_path>\n
   ```
   The manifest file itself is not included in its own digest calculation.

## Downstream Consumer Guidelines

Consumers (such as the Decision Simulator) should:
1. Copy the covered files (`reference_cases.json`, `examples/qp_resource_allocation_2variables.json`, `README.md`, `manifest.json`).
2. Record the fixture baseline commit (`1f3b45de0d75ddcfb239a8867d48b4926b3264ab`) and Optees version (`0.10.2`) as evidence provenance.
3. Separately record the actual executable version, commit, solver backend, and options used in runs.
4. Verify file bytes against the recorded SHA-256 digests in `manifest.json`.
5. Run independent evaluations without importing internal Optees Python modules.
