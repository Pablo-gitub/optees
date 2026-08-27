# Continuous Convex Quadratic Programming Contract

## Document Status

- **Work Unit:** `OPT-DS-01`
- **Gate:** `QP-C`
- **State:** frozen specification
- **Capability ID:** `qp.continuous`
- **Contract Version:** `1`
- **Problem Schema Version:** `1`
- **Result Schema Version:** `1`
- **Implementation Status:** planned for `OPT-DS-02`; no production solver code in this work unit.

This contract freezes the mathematical formulation, public JSON DTOs,
validation guarantees, status semantics, and backend selection for the general
continuous convex Quadratic Programming (QP) capability in Optees.

---

## 1. Mathematical Formulation

### 1.1 Canonical Optimization Problem

Optees defines a continuous Quadratic Program in canonical minimization form as:

\[
\begin{aligned}
\operatorname{minimize}_{x \in \mathbb{R}^n} \quad & \frac{1}{2} x^T Q x + c^T x + \alpha \\
\text{subject to} \quad & A_{eq} x = b_{eq} \\
& A_{ineq} x \le b_{ineq} \\
& l \le x \le u
\end{aligned}
\]

where:

- $x = (x_1, x_2, \dots, x_n)^T \in \mathbb{R}^n$ is the vector of continuous decision variables.
- $Q \in \mathbb{R}^{n \times n}$ is a symmetric positive semi-definite (PSD) Hessian matrix ($Q \succeq 0$).
- $c \in \mathbb{R}^n$ is the linear objective coefficient vector.
- $\alpha \in \mathbb{R}$ is a scalar objective offset (default $0.0$).
- $A_{eq} \in \mathbb{R}^{m_{eq} \times n}$ and $b_{eq} \in \mathbb{R}^{m_{eq}}$ define linear equality constraints.
- $A_{ineq} \in \mathbb{R}^{m_{ineq} \times n}$ and $b_{ineq} \in \mathbb{R}^{m_{ineq}}$ define linear inequality constraints.
- $l \in (\mathbb{R} \cup \{-\infty\})^n$ and $u \in (\mathbb{R} \cup \{+\infty\})^n$ define lower and upper box bounds on variables.

### 1.2 The Factor $1/2$ Convention

The objective uses the explicit $\frac{1}{2}$ factor in front of the quadratic
form:

\[
f(x) = \frac{1}{2} x^T Q x + c^T x + \alpha = \frac{1}{2} \sum_{i=1}^n \sum_{j=1}^n Q_{ij} x_i x_j + \sum_{i=1}^n c_i x_i + \alpha
\]

Under this convention:

- The gradient of $f(x)$ is $\nabla f(x) = Q x + c$.
- The Hessian of $f(x)$ is $\nabla^2 f(x) = Q$.
- The pure quadratic term for variable $x_i$ is $\frac{1}{2} Q_{ii} x_i^2$.
- The bilinear cross-term for $x_i x_j$ ($i \ne j$) with symmetric $Q$ ($Q_{ij} = Q_{ji}$) contributes $\frac{1}{2}(Q_{ij} x_i x_j + Q_{ji} x_j x_i) = Q_{ij} x_i x_j$.

Callers supply the matrix $Q$ directly representing the Hessian matrix.

### 1.3 Variable Ordering and Binding

- Decision variables are declared in an ordered `variables` array.
- The 0-based index $i \in \{0, \dots, n-1\}$ defines the position of variable $x_i$.
- Linear coefficient vectors $c$, constraint coefficient rows $A_k$, and quadratic matrix rows/columns $Q_{ij}$ bind strictly to this declared variable sequence.
- Variable names must be non-empty strings and unique within the problem.

### 1.4 Linear Relations and Variable Bounds

Constraints and bounds reuse the standard Optees linear conventions:

- Variable bounds use `"lb"` and `"ub"`. A `null` value denotes unbounded ($-\infty$ for lower bound, $+\infty$ for upper bound).
- Linear constraints declare `"coefficients"` (array of length $n$), `"relation"` (`"<="`, `"="`, or `">="`), and scalar `"rhs"`.
- Inequalities with `">="` ($\sum_j A_{kj} x_j \ge b_k$) are normalized to $\le$ by $-A_k x \le -b_k$ when required by backends.

### 1.5 Objective Sense: Convex Minimization and Concave Maximization

Schema version `1` supports both `"min"` and `"max"` objective senses:

1. **Minimization (`sense: "min"`)**:
   - Solves $\min \frac{1}{2} x^T Q x + c^T x + \alpha$.
   - Requires $Q$ to be positive semi-definite ($Q \succeq 0$).
2. **Maximization (`sense: "max"`)**:
   - Represents the concave maximization problem $\max \frac{1}{2} x^T Q_{user} x + c_{user}^T x + \alpha_{user}$.
   - For this problem to be concave and well-posed, the Hessian $Q_{user}$ must be negative semi-definite ($Q_{user} \preceq 0$, i.e. $-Q_{user} \succeq 0$).
   - If $Q_{user}$ has any strictly positive eigenvalue ($\lambda_{\max}(Q_{user}) > \varepsilon_{psd}$), the problem is non-concave and is rejected before solve with error `non_concave_quadratic_matrix`.
   - The solver adapter transforms the problem into equivalent convex minimization with $Q_{internal} = -Q_{user}$, $c_{internal} = -c_{user}$, $\alpha_{internal} = -\alpha_{user}$.
   - The reported optimal objective value is restored as $f_{max}^* = -f_{internal}^* = \frac{1}{2} (x^*)^T Q_{user} x^* + c_{user}^T x^* + \alpha_{user}$.

Non-convex quadratic problems (e.g. indefinite $Q$ for minimization or maximization) are strictly out of scope for capability `qp.continuous` and are rejected during validation.

### 1.6 Symmetry and Positive Semi-Definiteness (PSD) Tolerances

Before execution, $Q$ undergoes strict numerical validation:

- **Symmetry check**:
  \[
  \Delta_{sym} = \max_{i, j} |Q_{ij} - Q_{ji}| \le \varepsilon_{sym} = 10^{-8} \cdot \max(1.0, \|Q\|_\infty)
  \]
  If $\Delta_{sym} > \varepsilon_{sym}$, the problem is rejected with error `invalid_quadratic_matrix`.
  If $\Delta_{sym} \le \varepsilon_{sym}$, the matrix is canonicalized as $Q_{sym} = \frac{1}{2}(Q + Q^T)$.
- **Positive Semi-Definiteness (PSD) check**:
  The minimum eigenvalue $\lambda_{\min}(Q_{sym})$ is computed via symmetric eigenvalue decomposition.
  \[
  \lambda_{\min}(Q_{sym}) \ge -\varepsilon_{psd}, \quad \text{where } \varepsilon_{psd} = 10^{-8} \cdot \max(1.0, \|Q_{sym}\|_\infty)
  \]
  - If $\lambda_{\min}(Q_{sym}) < -\varepsilon_{psd}$, the matrix is non-convex and rejected with error `non_convex_quadratic_matrix`.
  - If $-\varepsilon_{psd} \le \lambda_{\min}(Q_{sym}) < 0$ (numerical rounding of a semi-definite matrix), the negative eigenvalues are clamped to $0$ ($Q_{psd} = V \max(0, \Lambda) V^T$) to guarantee stability across backends.

---

## 2. Public Contract and Versioned Schemas

### 2.1 Capability Identity

- **Capability ID:** `qp.continuous`
- **Title:** `Continuous convex quadratic programming`
- **Problem Type:** `quadratic_programming`
- **Contract Version:** `1`
- **Problem Schema Version:** `1`
- **Result Schema Version:** `1`
- **Primary Backend Candidate:** `osqp`
- **Secondary Backend Candidates:** `clarabel`, `scipy_slsqp`
- **Supports Time Limit:** `true`
- **Supports Cancellation:** `true`

### 2.2 Default Options and Resource Limits

| Parameter | Default | Allowed Range / Bound | Description |
| --- | --- | --- | --- |
| `method` | `"osqp"` | `["osqp", "clarabel", "scipy_slsqp"]` | Selected solver backend engine |
| `tolerance` | `1e-7` | `[1e-12, 1e-2]` | Primal and dual convergence tolerance |
| `max_iterations` | `4000` | `[10, 100000]` | Maximum solver iterations |
| `time_limit_seconds` | `60.0` | `[0.1, 300.0]` | Wall-clock execution timeout |
| Max Variables $n$ | — | $1 \le n \le 500$ | Dense $n \times n$ matrix dimension |
| Max Constraints $m$ | — | $0 \le m \le 1000$ | Total linear constraints |
| Max Payload Size | — | $10\text{ MB}$ | JSON string body limit |

### 2.3 Public Problem JSON Schema (`schema_version: "1"`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ContinuousConvexQPProblem",
  "type": "object",
  "required": ["version", "variables", "objective"],
  "properties": {
    "version": {
      "const": "1",
      "description": "Continuous QP problem schema version."
    },
    "problem_type": {
      "type": "string",
      "enum": ["quadratic_programming"],
      "default": "quadratic_programming"
    },
    "variables": {
      "type": "array",
      "minItems": 1,
      "maxItems": 500,
      "description": "Ordered decision variables defining vector indices 0..n-1.",
      "items": {
        "type": "object",
        "required": ["name", "lb", "ub"],
        "properties": {
          "name": {
            "type": "string",
            "minLength": 1,
            "description": "Unique variable identifier."
          },
          "label": {
            "type": "string",
            "description": "Optional human-readable variable label."
          },
          "lb": {
            "type": ["number", "null"],
            "description": "Finite lower bound or null for -infinity."
          },
          "ub": {
            "type": ["number", "null"],
            "description": "Finite upper bound or null for +infinity."
          }
        }
      }
    },
    "objective": {
      "type": "object",
      "required": ["sense", "linear_coefficients", "quadratic_matrix"],
      "description": "Quadratic objective: 0.5 * x^T * Q * x + c^T * x + offset.",
      "properties": {
        "sense": {
          "type": "string",
          "enum": ["min", "max"],
          "description": "min for convex minimization; max for concave maximization."
        },
        "linear_coefficients": {
          "type": "array",
          "minItems": 1,
          "maxItems": 500,
          "items": {"type": "number"},
          "description": "Linear term vector c of length n."
        },
        "quadratic_matrix": {
          "type": "array",
          "minItems": 1,
          "maxItems": 500,
          "description": "Dense n x n Hessian matrix Q.",
          "items": {
            "type": "array",
            "minItems": 1,
            "maxItems": 500,
            "items": {"type": "number"}
          }
        },
        "offset": {
          "type": "number",
          "default": 0.0,
          "description": "Scalar constant offset alpha added to the objective."
        }
      }
    },
    "constraints": {
      "type": "array",
      "default": [],
      "maxItems": 1000,
      "description": "Linear equality and inequality constraints.",
      "items": {
        "type": "object",
        "required": ["coefficients", "relation", "rhs"],
        "properties": {
          "name": {
            "type": "string",
            "description": "Optional constraint label."
          },
          "coefficients": {
            "type": "array",
            "minItems": 1,
            "maxItems": 500,
            "items": {"type": "number"},
            "description": "Row coefficient vector of length n."
          },
          "relation": {
            "type": "string",
            "enum": ["<=", "=", ">="]
          },
          "rhs": {
            "type": "number",
            "description": "Right-hand side scalar."
          }
        }
      }
    },
    "solver_options": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "enum": ["osqp", "clarabel", "scipy_slsqp"],
          "default": "osqp"
        },
        "tolerance": {
          "type": "number",
          "default": 1e-7
        },
        "max_iterations": {
          "type": "integer",
          "minimum": 10,
          "maximum": 100000,
          "default": 4000
        },
        "time_limit_seconds": {
          "type": "number",
          "minimum": 0.1,
          "maximum": 300.0,
          "default": 60.0
        }
      }
    }
  }
}
```

### 2.4 Public Result JSON Schema (`schema_version: "1"`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ContinuousConvexQPResult",
  "type": "object",
  "required": ["objective", "objective_sense", "variables"],
  "properties": {
    "objective": {
      "type": ["number", "null"],
      "description": "Optimal objective value, or null if no primal solution is available."
    },
    "objective_sense": {
      "type": "string",
      "enum": ["min", "max"]
    },
    "variables": {
      "type": "array",
      "description": "Optimal variable values in declared variable order.",
      "items": {
        "type": "object",
        "required": ["name", "value"],
        "properties": {
          "name": {"type": "string"},
          "value": {"type": "number"}
        }
      }
    },
    "dual_values": {
      "type": ["object", "null"],
      "description": "Dual multipliers if available from backend.",
      "properties": {
        "constraints": {
          "type": "array",
          "items": {"type": "number"}
        },
        "lower_bounds": {
          "type": "array",
          "items": {"type": "number"}
        },
        "upper_bounds": {
          "type": "array",
          "items": {"type": "number"}
        }
      }
    },
    "kkt_residuals": {
      "type": ["object", "null"],
      "description": "Primal, dual, and complementarity residuals.",
      "properties": {
        "primal_residual": {"type": "number"},
        "dual_residual": {"type": "number"},
        "duality_gap": {"type": "number"},
        "complementarity_residual": {"type": "number"}
      }
    }
  }
}
```

### 2.5 Status Semantics and Termination Reasons

Execution adheres to the standard Optees execution envelope:

- **`job_status`**: `completed`, `cancelled`, or `failed`.
- **`mathematical_status`**:
  - `optimal`: Global optimum found satisfying KKT optimality conditions within tolerance.
  - `feasible`: Feasible candidate produced (e.g. at time limit or iteration limit).
  - `infeasible`: Mathematically proven infeasible (no candidate satisfies linear constraints and bounds).
  - `unbounded`: Proven unbounded below for minimization / unbounded above for maximization.
  - `not_solved`: Solver failed due to numerical instability or divergence.
- **`termination_reason`**: `completed`, `time_limit`, `iteration_limit`, `cancelled`, `dependency_failure`, `internal_error`.
- **`validation`**: `verified`, `partial`, `failed`, `not_available`.

---

## 3. Complete JSON Examples

### 3.1 Valid Example 1: Interior Strictly Convex QP

Unconstrained problem with $Q = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}$, $c = \begin{pmatrix} -4 \\ -6 \end{pmatrix}$:
\[
\min \frac{1}{2} (2 x_1^2 + 2 x_2^2 + 2 x_1 x_2) - 4 x_1 - 6 x_2
\]
Analytical optimum: $x^* = (2/3, 8/3)^T \approx (0.66666667, 2.66666667)^T$, $f(x^*) = -28/3 \approx -9.33333333$.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "label": "Variable 1", "lb": null, "ub": null},
    {"name": "x2", "label": "Variable 2", "lb": null, "ub": null}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [-4.0, -6.0],
    "quadratic_matrix": [
      [2.0, 1.0],
      [1.0, 2.0]
    ],
    "offset": 0.0
  },
  "constraints": []
}
```

### 3.2 Valid Example 2: Boundary Constrained Convex QP

Problem: $\min \frac{1}{2}(x_1^2 + x_2^2)$ subject to $x_1 + x_2 \ge 2$, $x_1 \ge 0, x_2 \ge 0$.
Analytical optimum: $x^* = (1.0, 1.0)^T$, $f(x^*) = 1.0$.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "label": "X1", "lb": 0.0, "ub": null},
    {"name": "x2", "label": "X2", "lb": 0.0, "ub": null}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [0.0, 0.0],
    "quadratic_matrix": [
      [1.0, 0.0],
      [0.0, 1.0]
    ],
    "offset": 0.0
  },
  "constraints": [
    {
      "name": "sum_bound",
      "coefficients": [1.0, 1.0],
      "relation": ">=",
      "rhs": 2.0
    }
  ]
}
```

### 3.3 Valid Example 3: Concave Maximization QP

Problem: $\max -\frac{1}{2}(2 x_1^2 + 2 x_2^2) + 4 x_1 + 6 x_2$ subject to $x_1 \ge 0, x_2 \ge 0$.
$Q = \begin{pmatrix} -2 & 0 \\ 0 & -2 \end{pmatrix} \preceq 0$ (negative definite).
Analytical optimum: $x^* = (2.0, 3.0)^T$, $f(x^*) = 13.0$.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "label": "X1", "lb": 0.0, "ub": null},
    {"name": "x2", "label": "X2", "lb": 0.0, "ub": null}
  ],
  "objective": {
    "sense": "max",
    "linear_coefficients": [4.0, 6.0],
    "quadratic_matrix": [
      [-2.0, 0.0],
      [0.0, -2.0]
    ],
    "offset": 0.0
  },
  "constraints": []
}
```

### 3.4 Invalid Example 1: Dimension Mismatch

$n=2$ variables declared, but `linear_coefficients` has length 3 and $Q$ is $3 \times 3$.
Rejected with error `dimension_mismatch`.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "lb": 0.0, "ub": 10.0},
    {"name": "x2", "lb": 0.0, "ub": 10.0}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [1.0, 2.0, 3.0],
    "quadratic_matrix": [
      [1.0, 0.0, 0.0],
      [0.0, 1.0, 0.0],
      [0.0, 0.0, 1.0]
    ],
    "offset": 0.0
  },
  "constraints": []
}
```

### 3.5 Invalid Example 2: Asymmetric Quadratic Matrix

$Q_{12} = 3.0 \ne Q_{21} = 1.0$, $|Q_{12} - Q_{21}| = 2.0 > 10^{-8}$.
Rejected with error `invalid_quadratic_matrix`.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "lb": 0.0, "ub": null},
    {"name": "x2", "lb": 0.0, "ub": null}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [0.0, 0.0],
    "quadratic_matrix": [
      [2.0, 3.0],
      [1.0, 2.0]
    ],
    "offset": 0.0
  },
  "constraints": []
}
```

### 3.6 Invalid Example 3: Non-PSD / Indefinite Matrix

$Q = \begin{pmatrix} 1 & 2 \\ 2 & 1 \end{pmatrix}$, eigenvalues $\lambda = \{3, -1\}$.
$\lambda_{\min} = -1.0 < -10^{-8}$.
Rejected with error `non_convex_quadratic_matrix`.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "lb": 0.0, "ub": null},
    {"name": "x2", "lb": 0.0, "ub": null}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [0.0, 0.0],
    "quadratic_matrix": [
      [1.0, 2.0],
      [2.0, 1.0]
    ],
    "offset": 0.0
  },
  "constraints": []
}
```

### 3.7 Infeasible Problem Example

Constraints $x_1 + x_2 \le 1$ and $x_1 + x_2 \ge 3$ for $x \ge 0$.
Executed to completion with `mathematical_status: "infeasible"`.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "lb": 0.0, "ub": null},
    {"name": "x2", "lb": 0.0, "ub": null}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [0.0, 0.0],
    "quadratic_matrix": [
      [1.0, 0.0],
      [0.0, 1.0]
    ],
    "offset": 0.0
  },
  "constraints": [
    {"name": "upper_sum", "coefficients": [1.0, 1.0], "relation": "<=", "rhs": 1.0},
    {"name": "lower_sum", "coefficients": [1.0, 1.0], "relation": ">=", "rhs": 3.0}
  ]
}
```

### 3.8 Unbounded Problem Example

$Q = \begin{pmatrix} 1 & 0 \\ 0 & 0 \end{pmatrix} \succeq 0$, $c = \begin{pmatrix} 0 \\ -2 \end{pmatrix}$, $x_1 \ge 0, x_2 \ge 0$.
As $x_2 \to +\infty$, $f(x) \to -\infty$.
Executed with `mathematical_status: "unbounded"`.

```json
{
  "version": "1",
  "problem_type": "quadratic_programming",
  "variables": [
    {"name": "x1", "lb": 0.0, "ub": null},
    {"name": "x2", "lb": 0.0, "ub": null}
  ],
  "objective": {
    "sense": "min",
    "linear_coefficients": [0.0, -2.0],
    "quadratic_matrix": [
      [1.0, 0.0],
      [0.0, 0.0]
    ],
    "offset": 0.0
  },
  "constraints": []
}
```

---

## 4. Independent Solution Validation

Independent post-solve validation recomputes mathematical properties directly
from the input model and candidate solution vector without trusting solver status flags.

### 4.1 Validation Checks

`QPIndependentSolutionValidator` performs the following checks:

1. **`qp.variable_vector`**:
   - Verifies that `variables` in the result contains exactly $n$ finite floats corresponding 1-to-1 with the model's declared variables.
2. **`qp.bounds`**:
   - For every variable $i$, verifies $l_i - \text{allowed} \le x_i^* \le u_i + \text{allowed}$.
   - Records $\max_i \text{violation}_i$.
3. **`qp.constraints`**:
   - For every linear constraint row $k$:
     - Relation `< =`: $\sum_j A_{kj} x_j^* \le b_k + \text{allowed}$.
     - Relation `>`: $\sum_j A_{kj} x_j^* \ge b_k - \text{allowed}$.
     - Relation `=`: $|\sum_j A_{kj} x_j^* - b_k| \le \text{allowed}$.
   - Records $\max_k \text{violation}_k$.
4. **`qp.objective`**:
   - Independently recalculates $f_{recomputed} = \frac{1}{2} (x^*)^T Q x^* + c^T x^* + \alpha$.
   - Compares with reported objective: $|f_{reported} - f_{recomputed}| \le \varepsilon_{abs} + \varepsilon_{rel} \max(|f_{reported}|, |f_{recomputed}|)$.
5. **`qp.kkt_stationarity`** (evaluated when dual multipliers are reported):
   - Stationarity residual: $r_{stat} = \| Q x^* + c + A_{eq}^T y_{eq} + A_{ineq}^T y_{ineq} - z_{lb} + z_{ub} \|_\infty$.
   - Complementary slackness: $\max_k |y_{ineq, k} (A_{ineq, k} x^* - b_{ineq, k})| \le \varepsilon_{kkt}$.
   - Dual non-negativity: $y_{ineq} \ge -\varepsilon_{kkt}$, $z_{lb} \ge -\varepsilon_{kkt}$, $z_{ub} \ge -\varepsilon_{kkt}$.

### 4.2 Validation Tolerances

- `absolute_tolerance`: $1.0 \times 10^{-7}$
- `relative_tolerance`: $1.0 \times 10^{-7}$
- `feasibility_tolerance`: $1.0 \times 10^{-7}$
- `kkt_tolerance`: $1.0 \times 10^{-6}$

### 4.3 Honest Validator Limitations

The validation report explicitly states:

- *"Feasibility, objective consistency, and local KKT satisfaction do not independently prove global optimality if the quadratic matrix is not positive semi-definite."*
- *"The independent validator does not verify whether the mathematical formulation reflects the business or domain intent."*

---

## 5. Backend Evaluation and Evidence

### 5.1 Evaluated Candidates

We evaluated candidate engines using primary documentation, license audits,
Python 3.12 compatibility, and numerical test probes:

1. **OSQP (Operator Splitting Quadratic Program solver)**
   - *Version evaluated:* 0.6.3+ / 1.0.0b
   - *Algorithm:* Alternating Direction Method of Multipliers (ADMM).
   - *License:* Apache 2.0 (fully compatible with Optees).
   - *Platforms & Wheels:* Pre-built binary wheels on PyPI for Linux (x86_64, aarch64), macOS (Apple Silicon arm64, Intel x86_64), Windows (x86_64, ARM64) on Python 3.8–3.13.
   - *Native Dependencies & Packaging:* Self-contained C extension with embedded QDLDL sparse solver; zero external dynamic library dependencies (no system BLAS/LAPACK requirement). Bundles cleanly in PyInstaller (<2 MB overhead).
   - *Determinism & Tolerances:* Fully deterministic arithmetic; configurable `eps_abs`, `eps_rel`, `eps_prim_inf`, `eps_dual_inf`, `max_iter`, `time_limit`.
   - *Status Fidelity:* Rigorous ADMM certificates for primal infeasibility (`primal infeasible`) and dual infeasibility / unboundedness (`dual infeasible`).
   - *Dual Variables & KKT:* Provides primal solution $x$ and full constraint dual multipliers $y$.
   - *Future Extensibility:* Native sparse matrix input (`scipy.sparse.csc_matrix`), warm starting (`warm_start(x, y)`), matrix/vector updates.
   - *Limitations:* First-order method; achieves medium-to-high precision ($10^{-5}$ to $10^{-7}$) very quickly; polishing mode (`polish=True`) provides high precision ($10^{-9}$).

2. **Clarabel (Clarabel.rs / Clarabel-python)**
   - *Version evaluated:* 0.9.0+
   - *Algorithm:* Homogeneous self-dual Interior Point Method (IPM) in Rust.
   - *License:* Apache 2.0.
   - *Platforms & Wheels:* Pre-built wheels via `maturin`/PyO3 on PyPI for Linux, macOS (Universal), Windows on Python 3.8–3.13.
   - *Native Dependencies & Packaging:* Self-contained statically compiled cdylib; clean PyInstaller packaging.
   - *Determinism & Tolerances:* High-precision IPM ($10^{-8}$ to $10^{-12}$ duality gap).
   - *Status Fidelity:* Homogeneous self-dual embedding provides exact infeasibility and unboundedness rays.
   - *Dual Variables & KKT:* Complete dual variables, duality gap, and residuals.
   - *Future Extensibility:* Native sparse matrices, conic cones (SOCP, SDP, Exponential).

3. **SciPy (`scipy.optimize.minimize` with SLSQP or trust-constr)**
   - *Version evaluated:* SciPy 1.17.1 (already bundled in Optees).
   - *Algorithm:* Sequential Least Squares Programming (SLSQP) / SQP Interior Point (`trust-constr`).
   - *License:* BSD 3-Clause.
   - *Limitations:* Not a dedicated QP solver. SLSQP uses dense matrices only, lacks formal infeasibility/unboundedness certificate vectors (reports generic line-search failure or singular matrix messages), lacks warm-starting, and dual multipliers for bounds are not uniformly exposed.
   - *Role:* Zero-dependency comparison baseline and fallback, not recommended as the primary production QP engine.

4. **HiGHS (`highspy`)**
   - *Algorithm:* Active-set and Interior Point QP solver built into HiGHS C++.
   - *License:* MIT.
   - *Limitations:* SciPy bundles HiGHS for `linprog` (LP) and `milp` (MILP), but does *not* expose HiGHS QP in Python. Using HiGHS QP requires the external `highspy` package, which has higher platform build complexity than OSQP.

5. **CVXOPT (`cvxopt.solvers.qp`)**
   - *License:* GNU General Public License v3 (GPLv3).
   - *Disqualification:* Viral copyleft GPLv3 license is incompatible with Optees Apache 2.0 licensing and distribution model.

6. **ProxQP (`proxsuite`)**
   - *Algorithm:* Primal-dual proximal method.
   - *License:* BSD 2-Clause.
   - *Limitations:* Primarily targeted at small robotics MPC problems; narrower ecosystem on Windows and ARM.

### 5.2 Comparative Summary Matrix

| Evaluation Criterion | OSQP | Clarabel | SciPy (SLSQP) | HiGHS (`highspy`) | CVXOPT |
| --- | --- | --- | --- | --- | --- |
| **Algorithm** | ADMM (First-order) | IPM (Self-dual) | SQP (General NLP) | Active Set / IPM | IPM |
| **License** | **Apache 2.0** | **Apache 2.0** | BSD 3-Clause | MIT | GPLv3 *(Rejected)* |
| **Python 3.12+ Wheels** | Yes (Win/Mac/Linux) | Yes (Win/Mac/Linux) | Already bundled | Yes | Yes |
| **Self-contained binary** | Yes (C / QDLDL) | Yes (Rust cdylib) | Yes | Yes (C++) | Requires BLAS/LAPACK |
| **PyInstaller overhead** | ~1.5 MB | ~2.5 MB | 0 MB | ~4 MB | ~15 MB |
| **Infeasible detection** | Exact certificate | Exact certificate | Heuristic / weak | Exact | Exact |
| **Unbounded detection** | Exact certificate | Exact certificate | Heuristic / weak | Exact | Exact |
| **Duals / KKT output** | Complete | Complete | Partial / Incomplete | Complete | Complete |
| **Sparse Matrix Ready** | Yes (CSC) | Yes (CSC) | No (Dense only) | Yes (CSC) | Yes (Sparse matrix) |
| **Warm Start Ready** | Yes ($x, y$) | Partial | No | Yes | No |
| **Determinism** | 100% | 100% | 100% | 100% | 100% |

### 5.3 Motivated Decision

- **Primary Recommended Backend:** `osqp` (Apache 2.0, robust ADMM with infeasibility/unboundedness detection, sparse CSC ready, warm-start ready, lightweight packaging).
- **Secondary / High-Precision Candidate:** `clarabel` (Apache 2.0, Rust IPM with high-precision interior-point convergence).
- **Comparative Baseline:** `scipy_slsqp` (built-in SciPy fallback for zero-dependency sanity checks).
- **Disqualified:** `cvxopt` due to GPLv3 license incompatibility.

---

## 6. Future Compatibility Considerations

1. **Sparse Matrix Representation (Future Schema Extension)**:
   Schema version `1` uses dense `quadratic_matrix` for clarity in educational and moderate-size problems ($n \le 500$).
   Future schema version `2` or compatible extensions will introduce `quadratic_sparse` with COO triplets `[{"row": i, "col": j, "value": v}]` or Compressed Sparse Column (CSC) format. `OSQP` and `Clarabel` consume CSC natively.
2. **Warm Start Capability**:
   The problem schema allows an optional `"initial_primal"` / `"initial_dual"` field in future extensions. OSQP natively supports `solver.warm_start(x=x0, y=y0)`.
3. **Convex MIQP (Mixed-Integer Quadratic Programming)**:
   In work unit `OPT-DS-05`, continuous QP will be extended to discrete variables by adding `"kind": "continuous" | "integer" | "binary"` to `variables`. The mathematical objective convention $\frac{1}{2} x^T Q x + c^T x + \alpha$ remains identical.

---

## 7. Educational Desktop Vertical Slice Definition (OPT-DS-02 Specification)

The minimum educational vertical slice in Phase `OPT-DS-02` will provide:

1. **Formulation View**:
   - Variables table with bounds ($l_i, u_i$).
   - Matrix editor with symmetric coefficient entry and formula view.
   - Linear objective coefficients ($c_i$) and offset ($\alpha$).
   - Linear constraints table ($A_{kj}, \text{relation}, b_k$).
2. **Solution View**:
   - Optimal objective value and variable assignments $x^*$.
   - Constraint activities and binding status.
   - Dual multipliers ($y_k, z_i$) and KKT residuals.
   - Educational explanations of convexity, eigenvalues, and KKT conditions.
3. **Interactive 2D Visualization**:
   - Contour plot of the quadratic surface for $n=2$ with constraint boundary lines, gradient vectors, and optimal point.
4. **Bilingual Resources (EN / IT)**:
   - English: *Quadratic Programming*, *Convex Optimization*, *Hessian Matrix*, *Positive Semi-Definite*, *KKT Residuals*.
   - Italian: *Programmazione Quadratica*, *Ottimizzazione Convessa*, *Matrice Hessiana*, *Semidefinita Positiva*, *Residui KKT*.
5. **Reference Cases and Benchmark Integration**:
   - Deterministic analytic reference cases (Interior, Boundary, Infeasible, Unbounded, Concave Max).
   - Integration path for the public-domain Maros-Mészáros convex QP benchmark problem collection.

---

## 8. Summary of Frozen Decisions for Work Unit `OPT-DS-01`

- [x] Mathematical convention frozen: $\min \frac{1}{2} x^T Q x + c^T x + \alpha$.
- [x] Objective sense: convex minimization and concave maximization supported; non-convex models rejected.
- [x] Symmetry tolerance $\varepsilon_{sym} = 10^{-8}$ and PSD tolerance $\varepsilon_{psd} = 10^{-8} \max(1, \|Q\|_\infty)$ frozen.
- [x] Variable ordering, binding, and dense matrix representation frozen.
- [x] Public capability ID `qp.continuous` and schema versions (`1`) frozen.
- [x] Full JSON DTO schemas, options, limits, error codes, and statuses frozen.
- [x] Complete valid and invalid JSON examples verified.
- [x] Independent solution validation rules and honest limitations frozen.
- [x] Backend selection analyzed: `osqp` recommended as primary engine; `clarabel` and `scipy_slsqp` catalogued; `cvxopt` rejected.
- [x] Gate `QP-C` achieved without blocking ambiguities.
