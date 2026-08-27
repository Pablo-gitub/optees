# Continuous Convex Quadratic Programming Contract

## Document Status

- **Work Unit:** `OPT-DS-01`
- **Gate:** `QP-C`
- **State:** frozen specification
- **Capability ID:** `qp.continuous`
- **Contract Version:** `1`
- **Problem Schema Version:** `1`
- **Result Schema Version:** `1`
- **Implementation Status:** shipped by `OPT-DS-02`; capability gate `QP-I`
  and desktop gate `QP-UI` reached after review correction.

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
     - If $Q_{user}$ has any strictly positive eigenvalue ($\lambda_{\max}(Q_{user}) > \varepsilon_{psd}$), the problem is non-concave and is rejected before solve with validation detail code `qp.non_concave_quadratic_matrix`.
   - The solver adapter transforms the problem into equivalent convex minimization with $Q_{internal} = -Q_{user}$, $c_{internal} = -c_{user}$, $\alpha_{internal} = -\alpha_{user}$.
   - The reported optimal objective value is restored as $f_{max}^* = -f_{internal}^* = \frac{1}{2} (x^*)^T Q_{user} x^* + c_{user}^T x^* + \alpha_{user}$.

Non-convex quadratic problems (e.g. indefinite $Q$ for minimization or maximization) are strictly out of scope for capability `qp.continuous` and are rejected during validation.

### 1.6 Symmetry and Positive Semi-Definiteness (PSD) Tolerances

Before execution, $Q$ undergoes strict numerical validation:

- **Symmetry check**:
  \[
  \Delta_{sym} = \max_{i, j} |Q_{ij} - Q_{ji}| \le \varepsilon_{sym} = 10^{-8} \cdot \max(1.0, \max_{i,j}|Q_{ij}|)
  \]
  If $\Delta_{sym} > \varepsilon_{sym}$, the problem is rejected with validation detail code `qp.asymmetric_quadratic_matrix`.
  If $\Delta_{sym} \le \varepsilon_{sym}$, the matrix is canonicalized as $Q_{sym} = \frac{1}{2}(Q + Q^T)$.
- **Positive Semi-Definiteness (PSD) check**:
  The minimum eigenvalue $\lambda_{\min}(Q_{sym})$ is computed via symmetric eigenvalue decomposition.
  \[
  \lambda_{\min}(Q_{sym}) \ge -\varepsilon_{psd}, \quad \text{where } \varepsilon_{psd} = 10^{-8} \cdot \max(1.0, \max_{i,j}|Q_{sym,ij}|)
  \]
  - If $\lambda_{\min}(Q_{sym}) < -\varepsilon_{psd}$, the matrix is non-convex and rejected with validation detail code `qp.non_convex_quadratic_matrix`.
  - If $-\varepsilon_{psd} \le \lambda_{\min}(Q_{sym}) < 0$, the model is
    accepted as convex within the declared numerical tolerance and the
    symmetrized matrix is passed unchanged to the backend. Optees does not
    project eigenvalues or otherwise change the caller's objective silently.
    A backend that cannot factor the accepted matrix returns a numerical
    failure, with diagnostics, rather than solving a modified problem.

---

## 2. Public Contract and Versioned Schemas

### 2.1 Capability Identity

- **Capability ID:** `qp.continuous`
- **Title:** `Continuous convex quadratic programming`
- **Problem Type:** `quadratic_programming`
- **Contract Version:** `1`
- **Problem Schema Version:** `1`
- **Result Schema Version:** `1`
- **Selected Version 1 Backend:** `osqp`
- **Evaluated Alternatives:** `clarabel`, `scipy_slsqp`
- **Supports Time Limit:** `true`
- **Supports Cancellation:** `false` for version 1 unless `OPT-DS-02`
  demonstrates a safe interrupt boundary and updates the descriptor contract.

### 2.2 Default Options and Resource Limits

| Parameter | Default | Allowed Range / Bound | Description |
| --- | --- | --- | --- |
| `method` | `"osqp"` | `"osqp"` | Version 1 backend; alternatives are not public fallbacks |
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
  "additionalProperties": false,
  "required": ["version", "problem_type", "variables", "objective", "constraints"],
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
        "additionalProperties": false,
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
      "additionalProperties": false,
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
        "additionalProperties": false,
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
      "additionalProperties": false,
      "properties": {
        "method": {
          "type": "string",
          "const": "osqp",
          "default": "osqp"
        },
        "tolerance": {
          "type": "number",
          "minimum": 1e-12,
          "maximum": 1e-2,
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
  "additionalProperties": false,
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
      "maxItems": 500,
      "description": "Candidate variable values in declared order; empty when no primal candidate is available.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "value"],
        "properties": {
          "name": {"type": "string"},
          "value": {"type": "number"}
        }
      }
    },
    "dual_values": {
      "type": ["object", "null"],
      "additionalProperties": false,
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
      "additionalProperties": false,
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
  - `optimal`: Backend reports solved and the candidate passes the required
    independent feasibility and objective checks; available KKT residuals are
    within the declared tolerance. This is a numerical convex-optimization
    claim, not an exact-arithmetic proof.
  - `feasible`: Feasible candidate produced (e.g. at time limit or iteration limit).
  - `infeasible`: Backend reports primal infeasibility with its documented
    numerical certificate/status. Optees preserves certificate diagnostics and
    does not relabel an ambiguous failure as infeasible.
  - `unbounded`: Backend reports dual infeasibility, corresponding to primal
    unboundedness for this convex form, with its documented numerical
    certificate/status. Ambiguous failures remain `not_solved`.
  - `not_solved`: Solver failed due to numerical instability or divergence.
- **`termination_reason`**: `completed`, `time_limit`, `iteration_limit`, `cancelled`, `dependency_failure`, `internal_error`.
- **`validation`**: `verified`, `partial`, `failed`, `not_available`.

Invalid problem documents use the existing public envelope error
`validation_failed`. The stable QP-specific `details[].code` values are:

| Detail code | Meaning |
| --- | --- |
| `qp.invalid_structure` | Missing, unexpected, or incorrectly typed JSON field |
| `qp.non_finite_value` | A coefficient, bound, option, or result value is not finite |
| `qp.duplicate_variable_name` | Variable names are not unique |
| `qp.invalid_bounds` | A finite lower bound exceeds its upper bound |
| `qp.dimension_mismatch` | A vector, matrix row, or constraint does not bind to all variables |
| `qp.asymmetric_quadratic_matrix` | $Q$ exceeds the frozen symmetry tolerance |
| `qp.non_convex_quadratic_matrix` | A minimization Hessian is not PSD within tolerance |
| `qp.non_concave_quadratic_matrix` | A maximization Hessian is not NSD within tolerance |
| `qp.invalid_solver_option` | An option is unknown or outside its frozen range |
| `qp.resource_limit_exceeded` | Variables, constraints, or payload size exceed version 1 limits |

These are validation detail codes, not additions to the top-level `ErrorCode`
enumeration. Backend absence maps to the existing `dependency_unavailable`
error and makes the capability descriptor unavailable; Optees must not silently
fall back to a backend with different status semantics.

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
Rejected with validation detail code `qp.dimension_mismatch`.

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
Rejected with validation detail code `qp.asymmetric_quadratic_matrix`.

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
Rejected with validation detail code `qp.non_convex_quadratic_matrix`.

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

### 5.1 Evidence Boundary

The decision review used official solver documentation and package metadata,
plus analytic NumPy/SciPy probes. Neither OSQP nor Clarabel was installed in the
review environment, and no PyInstaller artifact containing either package was
built. Consequently, wheel availability and documented APIs are evidence for a
direction, while runtime status mapping, cancellation, repeatability, binary
closure, and bundle-size impact remain acceptance tests for `OPT-DS-02`.

### 5.2 Evaluated Candidates

1. **OSQP — selected for version 1**
   - Uses ADMM for convex QPs and accepts sparse CSC matrices.
   - Apache-2.0 licensed. Current PyPI metadata provides Python 3.12 wheels for
     the three Optees release targets: Windows x64, macOS Apple Silicon, and
     Linux x86_64.
   - The Python result API documents primal and dual solutions, solver
     statistics, and primal/dual infeasibility certificate fields. These are
     numerical solver certificates governed by solver tolerances, not exact
     mathematical proofs; Optees still performs its independent checks.
   - Official settings include iteration and runtime limits, and the Python API
     supports warm starts. No safe in-process cancellation claim is frozen.
   - Repeatability must be tested with pinned backend version, settings,
     algebra backend, thread configuration, and platform. The contract does not
     promise bitwise or cross-platform determinism.

2. **Clarabel — retained alternative, not a version 1 public method**
   - Apache-2.0 licensed interior-point conic solver with direct Python QP
     support, sparse CSC data, primal/dual values, explicit full- and
     reduced-accuracy statuses, iteration limits, and time limits.
   - Its different status taxonomy and numerical behavior must not be hidden
     behind an automatic fallback. Adopting it later requires an explicit
     contract/backend revision and the same packaging gates as OSQP.

3. **SciPy SLSQP/trust-constr — comparison probe only**
   - Already present in Optees and useful for analytic comparisons.
   - It is not accepted as a transparent production fallback because its
     termination and infeasible/unbounded reporting do not satisfy the frozen
     QP status contract.

4. **HiGHS, CVXOPT, and ProxQP — not selected**
   - They remain possible future evaluation candidates, but this work unit did
     not produce sufficient platform and packaging evidence to expose them.
   - CVXOPT's GPLv3 distribution terms conflict with the current goal of
     retaining an Apache-2.0 Optees binary distribution. This is a product
     licensing constraint, not a claim that Apache-2.0 and GPLv3 code can never
     be combined.

### 5.3 Decision and Implementation Acceptance Gates

- `osqp` is the only public `method` in schema version 1.
- If the dependency is absent, `qp.continuous` is advertised as unavailable
  with a reason and execution returns `dependency_unavailable`.
- `OPT-DS-02` must pin the evaluated OSQP release, solve and independently
  validate all reference cases, exercise every mapped backend status, and build
  the actual Windows x64, macOS Apple Silicon, and Linux x86_64 artifacts.
- Bundle size must be measured from those artifacts; no numeric overhead is
  claimed before that evidence exists.
- `supports_cancellation` remains `false` unless a safe interrupt or isolated
  worker strategy is implemented and tested. A time limit is not cancellation.

### 5.4 Primary Sources Consulted

- [OSQP Python interface](https://osqp.org/docs/interfaces/python.html)
- [OSQP solver settings](https://osqp.org/docs/interfaces/solver_settings.html)
- [OSQP status values](https://osqp.org/docs/interfaces/status_values.html)
- [OSQP package metadata and release wheels](https://pypi.org/project/osqp/)
- [Clarabel Python problem and result interface](https://clarabel.org/stable/python/getting_started_py/)
- [Clarabel solver settings](https://clarabel.org/stable/api_settings/)
- [Clarabel package metadata and release wheels](https://pypi.org/project/clarabel/)
- [SciPy `minimize` API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html)

Sources and package metadata were reviewed on 2026-08-27. Packaging claims
must be rechecked against the pinned release when `OPT-DS-02` begins.

---

## 6. Future Compatibility Considerations

1. **Sparse Matrix Representation (Future Schema Extension)**:
   Schema version `1` uses dense `quadratic_matrix` for clarity in educational and moderate-size problems ($n \le 500$).
   A future schema version `2` may introduce `quadratic_sparse` with COO triplets `[{"row": i, "col": j, "value": v}]` or Compressed Sparse Column (CSC) format. Because schema v1 is closed to unknown fields, this is an explicit version change rather than a silent extension. `OSQP` and `Clarabel` consume CSC natively.
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
- [x] Symmetry and PSD tolerances use the explicit scale $10^{-8} \max(1, \max_{i,j}|Q_{ij}|)$; accepted matrices are never silently projected.
- [x] Variable ordering, binding, and dense matrix representation frozen.
- [x] Public capability ID `qp.continuous` and schema versions (`1`) frozen.
- [x] Full JSON DTO schemas, options, limits, error codes, and statuses frozen.
- [x] Complete valid and invalid JSON examples verified.
- [x] Independent solution validation rules and honest limitations frozen.
- [x] Backend selection analyzed: `osqp` is the sole version 1 method; alternatives are catalogued without fallback or unverified packaging claims.
- [x] Gate `QP-C` achieved without blocking ambiguities.
