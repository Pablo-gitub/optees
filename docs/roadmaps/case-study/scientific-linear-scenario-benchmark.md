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
| **Data Format** | The reviewed paper describes generators and Selection instances; the broader website also catalogues Knapsack, Shortest Path, and TSP data. Exact downloadable formats require a per-artifact audit. | Fortran source and driver arrays | Payoff matrices $A \in \mathbb{R}^{m \times n}$; some tool ecosystems use formats such as Gambit `.nfg` | SMPS format (`.cor`, `.tim`, `.sto`) | Mathematical formulation in text |
| **Problem Dimensions** | Vary by generator and website entry; no single range is frozen by this audit | Vary by driver data | Vary by published example or collection | Vary by collection | Small illustrative networks |
| **Available Reference Results** | The reviewed paper primarily reports generator and computational-performance evidence; this audit did not identify a stable per-instance table suitable as the frozen oracle. | Driver outputs may provide candidate residual references, but their exact provenance and precision remain to be audited. | Some individual literature examples have exact closed-form or rational game values; no corpus was selected in this audit. | Published outcomes generally follow stochastic-programming semantics and cannot be reused as minimax values. | Vary by source; no suitable frozen corpus was selected. |
| **Result Status Type** | Runtime benchmark only (no solution lookup table) | Driver printout candidate | Proven theoretical optimum | Expected-value optimum (incompatible objective) | Average performance statistics |
| **License / Terms** | No dataset licence was established by this audit | Must be checked against the terms attached to the exact Netlib/ACM artifact | Must be checked for each selected source; publication does not imply public domain | Must be checked for each exact artifact | Copyright applies; quotation or redistribution rights require a source-specific audit |
| **In-Repo Committability** | Not established | Not established | Not established | Not established | Not established |
| **Stable external artifact** | The website is live and evolving; exact candidate files still require immutable-byte capture and provenance review | Netlib exposes an Algorithm 495 artifact; byte stability, terms, test data, and expected outputs still require verification | No standard corpus was identified in this bounded review | Netlib hosts SMPS artifacts, but their published objectives use different semantics | No corpus selected |
| **Mathematical Fit: Min-Max Loss** | Exact fit for binary Selection MILP ($\sum x_i = p$) | Lossless mapping via scenario doubling ($s_{i,+}, s_{i,-}$) | Exact fit (Player 1 LP: $x \in \Delta_m$, $n$ scenarios) | **Incompatible:** optimizes expected value $\mathbb{E}$, not $\max_k$ | Min-max regret (incompatible with pure min-max loss) |
| **Mathematical Fit: Max-Min Reward** | No native reward corpus was established; exact sign dualization could exercise the separate max-min capability if a min-max reference value is independently trusted | No native reward semantics, but $\max_x\min_k R_k(x)=-\min_x\max_k[-R_k(x)]$ gives an exact sign-dual construction | Exact fit (Player 2 LP: $y \in \Delta_n$, $m$ scenarios) | **Incompatible with the published oracle:** expectation values are not minimum-scenario rewards | Requires source-specific analysis |
| **Transformation assessment** | Exact for compatible one-stage finite min-max instances; feature coverage varies | Residual-sign doubling is an exact epigraph formulation, not mathematical distortion; it covers only a specialised subfamily | Simplex matrix games map exactly to both orientations but cover a specialised subfamily and should not be presented as operational-uncertainty evidence | Replacing expectation by worst case would change the published problem | Regret instances need scenario-optimum baselines absent from the current pure-guarantee contract |
| **Expected CI runtime** | Must be measured on a selected bounded subset | Must be measured | Must be measured | Must be measured if ever considered under a matching future capability | Must be measured |
| **Additional Dependencies** | None (CSV reader) | None (fixed matrix parser) | None (matrix parser) | SMPS parser required | None |

---

## 4. Rigorous Scientific Analysis of Candidate Sources

### 4.1 Candidate 1: `robust-optimization.com` (Goerigk & Khosravi 2024)
- **Scientific Foundation:** Marc Goerigk and Mohammad Khosravi introduced this library in *"Benchmarking Problems for Robust Discrete Optimization"* (Computers & Operations Research 166, 2024, 106608; arXiv:2201.04985). The authors specifically observed that *“for robust discrete optimization, it seems that no such benchmark currently exists”* and proposed generators for "hard" instances.
- **Why It Must Be Rejected for Current Verification:**
  1. **Absence of Certified Reference Solutions:** Neither the paper nor the website publishes a table of certified optimal objective values (analogous to `00README.QP` or `miplib2017.solu`). The published results consist exclusively of CPU runtime distributions, solve success rates, and MIP solver gap plots across batches of 50 randomly sampled instances. If Optees were to solve these instances and use its own output as the golden reference, it would commit **circular validation** (Stop Condition 10).
  2. **Unclear Licensing Terms:** The website `robust-optimization.com` lacks an explicit open-source license grant (e.g. Apache-2.0, MIT, CC-BY) for the instance data files (Stop Condition 1).
  3. **Mutable Discovery Surface:** The website describes itself as under construction and evolving. That does not make its data invalid, but an implementation would need to freeze the exact source URL, bytes, retrieval date, and locally computed digest (Stop Condition 2).
  4. **Coverage Limitation:** The reviewed benchmark paper focuses on robust discrete optimization and does not provide a native max-min-reward oracle. A sign-dual test is mathematically exact but would be derived coverage rather than an independent reward corpus.
  5. **Unmeasured CI Budget:** The paper deliberately studies hard generators. Runtime must be measured on the exact selected instances and Optees backends before any CI subset can be approved (Stop Condition 8); this audit does not assign unsupported universal runtime ranges.

### 4.2 Candidate 2: Chebyshev $L_\infty$ Approximation (Netlib TOMS 495 / Barrodale & Phillips 1975)
- **Scientific Foundation:** Algorithm 495 (CHEB) solves overdetermined linear systems $\min_{x} \|Ax - b\|_\infty = \min_{x} \max_{i=1,\dots,m} |a_i^T x - b_i|$.
- **Artifact Audit Completed (`OPT-DS-ROBUST-BENCH-A`):** The artifact-level audit has been completed in [Netlib Algorithm 495 Artifact Audit](netlib-495-artifact-audit.md), adopting Conclusion **`C — REFERENCE-ONLY`**:
  1. **Artifact Inventory & Format:** The Netlib archive (`https://www.netlib.org/toms/495`, SHA-256 `8dbff5f53f9d4b76a39885d4b676be6e8529d6b01a679f27fe14b847cc4a8681`) contains exclusively the 298-line Fortran subroutine `CHEB`. It contains **no standalone test datasets, input instances, or solution tables**.
  2. **Licensing Restriction:** CALGO distribution terms include non-commercial conditions. Optees therefore conservatively prohibits vendoring this Fortran code under its Apache-2.0 distribution without separate compatible permission.
  3. **Exact Mathematical Mapping:** Representing each residual by $s_{i,+}=a_i^Tx-b_i$ and $s_{i,-}=-a_i^Tx+b_i$ is an exact algebraic isomorphism to `scenario.linear.min_max_loss`. Similarly, sign duality $R_k(x) = -v_k(x)$ gives an exact algebraic derivation for `scenario.linear.max_min_reward`. Experimental verification proved 100% passing independent validation (`verified` status across all 10 checks).
  4. **Integration Boundary:** Netlib 495 cannot support a benchmark-data downloader because it contains no instances. A five-point example located in NAG documentation maps exactly and has independently derived optimum $x_1^*=4.386$, $x_2^*=0.155$, $z^*=0.115$, but its exact page/version and terms require a separate audit before fixture inclusion is authorized.


### 4.3 Candidate 3: Two-Person Zero-Sum Matrix Games
- **Scientific Foundation:** Under von Neumann’s Minimax Theorem, any matrix $A \in \mathbb{R}^{m \times n}$ has an exact game value $v^*$ such that:
  \[
  \min_{x \in \Delta_m} \max_{j=1,\dots,n} (A^T x)_j = \max_{y \in \Delta_n} \min_{i=1,\dots,m} (A y)_i = v^*
  \]
  This establishes an exact mathematical mapping:
  - Player 1 solves `scenario.linear.min_max_loss` over $x \in \Delta_m$ against $n$ scenarios (columns of $A$);
  - Player 2 solves `scenario.linear.max_min_reward` over $y \in \Delta_n$ against $m$ scenarios (rows of $A$);
  - Both orientations achieve identical objective $v^*$, and binding scenarios identify the support of the opponent’s optimal mixed strategy.
- **Why It Is Not Yet Authorized:**
  1. **Corpus Gap:** This bounded review did not identify a standard corpus with stable artifacts, source-specific redistribution terms, and frozen expected values comparable to the QP collection.
  2. **Valid Cross-Domain Mathematical Evidence:** Matrix games are an exact special case of the two public scenario formulations. They may test the reductions without changing either contract. They must, however, be labelled as cross-domain mathematical evidence rather than evidence about operational uncertainty, and they do not replace the future game-theory capability.
  3. **Coverage Limitation:** Simplex matrix games do not by themselves validate offsets, arbitrary shared constraints, or discrete routing. A scientific suite may combine complementary sources and analytic cases; no single corpus is required to cover every feature.

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
1. **Bounded Evidence Result:** The candidates examined in this planning pass did not establish a source that simultaneously provides stable artifacts, source-specific usable terms, and independently published per-instance values appropriate for immediate integration. This is a conclusion about the reviewed evidence, not a claim that no suitable corpus exists anywhere.
2. **Prevention of Circular Self-Validation:** Fabricating expected objective values by solving unverified instance generators with Optees or third-party MIP solvers would violate Stop Condition 10 and destroy independent verification integrity.
3. **Preservation of Semantic Integrity:** Expected-value stochastic or regret oracles cannot validate a worst-case guarantee without changing the problem. By contrast, exact special-case reductions such as Chebyshev residual doubling and matrix games remain legitimate mathematical evidence when labelled with their limited coverage.
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
| 2 | Stable primary artifact not established | **TRIGGERED FOR CURRENT CANDIDATES** | The robust-optimization website is explicitly evolving, while the exact bytes and stability of the more promising Netlib artifact were not completed in this audit. No universal claim about all possible sources is made. |
| 3 | Verifiable published reference results not established | **TRIGGERED FOR CURRENT CANDIDATES** | No selected artifact/result pair was verified closely enough to freeze as an oracle. This does not assert that the wider literature contains no usable individual examples. |
| 4 | Corpus incompatible with current capability contract | **TRIGGERED** | Stochastic libraries optimize expectation; Kouvelis & Yu optimizes regret; Chebyshev lacks reward orientation. |
| 5 | Need to alter public capability semantics | **NOT TRIGGERED** | No candidate may modify frozen schema v1. Exact special-case mappings and sign dualization fit the existing semantics; adding probabilities or regret would not. |
| 6 | Conversion dependent on assumptions absent from data | **NOT TRIGGERED FOR EXACT MAPPINGS** | Chebyshev residual doubling and finite matrix-game mappings are algebraically exact. This condition remains triggered for conversions that invent probabilities, regret baselines, or unstated constraints. |
| 7 | Benchmark tests only LP/MILP solver without scenario reconstruction | **IMPLEMENTATION CONDITION** | A future test must traverse the registered scenario capability and independently verify scenario values, guarantee, auxiliary value, and binding set; specialised corpora may be complemented by existing analytic cases. |
| 8 | Problem dimensions or solve times unsuitable for CI | **UNRESOLVED** | Runtime and memory must be measured on the exact proposed subset rather than inferred from a paper's broad computational study. |
| 9 | Inability to verify file integrity via checksums | **UNRESOLVED** | A source need not publish SHA-256 itself: Optees may freeze a locally computed digest after provenance and exact bytes are independently reviewed. Artifact stability has not yet been established. |
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
- **Mandatory Independent Validation:** Scientific benchmark candidates must produce a strict `verified` report from `ScenarioIndependentSolutionValidator`, with passing sub-checks across variable vectors, bounds, shared constraints, scenario values, guarantees, auxiliary/delegated-objective consistency, and binding sets. This validator does not make a dual-evidence promise, so missing duals are not a reason to accept `partial` here.

---

## 8. Planned Files for Future Work Unit

When an artifact-level audit authorizes a verified external corpus or a bounded published example set:
- `src/optees/utility/data_adapters/scenario_benchmark_adapter.py`: Data adapter at utility boundary translating source benchmark format into `ContinuousLinearScenarioProblem` (schema v1).
- `scripts/fetch_linear_scenario_benchmark.py`: Isolated acquisition script with SHA-256 verification and path-traversal protection.
- `tests/utility/test_scenario_benchmark_adapter.py`: Unit tests for parser, error handling, and CRLF normalization.
- `tests/utility/test_scenario_benchmark.py`: Benchmark suite marked `@pytest.mark.benchmark` executing selected instances against published literature optima.

---

## 9. Next Authorized Step

- **Immediate action:** Freeze the Netlib 495 artifact audit findings in `netlib-495-artifact-audit.md`.
- **State:** The source survey and the Netlib Algorithm 495 artifact audit (`OPT-DS-ROBUST-BENCH-A`) are complete, concluding with **`C — REFERENCE-ONLY`** (individual published problems authorized as reference cases; downloadable bulk benchmark corpus deferred due to lack of dataset files in Netlib 495). `OPT-DS-ROBUST-BENCH` downloadable benchmark integration remains **planned/deferred**.
- **Next roadmap item:** Return to the primary project sequence (`OPT-DS-04` forecasting evidence protocol or scheduled baseline items).
