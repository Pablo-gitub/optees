# Linear Scenario Min-Max and Max-Min Optimization Contract

## Document Status

- **Work Unit:** `OPT-DS-03`
- **Gate:** `ROBUST-D`
- **State:** frozen specification
- **Capability IDs:**
  - `scenario.linear.min_max_loss` (orientation: `minimize_maximum_loss`)
  - `scenario.linear.max_min_reward` (orientation: `maximize_minimum_reward`)
- **Contract Version:** `1`
- **Problem Schema Version:** `1`
- **Result Schema Version:** `1`
- **Implementation Status:** planned for `OPT-DS-03B` through `OPT-DS-03E`.

This contract defines and freezes the mathematical foundations, epigraph/hypograph
reductions to linear programming (LP) and mixed-integer linear programming (MILP),
public JSON data transfer objects (DTOs), independent validation guarantees, status
mappings, and delivery boundaries for finite linear scenario optimization in Optees.

---

## 1. Mathematical Formulation and Semantic Orientations

### 1.1 Decision Variables, Bounds, and Integrality

Let $x = (x_1, x_2, \dots, x_n)^T \in \mathbb{R}^n$ be the ordered vector of $n \ge 1$
decision variables.

Each variable $x_j$ ($j \in \{1, \dots, n\}$) has:
- an immutable, non-empty, unique name $name_j \in \text{String}$;
- an optional label $label_j \in \text{String}$;
- box bounds $[l_j, u_j]$ with $l_j \in \mathbb{R} \cup \{-\infty\}$ and $u_j \in \mathbb{R} \cup \{+\infty\}$ such that $l_j \le u_j$;
- an integrality domain $D_j \in \{\text{CONTINUOUS}, \text{INTEGER}, \text{BINARY}\}$:
  - $\text{CONTINUOUS}$ (`"C"`): $x_j \in \mathbb{R}$ with $l_j \le x_j \le u_j$.
  - $\text{INTEGER}$ (`"I"`): $x_j \in \mathbb{Z}$ with $l_j \le x_j \le u_j$.
  - $\text{BINARY}$ (`"B"`): $x_j \in \{0, 1\}$, with implicit canonical bounds $0 \le x_j \le 1$.

Let $\mathcal{X} \subseteq \mathbb{R}^n$ denote the shared feasible region:
\[
\mathcal{X} = \left\{ x \in \mathbb{R}^n \;\middle|\;
l \le x \le u, \quad
x_j \in \mathbb{Z} \; (\forall j \in \mathcal{I}), \quad
x_j \in \{0, 1\} \; (\forall j \in \mathcal{B}), \quad
A_{eq} x = b_{eq}, \quad
A_{ineq} x \le b_{ineq}
\right\}
\]
where $A_{eq} x = b_{eq}$ and $A_{ineq} x \le b_{ineq}$ represent optional shared linear
equality and inequality constraints.

### 1.2 Finite Scenario Set and Linear Evaluations

Let $S = (s_1, s_2, \dots, s_K)$ be a deterministic, ordered sequence of $K \ge 1$
scenarios.

Each scenario $s_k$ ($k \in \{1, \dots, K\}$) declares:
- a unique scenario identifier $id_k \in \text{String}$;
- an optional human-readable label $label_k \in \text{String}$;
- a scenario linear coefficient vector $c^{(k)} = (c^{(k)}_1, \dots, c^{(k)}_n)^T \in \mathbb{R}^n$;
- a scenario scalar constant offset $\gamma_k \in \mathbb{R}$ (default $0.0$).

The problem may optionally declare a shared base objective term $c^{(0)} \in \mathbb{R}^n$
and a shared scalar offset $\gamma_0 \in \mathbb{R}$ (default $0.0$).

For any candidate $x \in \mathcal{X}$, the linear evaluation under scenario $s_k$ is:
\[
v_k(x) = \sum_{j=1}^n \left(c^{(0)}_j + c^{(k)}_j\right) x_j + \left(\gamma_0 + \gamma_k\right) = d^{(k)T} x + \delta_k
\]
where $d^{(k)} = c^{(0)} + c^{(k)} \in \mathbb{R}^n$ and $\delta_k = \gamma_0 + \gamma_k \in \mathbb{R}$.

### 1.3 Orientation 1: Minimize Maximum Loss (`minimize_maximum_loss`)

In this orientation, $v_k(x)$ represents the **loss** (or cost, damage, penalty)
incurred under scenario $s_k$.

The worst-case loss across all scenarios for candidate $x$ is:
\[
L_{\max}(x) = \max_{k \in \{1, \dots, K\}} v_k(x) = \max_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]

The robust optimization problem is:
\[
\min_{x \in \mathcal{X}} L_{\max}(x) = \min_{x \in \mathcal{X}} \max_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]

#### Epigraph LP/MILP Reduction
Introducing a single continuous auxiliary epigraph variable $\theta \in \mathbb{R}$
representing the upper bound on loss across all scenarios:
\[
\begin{aligned}
\min_{x \in \mathcal{X}, \; \theta \in \mathbb{R}} \quad & \theta \\
\text{subject to} \quad & \theta \ge d^{(k)T} x + \delta_k, \quad \forall k \in \{1, \dots, K\}
\end{aligned}
\]
In canonical constraint form ($A x \le b$):
\[
d^{(k)T} x - \theta \le -\delta_k, \quad \forall k \in \{1, \dots, K\}
\]

At the optimal solution $(x^*, \theta^*)$:
- Optimal robust objective: $z^* = \theta^* = \max_{k=1,\dots,K} v_k(x^*)$.
- The guarantee value is: $\text{guaranteed\_loss} = z^*$. In every scenario $s_k$, $v_k(x^*) \le z^*$.

### 1.4 Orientation 2: Maximize Minimum Reward (`maximize_minimum_reward`)

In this orientation, $v_k(x)$ represents the **reward** (or payoff, utility, revenue)
achieved under scenario $s_k$.

The worst-case reward across all scenarios for candidate $x$ is:
\[
R_{\min}(x) = \min_{k \in \{1, \dots, K\}} v_k(x) = \min_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]

The robust optimization problem is:
\[
\max_{x \in \mathcal{X}} R_{\min}(x) = \max_{x \in \mathcal{X}} \min_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]

#### Hypograph LP/MILP Reduction
Introducing a single continuous auxiliary hypograph variable $\tau \in \mathbb{R}$
representing the lower bound on reward across all scenarios:
\[
\begin{aligned}
\max_{x \in \mathcal{X}, \; \tau \in \mathbb{R}} \quad & \tau \\
\text{subject to} \quad & \tau \le d^{(k)T} x + \delta_k, \quad \forall k \in \{1, \dots, K\}
\end{aligned}
\]
In canonical constraint form ($A x \le b$):
\[
-d^{(k)T} x + \tau \le \delta_k, \quad \forall k \in \{1, \dots, K\}
\]

At the optimal solution $(x^*, \tau^*)$:
- Optimal robust objective: $z^* = \tau^* = \min_{k=1,\dots,K} v_k(x^*)$.
- The guarantee value is: $\text{guaranteed\_reward} = z^*$. In every scenario $s_k$, $v_k(x^*) \ge z^*$.

---

## 2. Mathematical Proof of Non-Aliasing

The two orientations `minimize_maximum_loss` and `maximize_minimum_reward` are
fundamentally distinct public semantics and **must not be implemented or exposed
as mere sign-flipped aliases**.

### Proof of Distinction:

1. **Physical Semantics of Coefficients**:
   - Under `minimize_maximum_loss`, a positive coefficient $c_j^{(k)} > 0$ means that increasing $x_j$ increases loss (adverse impact).
   - Under `maximize_minimum_reward`, a positive coefficient $c_j^{(k)} > 0$ means that increasing $x_j$ increases reward (beneficial impact).
   - Inverting signs implicitly causes severe cognitive errors in formulation and decision interpretation.

2. **Epigraph vs. Hypograph Polyhedral Geometry**:
   - The epigraph $\{(x, \theta) \mid \theta \ge \max_k v_k(x)\}$ is an unbounded upward polyhedron; minimization pushes downward to the lower boundary envelope.
   - The hypograph $\{(x, \tau) \mid \tau \le \min_k v_k(x)\}$ is an unbounded downward polyhedron; maximization pushes upward to the upper boundary envelope.

3. **Scenario-Level Reporting and Binding Set Semantics**:
   - For `minimize_maximum_loss`, each scenario produces a loss $L_k(x)$; the binding set comprises the scenarios that achieve the **maximum** loss:
     \[
     \mathcal{B}_{\text{loss}} = \left\{ k \in \{1, \dots, K\} \;\middle|\; v_k(x^*) = \max_{j} v_j(x^*) \right\}
     \]
   - For `maximize_minimum_reward`, each scenario produces a reward $R_k(x)$; the binding set comprises the scenarios that achieve the **minimum** reward:
     \[
     \mathcal{B}_{\text{reward}} = \left\{ k \in \{1, \dots, K\} \;\middle|\; v_k(x^*) = \min_{j} v_j(x^*) \right\}
     \]
   - If an engine were to flip signs internally without explicit orientation awareness, it would misreport binding scenarios (e.g. reporting scenarios with least loss as binding for a reward problem).

4. **Sign Transformation Equivalence**:
   Mathematically, if $L_k(x) = -R_k(x)$, then:
   \[
   \max_{x \in \mathcal{X}} \min_{k} R_k(x) = \max_{x \in \mathcal{X}} \left( -\max_{k} \left(-R_k(x)\right) \right) = -\min_{x \in \mathcal{X}} \max_{k} L_k(x)
   \]
   While this identity is mathematically sound, demanding that users or transport layers manually negate coefficients, offsets, objectives, and scenario outputs creates ambiguity and breaks independent validation. Therefore, both orientations exist as first-class capabilities with dedicated capability IDs and separate semantic contracts.

---

## 3. Epigraph and Hypograph Reduction Proof Table

| Property | `minimize_maximum_loss` | `maximize_minimum_reward` |
| :--- | :--- | :--- |
| **Capability ID** | `scenario.linear.min_max_loss` | `scenario.linear.max_min_reward` |
| **Public Orientation Token** | `"minimize_maximum_loss"` | `"maximize_minimum_reward"` |
| **Evaluation $v_k(x)$** | Scenario Loss $L_k(x) = d^{(k)T} x + \delta_k$ | Scenario Reward $R_k(x) = d^{(k)T} x + \delta_k$ |
| **Worst-Case Value** | Maximum Loss $L_{\max}(x) = \max_k v_k(x)$ | Minimum Reward $R_{\min}(x) = \min_k v_k(x)$ |
| **Optimization Sense** | $\min_{x \in \mathcal{X}} L_{\max}(x)$ | $\max_{x \in \mathcal{X}} R_{\min}(x)$ |
| **Auxiliary Variable** | $\theta \in \mathbb{R}$ (bounds: $[-\infty, +\infty]$) | $\tau \in \mathbb{R}$ (bounds: $[-\infty, +\infty]$) |
| **Auxiliary Name** | `"_aux_theta"` | `"_aux_tau"` |
| **Auxiliary Integrality** | Always `CONTINUOUS` (`"C"`) | Always `CONTINUOUS` (`"C"`) |
| **Delegated Objective** | $\min 1 \cdot \theta + 0 \cdot x$ | $\max 1 \cdot \tau + 0 \cdot x$ (or $\min -1 \cdot \tau$) |
| **Scenario Constraints ($k=1..K$)** | $d^{(k)T} x - \theta \le -\delta_k$ | $-d^{(k)T} x + \tau \le \delta_k$ |
| **Shared Constraints** | $A_{eq} x = b_{eq}$, $A_{ineq} x \le b_{ineq}$ (unchanged) | $A_{eq} x = b_{eq}$, $A_{ineq} x \le b_{ineq}$ (unchanged) |
| **Guaranteed Bound** | $\text{guaranteed\_loss} = \theta^* = \max_k v_k(x^*)$ | $\text{guaranteed\_reward} = \tau^* = \min_k v_k(x^*)$ |
| **Binding Definition** | $v_k(x^*) \ge \theta^* - \varepsilon_{bind} \max(1, |\theta^*|)$ | $v_k(x^*) \le \tau^* + \varepsilon_{bind} \max(1, |\tau^*|)$ |

---

## 4. Variable Domains and Solver Delegation Rules

The reduction inspects the integrality of all decision variables:

1. **Continuous Problem**:
   If $D_j = \text{CONTINUOUS}$ for all $j \in \{1, \dots, n\}$, the reduced problem has $n+1$ continuous variables.
   - Delegated to LP solver port (`LPSolverPort`, e.g. HiGHS backend).
   - Solver executes in polynomial time with exact simplex/interior-point guarantees.

2. **Mixed-Integer / Discrete Problem**:
   If any $D_j \in \{\text{INTEGER}, \text{BINARY}\}$, the reduced problem is a Mixed-Integer Linear Program (MILP).
   - The auxiliary variable ($\theta$ or $\tau$) remains **strictly continuous** ($\text{CONTINUOUS}$).
   - The original variable domains ($x_j \in \mathbb{Z}$ or $x_j \in \{0, 1\}$) are strictly preserved.
   - Delegated to MILP solver port (`MILPSolverPort`, e.g. OR-Tools CBC / CP-SAT backend).

---

## 5. Binding Scenarios and Deterministic Tie-Breaking

### 5.1 Worst-Case Guarantee and Scenario Evaluation

Let $x^*$ be the returned decision vector. The application layer independently evaluates:
\[
v_k(x^*) = d^{(k)T} x^* + \delta_k, \quad \forall k \in \{1, \dots, K\}
\]

- For `minimize_maximum_loss`:
  \[
  L_{\max}^* = \max_{k \in \{1, \dots, K\}} v_k(x^*)
  \]
- For `maximize_minimum_reward`:
  \[
  R_{\min}^* = \min_{k \in \{1, \dots, K\}} v_k(x^*)
  \]

### 5.2 Binding Scenario Tolerance

A scenario $s_k$ is classified as **binding** if its evaluated value matches the worst-case
guarantee within a relative tolerance $\varepsilon_{bind}$:
- `minimize_maximum_loss`:
  \[
  |v_k(x^*) - L_{\max}^*| \le \varepsilon_{bind} \max\left(1.0, |L_{\max}^*|\right)
  \]
- `maximize_minimum_reward`:
  \[
  |v_k(x^*) - R_{\min}^*| \le \varepsilon_{bind} \max\left(1.0, |R_{\min}^*|\right)
  \]
where default $\varepsilon_{bind} = 10^{-6}$.

### 5.3 Deterministic Tie-Breaking and Sequence Preservation

When multiple scenarios achieve the worst-case value within tolerance (a tie):
1. **No Scenario Dropping**: All binding scenarios must be included in `binding_scenario_ids`.
2. **Deterministic Sequence**: `binding_scenario_ids` must preserve the exact relative order in which the scenarios were declared in the input `scenarios` array.
3. **Scenario Values Array**: The output `scenario_values` array contains exactly $K$ entries in the original declared order, each reporting `scenario_id`, `value`, and boolean `is_binding`.

---

## 6. Analytical Reference Examples (Hand-Calculable)

### 6.1 Example 1: `minimize_maximum_loss` (Continuous, Mixed Signs, Multiple Binding Scenarios)

#### Problem Definition:
- Variables: $x_1 \ge 0, x_2 \ge 0$.
- Shared Constraint: $x_1 + x_2 = 10$.
- Scenarios:
  - $s_1$: $L_1(x) = 2 x_1 - x_2 + 5$
  - $s_2$: $L_2(x) = -x_1 + 3 x_2 + 2$
  - $s_3$: $L_3(x) = x_1 + x_2 - 4$

#### Analytical Derivation:
Substituting $x_2 = 10 - x_1$ for $x_1 \in [0, 10]$:
- $L_1(x_1) = 2 x_1 - (10 - x_1) + 5 = 3 x_1 - 5$.
- $L_2(x_1) = -x_1 + 3(10 - x_1) + 2 = -4 x_1 + 32$.
- $L_3(x_1) = x_1 + (10 - x_1) - 4 = 6$ (constant).

Intersection of $L_1(x_1)$ and $L_2(x_1)$:
\[
3 x_1 - 5 = -4 x_1 + 32 \implies 7 x_1 = 37 \implies x_1^* = \frac{37}{7} \approx 5.2857142857
\]
\[
x_2^* = 10 - \frac{37}{7} = \frac{33}{7} \approx 4.7142857143
\]

Evaluating loss values at $x^*$:
- $L_1(x^*) = 3\left(\frac{37}{7}\right) - 5 = \frac{76}{7} \approx 10.8571428571$
- $L_2(x^*) = -4\left(\frac{37}{7}\right) + 32 = \frac{76}{7} \approx 10.8571428571$
- $L_3(x^*) = 6 < \frac{76}{7}$

Optimal solution:
- $x^* = (37/7, 33/7)^T \approx (5.285714, 4.714286)^T$
- $\text{guaranteed\_loss} = \frac{76}{7} \approx 10.857143$
- Binding scenarios: `["s1", "s2"]` (tie with two active binding scenarios).

---

### 6.2 Example 2: `maximize_minimum_reward` (Continuous, Negative Values, Multiple Binding Scenarios)

#### Problem Definition:
- Variables: $0 \le x_1 \le 4, 0 \le x_2 \le 4$.
- Shared Constraint: $x_1 + x_2 \le 6$.
- Scenarios:
  - $s_A$: $R_A(x) = 4 x_1 - 2 x_2 - 10$
  - $s_B$: $R_B(x) = -2 x_1 + 5 x_2 - 8$
  - $s_C$: $R_C(x) = x_1 + x_2 - 5$

#### Analytical Derivation:
To maximize the lower envelope $\min(R_A, R_B, R_C)$, setting $R_A(x) = R_B(x)$:
\[
4 x_1 - 2 x_2 - 10 = -2 x_1 + 5 x_2 - 8 \implies 6 x_1 - 7 x_2 = 2 \implies x_2 = \frac{6 x_1 - 2}{7}
\]
With budget boundary $x_1 + x_2 = 6$:
\[
x_1 + \frac{6 x_1 - 2}{7} = 6 \implies \frac{13 x_1 - 2}{7} = 6 \implies 13 x_1 = 44 \implies x_1^* = \frac{44}{13} \approx 3.3846153846
\]
\[
x_2^* = \frac{6(44/13) - 2}{7} = \frac{34}{13} \approx 2.6153846154
\]
Both $x_1^* \le 4$ and $x_2^* \le 4$ are satisfied.

Evaluating reward values at $x^*$:
- $R_A(x^*) = 4\left(\frac{44}{13}\right) - 2\left(\frac{34}{13}\right) - 10 = \frac{176 - 68 - 130}{13} = -\frac{22}{13} \approx -1.6923076923$
- $R_B(x^*) = -2\left(\frac{44}{13}\right) + 5\left(\frac{34}{13}\right) - 8 = \frac{-88 + 170 - 104}{13} = -\frac{22}{13} \approx -1.6923076923$
- $R_C(x^*) = \frac{44}{13} + \frac{34}{13} - 5 = 6 - 5 = 1.0 > -\frac{22}{13}$

Optimal solution:
- $x^* = (44/13, 34/13)^T \approx (3.384615, 2.615385)^T$
- $\text{guaranteed\_reward} = -\frac{22}{13} \approx -1.692308$ (strictly negative worst-case reward)
- Binding scenarios: `["sA", "sB"]` (tie with two active binding scenarios).

---

### 6.3 Example 3: `minimize_maximum_loss` (Discrete/Binary Selection MILP)

#### Problem Definition:
- Variables: $x_1, x_2, x_3 \in \{0, 1\}$ (binary).
- Shared Constraint: $x_1 + x_2 + x_3 = 2$ (select exactly 2 items).
- Scenarios:
  - $s_1$: $L_1(x) = 10 x_1 + 2 x_2 + 8 x_3$
  - $s_2$: $L_2(x) = 3 x_1 + 12 x_2 + 4 x_3$
  - $s_3$: $L_3(x) = 6 x_1 + 5 x_2 + 9 x_3$

#### Analytical Evaluation of Feasible Combinations:
1. $x = (1, 1, 0)$:
   - $L_1 = 10 + 2 = 12$
   - $L_2 = 3 + 12 = 15$
   - $L_3 = 6 + 5 = 11$
   - Worst loss: $\max(12, 15, 11) = 15.0$ (binding: $s_2$).
2. $x = (1, 0, 1)$:
   - $L_1 = 10 + 8 = 18$
   - $L_2 = 3 + 4 = 7$
   - $L_3 = 6 + 9 = 15$
   - Worst loss: $\max(18, 7, 15) = 18.0$ (binding: $s_1$).
3. $x = (0, 1, 1)$:
   - $L_1 = 2 + 8 = 10$
   - $L_2 = 12 + 4 = 16$
   - $L_3 = 5 + 9 = 14$
   - Worst loss: $\max(10, 16, 14) = 16.0$ (binding: $s_2$).

Optimal binary solution:
- $x^* = (1, 1, 0)^T$
- $\text{guaranteed\_loss} = 15.0$
- Binding scenarios: `["s2"]`.

---

## 7. Status Mappings and Mathematical Dimensions

The robust capability maps delegated LP/MILP outcomes to public Optees statuses:

### 7.1 Mathematical Status (`mathematical_status`)

- `OPTIMAL` (`"optimal"`): Solver proved optimality within tolerances. All scenario constraints hold and worst-case guarantee is exact.
- `FEASIBLE` (`"feasible"`): A feasible candidate solution was found (e.g. MILP incumbent when time limit was reached), but optimality is unproven.
- `INFEASIBLE` (`"infeasible"`): Shared constraints or scenario epigraph constraints are mutually contradictory; no candidate exists.
- `UNBOUNDED` (`"unbounded"`): The robust objective can be improved indefinitely ($\theta \to -\infty$ or $\tau \to +\infty$) along a feasible ray.
- `NOT_SOLVED` (`"not_solved"`): Numerical breakdown or missing dependencies prevented resolution.

### 7.2 Termination Reason (`termination_reason`)

- `COMPLETED` (`"completed"`): Normal successful termination.
- `TIME_LIMIT` (`"time_limit"`): Solver halted because the time limit expired.
- `ITERATION_LIMIT` (`"iteration_limit"`): Solver halted because iteration count expired.
- `INFEASIBLE` (`"infeasible"`): Proven infeasible.
- `UNBOUNDED` (`"unbounded"`): Proven unbounded.
- `NUMERICAL_ERROR` (`"numerical_error"`): Solver numerical failure.
- `DEPENDENCY_MISSING` (`"dependency_missing"`): Required solver library missing.

### 7.3 Validation Status (`validation.status`)

- `VERIFIED` (`"verified"`): Candidate satisfies all variable domains, bounds, shared constraints, every $v_k(x^*)$ matches, and guarantee $L_{\max}^*$ or $R_{\min}^*$ matches the reported objective.
- `PARTIAL` (`"partial"`): Feasibility and scenario recomputation passed, but dual/stationarity verification was unavailable (e.g. for discrete MILP).
- `FAILED` (`"failed"`): Any constraint, bound, scenario calculation, or guarantee value was violated.
- `NOT_AVAILABLE` (`"not_available"`): Validation is not applicable (e.g. for infeasible or unbounded results without candidate).

---

## 8. Independent Solution Validation Contract

The validator `ScenarioIndependentSolutionValidator` executes strictly outside the solver:

1. **`scenario.variable_vector`**:
   Verifies that the returned `variables` mapping contains exactly the declared $n$ variable names and that all values are finite numbers.
2. **`scenario.bounds`**:
   Verifies that $l_j - \varepsilon \le x_j^* \le u_j + \varepsilon$ for all $j$. For integer/binary variables, verifies integrality $|x_j^* - \text{round}(x_j^*)| \le \varepsilon_{int}$.
3. **`scenario.constraints`**:
   Recomputes shared constraints $\sum_j A_{kj} x_j^*$ and verifies relation to $b_k$ within tolerance $\varepsilon$.
4. **`scenario.values`**:
   Independently recomputes $v_k(x^*) = d^{(k)T} x^* + \delta_k$ for every scenario $k \in \{1, \dots, K\}$ and verifies matching with reported `scenario_values[k].value`.
5. **`scenario.guarantee`**:
   Recomputes $\text{worst} = \max_k v_k(x^*)$ (for loss) or $\min_k v_k(x^*)$ (for reward) and verifies equality to reported `guaranteed_value`.
6. **`scenario.binding_set`**:
   Identifies all scenarios satisfying $|v_k(x^*) - \text{worst}| \le \varepsilon_{bind} \max(1, |\text{worst}|)$ and verifies exact match with `binding_scenario_ids` and `scenario_values[k].is_binding`.

---

## 9. Public JSON Schemas (Version 1)

### 9.1 Problem Schema (`problem_schema_version: "1"`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "contract_version",
    "problem_schema_version",
    "capability_id",
    "problem_type",
    "orientation",
    "variables",
    "scenarios"
  ],
  "properties": {
    "contract_version": { "const": "1" },
    "problem_schema_version": { "const": "1" },
    "capability_id": {
      "enum": [
        "scenario.linear.min_max_loss",
        "scenario.linear.max_min_reward"
      ]
    },
    "problem_type": { "const": "linear_scenario" },
    "orientation": {
      "enum": [
        "minimize_maximum_loss",
        "maximize_minimum_reward"
      ]
    },
    "variables": {
      "type": "array",
      "minItems": 1,
      "maxItems": 500,
      "items": {
        "type": "object",
        "required": ["name"],
        "properties": {
          "name": { "type": "string", "minLength": 1 },
          "label": { "type": "string" },
          "lower_bound": { "type": ["number", "null"] },
          "upper_bound": { "type": ["number", "null"] },
          "integrality": {
            "enum": ["C", "I", "B"],
            "default": "C"
          }
        },
        "additionalProperties": false
      }
    },
    "shared_objective": {
      "type": "object",
      "properties": {
        "coefficients": {
          "type": "array",
          "items": { "type": "number" }
        },
        "offset": { "type": "number", "default": 0.0 }
      },
      "additionalProperties": false
    },
    "scenarios": {
      "type": "array",
      "minItems": 1,
      "maxItems": 2000,
      "items": {
        "type": "object",
        "required": ["id", "coefficients"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "label": { "type": "string" },
          "coefficients": {
            "type": "array",
            "minItems": 1,
            "maxItems": 500,
            "items": { "type": "number" }
          },
          "offset": { "type": "number", "default": 0.0 }
        },
        "additionalProperties": false
      }
    },
    "shared_constraints": {
      "type": "array",
      "maxItems": 1000,
      "items": {
        "type": "object",
        "required": ["coefficients", "relation", "rhs"],
        "properties": {
          "name": { "type": "string" },
          "coefficients": {
            "type": "array",
            "items": { "type": "number" }
          },
          "relation": { "enum": ["<=", "=", ">="] },
          "rhs": { "type": "number" }
        },
        "additionalProperties": false
      }
    },
    "options": {
      "type": "object",
      "properties": {
        "tolerance": { "type": "number", "exclusiveMinimum": 0, "default": 1e-7 },
        "binding_tolerance": { "type": "number", "exclusiveMinimum": 0, "default": 1e-6 },
        "time_limit_seconds": { "type": "number", "exclusiveMinimum": 0 }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

### 9.2 Result Schema (`result_schema_version: "1"`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "contract_version",
    "result_schema_version",
    "capability_id",
    "orientation",
    "guaranteed_value",
    "variables",
    "scenario_values",
    "binding_scenario_ids",
    "delegated_backend"
  ],
  "properties": {
    "contract_version": { "const": "1" },
    "result_schema_version": { "const": "1" },
    "capability_id": {
      "enum": [
        "scenario.linear.min_max_loss",
        "scenario.linear.max_min_reward"
      ]
    },
    "orientation": {
      "enum": [
        "minimize_maximum_loss",
        "maximize_minimum_reward"
      ]
    },
    "guaranteed_value": { "type": ["number", "null"] },
    "variables": {
      "type": "object",
      "additionalProperties": { "type": "number" }
    },
    "scenario_values": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["scenario_id", "value", "is_binding"],
        "properties": {
          "scenario_id": { "type": "string" },
          "value": { "type": "number" },
          "is_binding": { "type": "boolean" }
        },
        "additionalProperties": false
      }
    },
    "binding_scenario_ids": {
      "type": "array",
      "items": { "type": "string" }
    },
    "delegated_backend": {
      "type": "object",
      "required": ["problem_type", "backend_id", "solver_status"],
      "properties": {
        "problem_type": { "enum": ["linear_programming", "mixed_integer_linear_programming"] },
        "backend_id": { "type": "string" },
        "solver_status": { "type": "string" },
        "iterations": { "type": ["integer", "null"] },
        "solve_time_seconds": { "type": ["number", "null"] }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

---

## 10. Canonical JSON Examples

### 10.1 Example 1: `scenario.linear.min_max_loss` Problem Payload

```json
{
  "contract_version": "1",
  "problem_schema_version": "1",
  "capability_id": "scenario.linear.min_max_loss",
  "problem_type": "linear_scenario",
  "orientation": "minimize_maximum_loss",
  "variables": [
    { "name": "x1", "label": "Resource allocation 1", "lower_bound": 0.0, "upper_bound": null, "integrality": "C" },
    { "name": "x2", "label": "Resource allocation 2", "lower_bound": 0.0, "upper_bound": null, "integrality": "C" }
  ],
  "scenarios": [
    { "id": "s1", "label": "High-demand regime", "coefficients": [2.0, -1.0], "offset": 5.0 },
    { "id": "s2", "label": "Low-demand regime", "coefficients": [-1.0, 3.0], "offset": 2.0 },
    { "id": "s3", "label": "Baseline regime", "coefficients": [1.0, 1.0], "offset": -4.0 }
  ],
  "shared_constraints": [
    { "name": "total_budget", "coefficients": [1.0, 1.0], "relation": "=", "rhs": 10.0 }
  ],
  "options": {
    "tolerance": 1e-7,
    "binding_tolerance": 1e-6
  }
}
```

### 10.2 Example 1: Execution Result Payload

```json
{
  "contract_version": "1",
  "result_schema_version": "1",
  "capability_id": "scenario.linear.min_max_loss",
  "orientation": "minimize_maximum_loss",
  "guaranteed_value": 10.857142857142858,
  "variables": {
    "x1": 5.285714285714286,
    "x2": 4.714285714285714
  },
  "scenario_values": [
    { "scenario_id": "s1", "value": 10.857142857142858, "is_binding": true },
    { "scenario_id": "s2", "value": 10.857142857142858, "is_binding": true },
    { "scenario_id": "s3", "value": 6.0, "is_binding": false }
  ],
  "binding_scenario_ids": ["s1", "s2"],
  "delegated_backend": {
    "problem_type": "linear_programming",
    "backend_id": "scipy.highs",
    "solver_status": "optimal",
    "iterations": 2,
    "solve_time_seconds": 0.0004
  }
}
```

---

## 11. Domain Neutrality and Decision Simulator Boundary

Optees owns:
- mathematical models, variable bindings, reductions, solver execution, honest status reporting, and independent validation.

The Decision Simulator owns:
- episode structures, market datasets, portfolio choices, rebalancing horizons, transaction costs, and scoring metrics.

Optees capability interfaces and documentation **must remain strictly domain-neutral** and must never include trading jargon (e.g. assets, stock weights, returns, alpha, beta, slippage, bid-ask, PnL, brokerage).
