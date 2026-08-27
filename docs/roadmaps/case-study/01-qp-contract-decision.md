# Convex QP Contract Decision Plan

## Work Unit

- **ID:** `OPT-DS-01`
- **State:** completed
- **Type:** contract and backend decision; no production implementation
- **Parent roadmap:** `ROADMAP.md`
- **Contract document:** `docs/contracts/quadratic-programming-contract.md`
- **Gate reached:** `QP-C`

## Objective

Produce a reviewed, implementation-ready version 1 contract for a general
convex Quadratic Programming capability. The work unit resolves the
mathematical, numerical, architectural, validation, dependency, packaging, and
public-JSON decisions before domain or solver code is added in `OPT-DS-02`.

---

## Resolved Decisions

### 1. Mathematical Scope and Convention

- **Formulation:** Canonical continuous convex QP in minimization form:
  \[
  \min_{x \in \mathbb{R}^n} \quad \frac{1}{2} x^T Q x + c^T x + \alpha \quad \text{s.t.} \quad A_{eq} x = b_{eq}, \; A_{ineq} x \le b_{ineq}, \; l \le x \le u
  \]
- **Factor $\frac{1}{2}$ convention:** The factor $\frac{1}{2}$ is explicit in front of the quadratic term. The supplied matrix $Q$ directly represents the Hessian $\nabla^2 f(x) = Q$.
- **Sense:**
  - `sense: "min"`: Solves convex minimization. Requires $Q \succeq 0$.
  - `sense: "max"`: Represents concave quadratic maximization. Requires $-Q \succeq 0$ ($Q \preceq 0$). If $Q$ has strictly positive eigenvalues, it is rejected during validation with `qp.non_concave_quadratic_matrix`. Solver internally minimizes $\frac{1}{2} x^T (-Q) x - c^T x - \alpha$ and maps the optimal objective value back via $f_{max}^* = -f_{min}^*$.
- **Symmetry check and tolerance:** $Q$ must be symmetric within $\varepsilon_{sym} = 10^{-8} \max(1, \max_{i,j}|Q_{ij}|)$. Asymmetry exceeding tolerance is rejected with `qp.asymmetric_quadratic_matrix`. Within tolerance, matrix is symmetrized as $Q_{sym} = \frac{1}{2}(Q + Q^T)$.
- **PSD check and tolerance:** Minimum eigenvalue must satisfy $\lambda_{\min}(Q) \ge -\varepsilon_{psd}$ with $\varepsilon_{psd} = 10^{-8} \max(1, \max_{i,j}|Q_{ij}|)$. If $\lambda_{\min} < -\varepsilon_{psd}$, the problem is rejected with `qp.non_convex_quadratic_matrix`. A matrix accepted within tolerance is passed to the backend after symmetry canonicalization without silently projecting its eigenvalues.
- **Variable ordering:** An ordered `variables` array defines indices $0 \dots n-1$. Vectors $c, l, u$ and matrices $Q, A$ bind strictly to this declared order.

### 2. Public Contract and Schemas

- **Capability ID:** `qp.continuous`
- **Title:** `Continuous convex quadratic programming`
- **Problem Type:** `quadratic_programming`
- **Contract / Schema versions:** `contract_version: "1"`, `problem_schema_version: "1"`, `result_schema_version: "1"`.
- **Default options & limits:** `method: "osqp"` is the only v1 backend token; `tolerance: 1e-7`, `max_iterations: 4000`, `time_limit_seconds: 60.0`. Limits: $n \le 500$ variables (dense matrix), $m \le 1000$ constraints, body size $\le 10\text{ MB}$.
- **Public statuses:**
  - `job_status`: `queued`, `running`, `completed`, `cancelled`, `failed`
  - `mathematical_status`: `optimal`, `feasible`, `infeasible`, `unbounded`, `not_solved`
  - `termination_reason`: `completed`, `time_limit`, `iteration_limit`, `cancelled`, `dependency_failure`, `internal_error`
  - `validation`: `verified`, `partial`, `failed`, `not_available`
- **Complete schema definitions & examples:** Detailed in `docs/contracts/quadratic-programming-contract.md`.

### 3. Independent Solution Validation

- Validator `QPIndependentSolutionValidator` independently checks:
  1. `qp.variable_vector`: exactly $n$ finite floats matching declared names.
  2. `qp.bounds`: variable lower/upper bounds within $\varepsilon_{feas} = 10^{-7}$.
  3. `qp.constraints`: linear equality/inequality constraints within $\varepsilon_{feas} = 10^{-7}$.
  4. `qp.objective`: independent recomputation of $\frac{1}{2} (x^*)^T Q x^* + c^T x^* + \alpha$ vs reported objective within $\varepsilon_{abs} + \varepsilon_{rel} |f| = 10^{-7}$.
  5. `qp.kkt_stationarity` (when dual multipliers are available): stationarity residual $\| Q x^* + c + A^T y - z_l + z_u \|_\infty$ and complementary slackness.
- Explicit validator limitations are documented.

### 4. Backend Evaluation and Evidence

- Evaluated candidates: OSQP, Clarabel, SciPy (SLSQP/trust-constr), HiGHS (`highspy`), CVXOPT, ProxQP.
- **Selected v1 backend direction:** `osqp`, based on its Apache-2.0 license, QP/status API, sparse CSC input, warm starts, runtime limit, and published Python 3.12 wheels for the Optees release targets.
- **Alternative retained for later evaluation:** `clarabel`; it is not an automatic fallback because its status and numerical semantics differ.
- **Comparison probe only:** SciPy SLSQP/trust-constr; it is not a production fallback.
- **Packaging and repeatability boundary:** neither OSQP nor Clarabel was installed or packaged in this work unit. `OPT-DS-02` must pin the dependency, verify status mappings and measure the three release artifacts before the runtime dependency is accepted.
- **Cancellation:** v1 advertises `supports_cancellation: false` unless the implementation proves a safe interrupt or isolated-worker boundary.

### 5. Future Compatibility and Educational Slice

- Future schema version `2` or compatible extensions will support sparse COO/CSC triplets without breaking dense schema v1.
- Warm-starting is supported by OSQP (`warm_start(x, y)`).
- Convex MIQP (`OPT-DS-05`) will reuse the identical objective convention and port structure by adding variable integer/binary domains.
- Minimum educational vertical slice (`OPT-DS-02`) defines formulation table, matrix editor, solution view, 2D contour visualization, bilingual EN/IT terms, and Maros-Mészáros benchmark path.

---

## Verification Evidence

All numerical checks and contract invariants are verified by automated tests in `tests/utility/test_qp_contract_decision_probes.py`:

- [x] Interior unconstrained optimum analytical recomputation: $x^* = (2/3, 8/3)^T$, $f(x^*) = -28/3$.
- [x] Boundary constrained optimum analytical recomputation: $x^* = (1, 1)^T$, $f(x^*) = 1.0$.
- [x] Concave maximization transformation and analytical recomputation: $x^* = (2, 3)^T$, $f(x^*) = 13.0$.
- [x] Matrix asymmetry rejection beyond the scaled max-entry tolerance, mapped to `qp.asymmetric_quadratic_matrix`.
- [x] Non-PSD matrix rejection beyond the scaled max-entry tolerance, mapped to `qp.non_convex_quadratic_matrix`.
- [x] Infeasible problem detection via Farkas certificate ray.
- [x] Unbounded problem detection via dual infeasibility recession ray.
- [x] Independent validation arithmetic checks (vector, bounds, constraints, objective, KKT stationarity).
- [x] Structural validation of all JSON contract examples in `docs/contracts/quadratic-programming-contract.md`.
- [x] Markdown documentation links test (`tests/test_documentation_links.py`).
- [x] `git diff --check`.

---

## Gate `QP-C` Status

**Gate `QP-C` is achieved.** The public contract is frozen in
`docs/contracts/quadratic-programming-contract.md` and can be reviewed
independently of any GUI, transport, or domain-specific application. No
production solver code is added in this work unit.
