# Scientific Benchmark Validation for Linear Min-max and Max-min Optimization

## Document Status

- **Work Unit:** `OPT-DS-ROBUST-BENCH`
- **Capability IDs:**
  - `scenario.linear.min_max_loss` (orientation: `minimize_maximum_loss`)
  - `scenario.linear.max_min_reward` (orientation: `maximize_minimum_reward`)
- **State:** planned
- **Parent Roadmaps:** `docs/roadmaps/case-study/ROADMAP.md` and `docs/roadmaps/project.md`
- **Contract Reference:** `docs/contracts/linear-scenario-optimization-contract.md`
- **Prerequisites:** `ROBUST-C` and `ROBUST-UI` completed (`OPT-DS-03` complete); `OPT-DS-QP-BENCH` completed

---

## 1. Objective and Architectural Boundary

The objective of this work unit is to research, evaluate, and define the scientific validation
strategy for the two frozen linear finite-scenario optimization capabilities in Optees:
- `scenario.linear.min_max_loss`
- `scenario.linear.max_min_reward`

This work unit is strictly independent of `optees-decision-simulator`. It must not introduce
market concepts, portfolio terminology, financial time series, transaction costs, or trading policies.
Optees owns domain-neutral mathematical models, exact reductions, solver execution, honest status
reporting, and independent post-solve solution validation.

Following the engineering standard established in `OPT-DS-QP-BENCH` (Maros–Mészáros benchmark
validation), external scientific evidence must be grounded in primary authoritative literature,
verifiable checksums, reproducible offline acquisition, and strict numerical comparison without
circular self-validation.

---

## 2. Mathematical Reconstruction of Existing Scenario Capabilities

Optees provides two distinct, first-class semantic orientations for linear scenario optimization.
They share the underlying data transfer package (`problem_type: "linear_scenario"`, schema version 1)
while enforcing mathematically distinct formulations, epigraph/hypograph reductions, and result interpretations.

### 2.1 Decision Variables, Bounds, and Integrality

Let $x = (x_1, \dots, x_n)^T \in \mathbb{R}^n$ be the ordered vector of $n \ge 1$ decision variables ($n \le 500$).
Each variable $x_j$ has:
- an immutable unique identifier $name_j \in \text{String}$;
- an optional label $label_j \in \text{String}$;
- box bounds $[l_j, u_j]$ with $l_j \in \mathbb{R} \cup \{-\infty\}$ and $u_j \in \mathbb{R} \cup \{+\infty\}$, $l_j \le u_j$;
- an integrality domain $D_j \in \{\text{CONTINUOUS} (\text{"C"}), \text{INTEGER} (\text{"I"}), \text{BINARY} (\text{"B"})\}$.

The shared feasible region $\mathcal{X} \subseteq \mathbb{R}^n$ is defined by:
\[
\mathcal{X} = \left\{ x \in \mathbb{R}^n \;\middle|\;
l \le x \le u, \quad
x_j \in \mathbb{Z} \; (\forall j \in \mathcal{I}), \quad
x_j \in \{0, 1\} \; (\forall j \in \mathcal{B}), \quad
A_{eq} x = b_{eq}, \quad
A_{ineq} x \le b_{ineq}
\right\}
\]
where $A_{eq} x = b_{eq}$ and $A_{ineq} x \le b_{ineq}$ are optional shared linear equality and
inequality constraints ($m \le 1000$).

### 2.2 Finite Scenario Set and Linear Evaluations

Let $S = (s_1, \dots, s_K)$ be a deterministic, ordered sequence of $K \ge 1$ scenarios ($K \le 2000$).
Each scenario $s_k$ declares:
- a unique scenario identifier $id_k \in \text{String}$;
- an optional label $label_k \in \text{String}$;
- a scenario linear cost/payoff vector $c^{(k)} = (c^{(k)}_1, \dots, c^{(k)}_n)^T \in \mathbb{R}^n$;
- a scenario scalar constant offset $\gamma_k \in \mathbb{R}$ (default $0.0$).

The problem optionally declares a shared base objective vector $c^{(0)} \in \mathbb{R}^n$
and a shared scalar offset $\gamma_0 \in \mathbb{R}$ (default $0.0$).

For any candidate decision vector $x \in \mathcal{X}$, the linear evaluation under scenario $s_k$ is:
\[
v_k(x) = \sum_{j=1}^n \left(c^{(0)}_j + c^{(k)}_j\right) x_j + \left(\gamma_0 + \gamma_k\right) = d^{(k)T} x + \delta_k
\]
where $d^{(k)} = c^{(0)} + c^{(k)} \in \mathbb{R}^n$ and $\delta_k = \gamma_0 + \gamma_k \in \mathbb{R}$.

### 2.3 Orientation 1: Minimize Maximum Loss (`scenario.linear.min_max_loss`)

In this orientation, $v_k(x)$ represents the **loss** incurred under scenario $s_k$.
The worst-case loss is:
\[
L_{\max}(x) = \max_{k \in \{1, \dots, K\}} v_k(x) = \max_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]
The robust optimization problem is:
\[
\min_{x \in \mathcal{X}} L_{\max}(x) = \min_{x \in \mathcal{X}} \max_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]

#### Epigraph Reduction:
Introducing a single continuous auxiliary epigraph variable $\theta \in \mathbb{R}$ (`"_aux_theta"`):
\[
\begin{aligned}
\min_{x \in \mathcal{X}, \; \theta \in \mathbb{R}} \quad & \theta \\
\text{subject to} \quad & d^{(k)T} x - \theta \le -\delta_k, \quad \forall k \in \{1, \dots, K\}
\end{aligned}
\]
At the optimum $(x^*, \theta^*)$:
- Optimal robust objective: $z^* = \theta^* = \max_{k=1,\dots,K} v_k(x^*)$.
- Guarantee value: $\text{guaranteed\_loss} = z^*$. In every scenario $s_k$, $v_k(x^*) \le z^*$.
- Binding scenarios:
  \[
  \mathcal{B}_{\text{loss}} = \left\{ k \in \{1, \dots, K\} \;\middle|\; |v_k(x^*) - z^*| \le \varepsilon_{bind} \max(1.0, |z^*|) \right\}
  \]

### 2.4 Orientation 2: Maximize Minimum Reward (`scenario.linear.max_min_reward`)

In this orientation, $v_k(x)$ represents the **reward** obtained under scenario $s_k$.
The worst-case reward is:
\[
R_{\min}(x) = \min_{k \in \{1, \dots, K\}} v_k(x) = \min_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]
The robust optimization problem is:
\[
\max_{x \in \mathcal{X}} R_{\min}(x) = \max_{x \in \mathcal{X}} \min_{k \in \{1, \dots, K\}} \left( d^{(k)T} x + \delta_k \right)
\]

#### Hypograph Reduction:
Introducing a single continuous auxiliary hypograph variable $\tau \in \mathbb{R}$ (`"_aux_tau"`):
\[
\begin{aligned}
\max_{x \in \mathcal{X}, \; \tau \in \mathbb{R}} \quad & \tau \\
\text{subject to} \quad & -d^{(k)T} x + \tau \le \delta_k, \quad \forall k \in \{1, \dots, K\}
\end{aligned}
\]
At the optimum $(x^*, \tau^*)$:
- Optimal robust objective: $z^* = \tau^* = \min_{k=1,\dots,K} v_k(x^*)$.
- Guarantee value: $\text{guaranteed\_reward} = z^*$. In every scenario $s_k$, $v_k(x^*) \ge z^*$.
- Binding scenarios:
  \[
  \mathcal{B}_{\text{reward}} = \left\{ k \in \{1, \dots, K\} \;\middle|\; |v_k(x^*) - z^*| \le \varepsilon_{bind} \max(1.0, |z^*|) \right\}
  \]

### 2.5 Solver Delegation Rules (LP vs MILP)

The application layer (`SolveScenarioUseCase`) inspects the declared integrality of all decision variables:
1. **Continuous LP Route:** If all $D_j = \text{CONTINUOUS}$, the reduced problem is delegated to `SolveLPUseCase` / `LPSolverPort` (e.g. SciPy/HiGHS).
2. **Mixed-Integer MILP Route:** If any $D_j \in \{\text{INTEGER}, \text{BINARY}\}$, the auxiliary variable ($\theta$ or $\tau$) remains strictly continuous (`"C"`), original variable domains are preserved, and the reduced problem is delegated to `SolveMILPUseCase` / `MILPSolverPort` (e.g. OR-Tools CBC / CP-SAT).

### 2.6 Status Reporting and Independent Validation

- **Mathematical Statuses:** `optimal`, `feasible`, `infeasible`, `unbounded`, `not_solved`.
- **Termination Reasons:** `completed`, `time_limit`, `iteration_limit`, `cancelled`, `dependency_failure`, `internal_error`.
- **Independent Validation (`ScenarioIndependentSolutionValidator`):**
  Executes completely outside the solver, checking:
  1. `scenario.variable_vector`: correct dimension, exact declared variable names in declared order, finite values;
  2. `scenario.bounds`: compliance with $[l_j, u_j]$ and integrality for discrete variables;
  3. `scenario.constraints`: compliance with shared linear equalities and inequalities;
  4. `scenario.values`: exact recalculation of every $v_k(x^*) = d^{(k)T} x^* + \delta_k$ and comparison with reported `scenario_values[k].value`;
  5. `scenario.guarantee`: recalculation of worst-case value ($\max_k$ or $\min_k$) and comparison with reported `guaranteed_value`;
  6. `scenario.binding_set`: verification of `binding_scenario_ids` and `is_binding` flags against tolerance $\varepsilon_{bind}$.
  Validation returns: `verified`, `partial`, `failed`, or `not_available` (for candidates without solution).

---

## 3. Candidate Benchmark Sources: Comparative Evaluation

To identify external, reproducible scientific benchmarks, five candidate problem families were surveyed across
academic optimization and operations research literature:

| Criterion / Feature | Candidate 1: Robust Discrete Optimization Library | Candidate 2: Chebyshev $L_\infty$ Approximation | Candidate 3: Two-Person Zero-Sum Matrix Games | Candidate 4: Stochastic Programming Collections | Candidate 5: Monograph Reference Problems |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Authors & Publication** | Marc Goerigk and Mohammad Khosravi, *Computers & Operations Research* 166 (2024), 106608 | I. Barrodale and C. Phillips, *ACM TOMS* 1(3) (1975), Algorithm 495 | J. von Neumann (1928), D. Gale, H. W. Kuhn, A. W. Tucker (1950), V. Chvátal (1983) | J. R. Birge, C. R. Holmes et al. (POSTS / Netlib SMPS) | P. Kouvelis & G. Yu (1997), I. Averbakh (2001) |
| **Primary URL / Host** | `https://robust-optimization.com` | `http://www.netlib.org/toms/495` | Textbook / theoretical literature; Gambit (`gambit-project.org`) | `http://www.netlib.org/lp/data/` (SMPS) | Monograph literature (Kluwer / Springer) |
| **Data Format** | CSV ($n, p, N$ header + cost rows) | Fortran text / driver arrays | Payoff matrices $A \in \mathbb{R}^{m \times n}$, Gambit `.nfg` | SMPS format (`.cor`, `.tim`, `.sto`) | Mathematical formulation in text |
| **Problem Dimensions** | $n \in [50, 100]$, $N \in [5, 50]$, $p \in [10, 75]$ | $m \in [10, 100]$, $n \in [2, 10]$ | $m, n \in [2, 50]$ | Rows $\sim 100 - 5000$, scenarios $5 - 100$ | Small illustrative networks |
| **Available Reference Results** | **None.** Only solver CPU runtimes and MIP gap boxplots are published. | Selected polynomial fitting errors in driver sample outputs. | Exact closed-form / rational game values $v^* \in \mathbb{Q}$ published in literature. | Expected value $\mathbb{E}[c^T x]$, **not** minimax. | Average solve times across random seeds. |
| **Result Status Type** | Runtime benchmark only (no solution lookup table) | Driver printout candidate | Proven theoretical optimum | Expected-value optimum (incompatible objective) | Average performance statistics |
| **License / Terms** | Unspecified / unclear on website | ACM Software License (Netlib public research) | Academic / textbook public domain | Netlib open research data | Copyrighted book chapters |
| **In-Repo Committability** | Permissible only if small and public; license is ambiguous | Permissible (small driver test matrices) | Permissible (matrices can be embedded in tests) | Permissible for Netlib smoke files | Not distributable as bulk files |
| **External Checksummed Archive** | No static ZIP archive with published SHA-256; dynamic CMS | Yes (`495.gz` on Netlib) | No centralized checksummed matrix game repository | Yes (Netlib gzip files) | No online repository |
| **Mathematical Fit: Min-Max Loss** | Exact fit for binary Selection MILP ($\sum x_i = p$) | Lossless mapping via scenario doubling ($s_{i,+}, s_{i,-}$) | Exact fit (Player 1 LP: $x \in \Delta_m$, $n$ scenarios) | **Incompatible:** optimizes expected value $\mathbb{E}$, not $\max_k$ | Min-max regret (incompatible with pure min-max loss) |
| **Mathematical Fit: Max-Min Reward** | **Zero fit.** Only minimization criteria are modeled. | **Zero fit.** $L_\infty$ norm is strictly minimization. | Exact fit (Player 2 LP: $y \in \Delta_n$, $m$ scenarios) | **Incompatible:** optimizes expected value $\mathbb{E}$, not $\min_k$ | **Zero fit.** |
| **Semantic Loss / Transformation** | None on loss side; binary selection only | Severe: doubles rows into $+r_i, -r_i$; destroys scenario semantics | Severe domain conflation: game theory mixed strategies $\ne$ scenario uncertainty | Fatal: confuses stochastic expectation with robust worst-case | Fatal: confuses regret baseline with robust guarantee |
| **Expected CI Runtime** | High (50–600s per instance in CPLEX) | Low ($< 0.1$s) | Low ($< 0.1$s) | High ($> 10$s) | Variable |
| **Additional Dependencies** | None (CSV reader) | None (fixed matrix parser) | None (matrix parser) | SMPS parser required | None |

---

## 4. Rigorous Scientific Analysis of Candidate Sources

### 4.1 Candidate 1: `robust-optimization.com` (Goerigk & Khosravi 2024)
- **Scientific Foundation:** Marc Goerigk and Mohammad Khosravi introduced this library in *"Benchmarking Problems for Robust Discrete Optimization"* (Computers & Operations Research 166, 2024, 106608; arXiv:2201.04985). The authors specifically observed that *“for robust discrete optimization, it seems that no such benchmark currently exists”* and proposed generators for "hard" instances.
- **Why It Must Be Rejected for Current Verification:**
  1. **Absence of Certified Reference Solutions:** Neither the paper nor the website publishes a table of certified optimal objective values (analogous to `00README.QP` or `miplib2017.solu`). The published results consist exclusively of CPU runtime distributions, solve success rates, and MIP solver gap plots across batches of 50 randomly sampled instances. If Optees were to solve these instances and use its own output as the golden reference, it would commit **circular validation** (Stop Condition 10).
  2. **Unclear Licensing Terms:** The website `robust-optimization.com` lacks an explicit open-source license grant (e.g. Apache-2.0, MIT, CC-BY) for the instance data files (Stop Condition 1).
  3. **Unstable Primary Source:** The site is a dynamic WordPress installation without immutable, versioned release archives with published SHA-256 digests (Stop Condition 2).
  4. **Single-Orientation & Discrete Only:** The library contains only minimization instances (Min-Max and Min-Max Regret) and only binary combinatorial structures ($\sum x_i = p$, $x_i \in \{0, 1\}$). It offers zero continuous LP problems and zero instances for `maximize_minimum_reward` (Stop Condition 4).
  5. **CI Budget Incompatibility:** The instances are deliberately engineered to be computationally pathological, requiring hundreds of seconds on commercial MIP solvers (CPLEX/Gurobi) for modest sizes ($n=100$), which is incompatible with deterministic automated testing (Stop Condition 8).

### 4.2 Candidate 2: Chebyshev $L_\infty$ Approximation (Netlib TOMS 495 / Barrodale & Phillips 1975)
- **Scientific Foundation:** Algorithm 495 (CHEB) solves overdetermined linear systems $\min_{x} \|Ax - b\|_\infty = \min_{x} \max_{i=1,\dots,m} |a_i^T x - b_i|$.
- **Why It Must Be Rejected for Scenario Validation:**
  1. **Semantic Distortion via Scenario Doubling:** An overdetermined equation $a_i^T x \approx b_i$ has no intrinsic scenario meaning. Representing it in Optees requires generating $2m$ artificial scenarios: $s_{i,+} = a_i^T x - b_i$ and $s_{i,-} = -a_i^T x + b_i$. This artificial transformation introduces mathematical artifacts (e.g. mutually exclusive binding pairs) that do not reflect genuine operational scenarios (Stop Condition 6).
  2. **Zero Coverage for Max-Min Reward:** Chebyshev approximation is fundamentally a norm minimization problem ($L_\infty$). It cannot model `maximize_minimum_reward` without destroying its mathematical formulation (Stop Condition 4).
  3. **Inadequate Structural Verification:** Chebyshev regression problems have unconstrained variables $x \in \mathbb{R}^n$, zero box bounds, no shared constraints ($A_{eq} x = b_{eq}$), and no discrete domains. Testing Optees against them would exercise only the unconstrained epigraph reduction, failing to validate shared constraints, bound checking, or MILP orchestration (Stop Condition 7).

### 4.3 Candidate 3: Two-Person Zero-Sum Matrix Games
- **Scientific Foundation:** Under von Neumann’s Minimax Theorem, any matrix $A \in \mathbb{R}^{m \times n}$ has an exact game value $v^*$ such that:
  \[
  \min_{x \in \Delta_m} \max_{j=1,\dots,n} (A^T x)_j = \max_{y \in \Delta_n} \min_{i=1,\dots,m} (A y)_i = v^*
  \]
  This establishes an exact mathematical mapping:
  - Player 1 solves `scenario.linear.min_max_loss` over $x \in \Delta_m$ against $n$ scenarios (columns of $A$);
  - Player 2 solves `scenario.linear.max_min_reward` over $y \in \Delta_n$ against $m$ scenarios (rows of $A$);
  - Both orientations achieve identical objective $v^*$, and binding scenarios identify the support of the opponent’s optimal mixed strategy.
- **Why It Must Not Be Used as a Benchmark Corpus for Scenarios:**
  1. **Absence of a Centralized Benchmark Archive:** There is no standard, checksummed, institutional archive of zero-sum matrix games comparable to Netlib or Maros–Mészáros. Games are either published individually in textbooks (e.g. Chvátal 1983, Gale 1960) or procedurally generated by tools like GAMUT (Stop Condition 2 & 9).
  2. **Domain Conflation and Architectural Boundary:** Optees explicitly maintains Game Theory (`game_theory.two_player_zero_sum`) as a planned future capability on its product roadmap (`docs/roadmaps/project.md` line 9 and 180–184). Using zero-sum matrix games as an ad-hoc proxy for scenario optimization conflates two distinct domain models: strategic adversarial equilibrium versus robust decision-making under states of nature (Stop Condition 4 & 5).
  3. **Lack of Generalized Scenario Features:** Matrix games exclusively use simplex constraints ($\sum x_i = 1, x \ge 0$), zero scenario offsets ($\delta_k = 0$), zero base objective ($c^{(0)} = 0$), and strictly continuous variables. They do not validate general shared constraints, box bounds, offsets, or discrete MILP routing (Stop Condition 7).

### 4.4 Candidate 4: Stochastic Programming Collections (Netlib SMPS / POSTS)
- **Fatal Conceptual Flaw:** Stochastic programming collections minimize the **expected value** under known probability distributions: $\min \mathbb{E}_{s}[c(s)^T x]$.
- **Incompatibility:** Scenario optimization in Optees minimizes the **maximum loss** (or maximizes the **minimum reward**) without probabilities: $\min \max_k v_k(x)$.
- Solving SMPS problems as robust minimax problems would produce arbitrary numbers that have never been published or certified in the scientific literature, directly triggering Stop Condition 4 and Stop Condition 10.

### 4.5 Candidate 5: Monograph Reference Problems (Kouvelis & Yu 1997 / Averbakh 2001)
- **Fatal Conceptual Flaw:** The classic monograph of Kouvelis & Yu (1997) focuses predominantly on **min-max regret**:
  \[
  R(x, s) = v(x, s) - \min_{x' \in \mathcal{X}} v(x', s)
  \]
  Min-max regret requires computing scenario-specific optimal baselines before solving the robust master problem. Optees linear scenario capabilities (`scenario.linear.min_max_loss` and `scenario.linear.max_min_reward`) implement **pure worst-case guarantee**, not regret (min-max regret is tracked as a future workflow capability `OPT-DS-07`). Evaluating pure min-max on regret instances produces meaningless values with no literature baseline (Stop Condition 4).

---

## 5. Decision and Selected Strategy

### Normative Decision: Conclusion E

Among the authorized conclusions defined in the work unit mandate:
- **A.** Corpus selected and suitable for both capabilities.
- **B.** Corpus selected only for min-max.
- **C.** Corpus selected only for max-min.
- **D.** Two distinct corpora necessary.
- **E. No external corpus is currently sufficiently reliable: maintain analytical reference cases and defer external corpus integration.**

**Conclusion E is selected.**

### Rationale:
1. **Scientific Honesty:** As confirmed by current operations research literature (Goerigk & Khosravi 2024), there is currently **no standardized, peer-reviewed, open-licensed benchmark library with certified published optimal values** for finite-scenario linear min-max and max-min optimization.
2. **Prevention of Circular Self-Validation:** Fabricating expected objective values by solving unverified instance generators with Optees or third-party MIP solvers would violate Stop Condition 10 and destroy independent verification integrity.
3. **Preservation of Semantic Integrity:** Forcing external problems from unrelated domains (such as Chebyshev regression or expected-value stochastic programs) would require artificial scenario doubling or semantic distortions that fail to test genuine robust scenario decision-making.
4. **Current Verification Baseline is Rigorous and Complete:** Optees already possesses a fully verified, deterministic, hand-calculable analytical reference suite in `tests/data/scenario/reference_cases.json`, covering:
   - continuous problems with multiple binding scenarios and mixed signs;
   - continuous problems with strictly negative worst-case guarantees;
   - discrete/binary selection MILP problems;
   - contradictory infeasible scenario constraints;
   - unbounded descent rays;
   - independent validation guarantees (`verified`, `partial`, `not_available`).
   These cases have closed-form rational optima certified by independent mathematical derivation.

---

## 6. Stop Conditions Audit

Prior to any future external benchmark integration, all 10 mandatory stop conditions must be verified.
For the current work unit, the audit confirms why external integration must be deferred:

| # | Stop Condition | Status | Empirical Evidence |
| :--- | :--- | :--- | :--- |
| 1 | Undetermined or restrictive redistribution license | **TRIGGERED** | `robust-optimization.com` lacks an explicit open-source license; textbook examples are copyrighted. |
| 2 | Unstable primary source | **TRIGGERED** | No static institutional repository (like SuiteSparse or Imperial College) exists for finite linear scenarios. |
| 3 | Absence of verifiable published reference results | **TRIGGERED** | Literature on robust discrete optimization publishes runtime comparisons and solve rates, not certified optimal value tables. |
| 4 | Corpus incompatible with current capability contract | **TRIGGERED** | Stochastic libraries optimize expectation; Kouvelis & Yu optimizes regret; Chebyshev lacks reward orientation. |
| 5 | Need to alter public capability semantics | **PASSED** | Optees strictly refuses to modify frozen schema v1 or add artificial probabilities. |
| 6 | Conversion dependent on assumptions absent from data | **TRIGGERED** | Chebyshev requires arbitrary scenario doubling ($+r_i, -r_i$); matrix games require assuming adversarial zero-sum equilibrium. |
| 7 | Benchmark tests only LP/MILP solver without scenario reconstruction | **TRIGGERED** | Flattened MPS/LP benchmarks (like MIPLIB) bypass scenario decomposition, epigraph bounds, and binding set analysis. |
| 8 | Problem dimensions or solve times unsuitable for CI | **TRIGGERED** | Synthetic "hard" instances require 10–600 seconds per instance on CPLEX, far exceeding the CI budget. |
| 9 | Inability to verify file integrity via checksums | **TRIGGERED** | No authoritative SHA-256 manifest exists for scenario benchmark suites. |
| 10 | Circular use of Optees to produce expected reference values | **TRIGGERED** | Running Optees on unverified instances to generate "expected" answers would constitute circular pseudo-validation. |

**Conclusion:** Multiple stop conditions are triggered. Proceeding with external corpus integration at this stage would violate repository quality standards. Deferral is scientifically mandatory.

---

## 7. Mandatory Standards for Future External Benchmark Implementation

When an authoritative external benchmark library for linear scenario optimization becomes available
in the scientific literature, its implementation must comply with the following non-negotiable rules:

### 7.1 Security, Parsing, and Extraction Rules
- **Checksum Verification:** Downloaded archives must be validated against hardcoded, authoritative SHA-256 digests before extraction. Individual selected problem files must also have verified individual SHA-256 digests.
- **Strict Bounded Quotas:** Acquisition scripts must enforce hard limits on download size ($\le 25$ MB), uncompressed file size ($\le 50$ MB), number of records ($\le 50000$), and problem dimensions ($n \le 500, K \le 2000$).
- **Atomic Extraction & Path Protection:** Extraction must be atomic into isolated cache (`~/.cache/optees/benchmarks/linear_scenario/`). Archives must reject absolute paths, directory traversal sequences (`..`), symlinks, and duplicate member names.
- **Idempotent `--check-only` Mode:** The acquisition script must provide a non-modifying `--check-only` flag that verifies existing cache integrity without making network requests.
- **Zero Network in Tests:** Pytest test runs and Python module imports must make zero network requests. If cache is unpopulated, tests must skip cleanly with human-actionable instructions.
- **Fail-Closed Parser:** Parsers must strictly reject malformed headers, unexpected tokens, non-finite values (`NaN`, `Inf`), duplicate variable/scenario identifiers, and undeclared entity references.

### 7.2 Numerical Comparison and Validation Rules
- **Tolerances:** Assertions must use documented tolerances matching the contract:
  - Feasibility and bound tolerance: $\varepsilon_{tol} = 10^{-7}$;
  - Relative and absolute objective tolerance: `rel=1e-4, abs=1e-4`;
  - Binding scenario classification tolerance: $\varepsilon_{bind} = 10^{-6}$.
- **Full Epigraph & Scenario Recalculation:** Benchmark assertions must not test only the scalar objective. They must verify:
  1. that every scenario evaluation $v_k(x^*)$ matches reported values;
  2. that worst-case bound matches $\max_k v_k(x^*)$ (loss) or $\min_k v_k(x^*)$ (reward);
  3. that all binding scenarios are correctly identified in declared sequence;
  4. that non-binding scenarios satisfy strict inequality against the guarantee.
- **Public Surface Execution:** Tests must invoke `create_local_optimization_service().solve("scenario.linear.min_max_loss", payload)` or `create_local_optimization_service().solve("scenario.linear.max_min_reward", payload)`. They must never bypass public capability entrypoints by invoking underlying LP/MILP solvers directly.
- **Mandatory Independent Validation:** The independent validation report (`ScenarioIndependentSolutionValidator`) must be asserted to return status `verified` (or `partial` only if dual information is absent), with passing sub-checks across variable vectors, bounds, shared constraints, scenario values, guarantees, and binding sets.

---

## 8. Planned Files for Future Work Unit

When authorized by the appearance of a verified external corpus or an approved community standard:
- `src/optees/utility/data_adapters/scenario_benchmark_adapter.py`: Data adapter at utility boundary translating source benchmark format into `ContinuousLinearScenarioProblem` (schema v1).
- `scripts/fetch_linear_scenario_benchmark.py`: Isolated acquisition script with SHA-256 verification and path-traversal protection.
- `tests/utility/test_scenario_benchmark_adapter.py`: Unit tests for parser, error handling, and CRLF normalization.
- `tests/utility/test_scenario_benchmark.py`: Benchmark suite marked `@pytest.mark.benchmark` executing selected instances against published literature optima.

---

## 9. Next Authorized Step

- **Immediate action:** Commit this planning and evaluation document to freeze the scientific evaluation and Stop Condition findings.
- **State:** `OPT-DS-ROBUST-BENCH` remains **planned**; integration is deferred pending authoritative external corpus availability.
- **Next roadmap item:** Return to the primary project sequence (`OPT-DS-04` forecasting evidence protocol or scheduled baseline items).
