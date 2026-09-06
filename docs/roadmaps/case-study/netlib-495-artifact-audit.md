# Netlib TOMS Algorithm 495 Artifact Audit

## 1. Audit Status

- **Work Unit:** `OPT-DS-ROBUST-BENCH-A`
- **Target Capabilities:**
  - `scenario.linear.min_max_loss` (primary reduction)
  - `scenario.linear.max_min_reward` (exact derived sign-dual reduction)
- **Evaluation Status:** **Complete — Audit and Experimental Verification Performed**
- **Conclusion:** **`C — REFERENCE-ONLY`**
  - The Netlib Algorithm 495 distribution provides the Fortran subroutine `CHEB`, but contains **no standalone test datasets, input instances, or reference solution tables**.
  - ACM software policy imposes non-commercial restrictions that preclude vendoring the Fortran source code into the repository.
  - The mathematical reduction of discrete Chebyshev linear approximation via residual doubling is an exact algebraic isomorphism to `scenario.linear.min_max_loss`, and the sign-dual mapping is exact for `scenario.linear.max_min_reward`.
  - Individual problems published in the accompanying literature (Barrodale & Phillips 1975, NAG `e02gcc`) have closed-form analytical optima and are authorized exclusively as **reference cases** for fixture suites, not as a downloadable bulk benchmark corpus.

---

## 2. Primary Source and Bibliography

- **Repository / Collection:** Netlib Collected Algorithms of the ACM (CALGO), `toms` section.
- **Entry in Netlib Master Index (`https://www.netlib.org/toms/index`):**
  ```text
  file    toms/495
  keywords Chebyshev solution, linear system, linear programming, simplex method
  gams    D9a2
  title   CHEB
  for     overdetermined systems of linear equations in the Chebyshev norm
  alg     a variant of the simplex method
  by      I. Barrodale and C. Phillips
  ref     ACM TOMS 1 (1975) 264-270
  ```
- **Primary Canonical URL:** `https://www.netlib.org/toms/495` (also accessible as `https://www.netlib.org/toms/495.gz`).
- **Authors:** Ian Barrodale (Department of Mathematics, University of Victoria, Victoria, B.C., Canada) and Christopher Phillips (Department of Computational and Statistical Science, University of Liverpool, Liverpool, England).
- **Primary Publication:**
  - Ian Barrodale and C. Phillips, *Algorithm 495: Solution of an Overdetermined System of Linear Equations in the Chebyshev Norm [F4]*, ACM Transactions on Mathematical Software (TOMS), Vol. 1, No. 3, September 1975, pp. 264–270.
  - DOI: [10.1145/355644.355651](https://doi.org/10.1145/355644.355651).
- **Precursor and Literature Context:**
  - I. Barrodale and C. Phillips, *An Improved Algorithm for Discrete Chebyshev Linear Approximation*, Proceedings of the 4th Manitoba Conference on Numerical Mathematics, 1974, pp. 177–190.
  - NAG Library documentation for routine `e02gcc` (*nag_linf_fit*), which implements the Barrodale–Phillips simplex variant and provides standardized polynomial test data.
- **Institutional Custody:** Netlib is maintained by AT&T Bell Laboratories, the University of Tennessee at Knoxville (UTK), and Oak Ridge National Laboratory (ORNL). CALGO is an official publication series of the Association for Computing Machinery (ACM).

---

## 3. Physical Artifact Inventory

The artifact was downloaded into an isolated temporary directory outside the Git workspace (`/tmp/toms495_audit/`).
Inspection of the downloaded stream and decompressed file established the following physical facts:

1. **Single-File Distribution:** Unlike multi-problem benchmark repositories (e.g. Maros–Mészáros or MIPLIB), Netlib distributes Algorithm 495 as a single raw file (`toms/495`), served with gzip compression (`Content-Encoding: gzip` or `495.gz`).
2. **Absence of Separate Data Files:** There are no accompanying data files (`495-data`, `495-test`, or `.dat` archives). Requests to adjacent paths on Netlib return HTTP 404.
3. **Internal File Contents:**
   - The file consists of exactly 298 lines of Fortran source code (plus 1 trailing newline, total 299 lines, LF line endings, 8,872 bytes).
   - Lines 1–46 contain a comment block describing `SUBROUTINE CHEB` and its 13 arguments (`M, N, MDIM, NDIM, A, B, TOL, RELERR, X, RANK, RESMAX, ITER, OCODE`).
   - Lines 47–60 contain an optional column-operation optimization helper `SUBROUTINE COL`.
   - Lines 61–298 implement `SUBROUTINE CHEB` using a modified two-phase simplex algorithm operating directly on the transposed tableau.
4. **Deficiencies as a Benchmark Corpus:**
   - **No test driver:** The file contains no `PROGRAM MAIN` or driver routine.
   - **No test inputs:** No matrix coefficients, RHS vectors, or curve-fitting datasets are defined in the file.
   - **No published outputs:** No numerical output tables, iteration logs, or solution vectors are bundled in the artifact.

---

## 4. Checksums and Verification Table

All byte counts and cryptographic digests were computed directly on the downloaded Netlib files:

| Artifact | Canonical Source URL | Size (Bytes) | SHA-256 Digest |
| :--- | :--- | :--- | :--- |
| `495.gz` (compressed) | `https://www.netlib.org/toms/495` | 2,881 | `8dbff5f53f9d4b76a39885d4b676be6e8529d6b01a679f27fe14b847cc4a8681` |
| `495` (decompressed) | Extracted from `495.gz` | 8,872 | `a85e4eda06d4e02703fc0eadfa4e704180d29ecad6d475a817cb368e5b4d1e46` |

---

## 5. Usage Terms and Licensing Audit

A strict legal inspection of the artifact and the upstream distribution terms was conducted:

1. **Governing Policy:** The Netlib master index for TOMS explicitly declares:
   > *"Use of ACM Algorithms is subject to the ACM Software Copyright and License Agreement."*
2. **Historical ACM Software Policy (Pre-2013):**
   - Software published in ACM TOMS prior to 2013 is copyrighted by the Association for Computing Machinery.
   - The applicable ACM Software Copyright and License Notice grants royalty-free, non-exclusive rights to execute, copy, and modify the software **strictly for non-commercial research and education**.
   - Commercial use, sublicensing, or redistribution in proprietary or commercial packages requires explicit written authorization or commercial licensing from the ACM.
3. **Open-Source Compatibility Assessment:**
   - The non-commercial restriction in the ACM license violates Criterion 6 ("No Discrimination Against Fields of Endeavor") of the Open Source Definition (OSD).
   - Consequently, the Fortran source code in `toms/495` **cannot be vendored or redistributed directly inside an open-source repository** under permissive terms (such as MIT, Apache 2.0, or BSD).
4. **Status of Factual Problem Definitions:**
   - Under international copyright law and US copyright principles, mathematical problem formulations, numerical coefficients $(A, b)$, and objective values are factual mathematical truths that cannot be copyrighted.
   - Therefore, while the Fortran code cannot be vendored, the mathematical test cases described in the accompanying paper are fully usable for independent regression and validation.

---

## 6. Format Description

- **Format:** Fixed-form Fortran 66/77 source text.
- **Card Columns:** Standard 72-column card layout with sequence identifiers in columns 73–80 (e.g. `CHE   10`, `CHE   20`, ..., `CHE 1940`).
- **Data Types:** Single-precision real arrays (`REAL A(NDIM, MDIM), B(MDIM), X(NDIM)`).
- **Tableau Layout:** Column-major transposed representation: $A$ on entry holds the transpose of the $M \times N$ system matrix in its first $M$ columns and $N$ rows.

---

## 7. Included Cases Inventory

Because the Netlib artifact contains exclusively subroutine source code, test cases must be sourced from the primary literature:

| Problem ID | Origin / Publication | Dimensions ($M \times N$) | Problem Description | Reference Source |
| :--- | :--- | :--- | :--- | :--- |
| `BP1975-LINE` | Barrodale & Phillips (1975) / NAG `e02gcc` | $5 \times 2$ | Straight line fit $y(t) = x_1 + x_2 t$ to 5 data points: $t \in \{0.0, 0.2, 0.4, 0.6, 0.8\}$, $y \in \{4.501, 4.360, 4.333, 4.418, 4.625\}$. | Paper Section 4 / NAG Manual |
| `BP1975-QUAD` | Barrodale & Phillips (1975) Section 4 | $5 \times 3$ | Quadratic fit $y(t) = x_1 + x_2 t + x_3 t^2$ to the same 5 data points. | Paper Section 4 |
| `BP1975-EXP` | Barrodale & Phillips (1975) Table 1 | $21 \times 4$ | Discrete approximation of $e^t$ over $[0, 1]$ on an equidistant grid of 21 points using a cubic polynomial. | Paper Section 5 |

---

## 8. Available Reference Outputs

For `BP1975-LINE`, the exact mathematical optimum is analytically solvable in closed rational form:
- **System of Equations:**
  $x_1 + 0.0 x_2 \approx 4.501$
  $x_1 + 0.2 x_2 \approx 4.360$
  $x_1 + 0.4 x_2 \approx 4.333$
  $x_1 + 0.6 x_2 \approx 4.418$
  $x_1 + 0.8 x_2 \approx 4.625$
- **Equioscillating Active Set:**
  By Chebyshev equioscillation theory, with $N=2$ unknowns, there exist $N+1=3$ points where the residual achieves the maximum magnitude with alternating signs.
  For this problem, the active equioscillating points are $t_0 = 0.0$, $t_2 = 0.4$, and $t_4 = 0.8$:
  - At $t=0.0$: $r_0(x) = x_1 - 4.501 = -z^*$
  - At $t=0.4$: $r_2(x) = x_1 + 0.4 x_2 - 4.333 = +z^*$
  - At $t=0.8$: $r_4(x) = x_1 + 0.8 x_2 - 4.625 = -z^*$
- **Closed-Form Rational Solution:**
  - $x_2^* = \frac{4.625 - 4.501}{0.8} = \frac{0.124}{0.8} = 0.155 = \frac{31}{200}$
  - $x_1^* = 4.386 = \frac{2193}{500}$
  - $z^* = \text{RESMAX}^* = 0.115 = \frac{23}{200}$
- **Residual Evaluations:**
  - $r_0 = 4.386 - 4.501 = -0.115$ (magnitude $0.115$)
  - $r_1 = 4.386 + 0.155(0.2) - 4.360 = 4.417 - 4.360 = +0.057 < 0.115$
  - $r_2 = 4.386 + 0.155(0.4) - 4.333 = 4.448 - 4.333 = +0.115$ (magnitude $0.115$)
  - $r_3 = 4.386 + 0.155(0.6) - 4.418 = 4.479 - 4.418 = +0.061 < 0.115$
  - $r_4 = 4.386 + 0.155(0.8) - 4.625 = 4.510 - 4.625 = -0.115$ (magnitude $0.115$)
- **Nature of Output:** Certified global mathematical optimum, verified by independent rational algebra and dual equioscillation certificates.

---

## 9. Exact Min-Max Formulation

The discrete linear Chebyshev approximation problem:
\[
\min_{x \in \mathbb{R}^N} \|A x - b\|_\infty = \min_{x \in \mathbb{R}^N} \max_{i=1,\dots,M} |a_i^T x - b_i|
\]
is mapped to `scenario.linear.min_max_loss` through residual doubling.

For each equation $i \in \{1,\dots,M\}$, two linear scenarios are defined:
1. **Positive residual scenario ($s_{i,+}$):**
   \[
   v_{i,+}(x) = a_i^T x - b_i
   \]
   - Scenario coefficients: $a_i = (A_{i,1}, \dots, A_{i,N})$
   - Scenario offset: $\beta_{i,+} = -b_i$
2. **Negative residual scenario ($s_{i,-}$):**
   \[
   v_{i,-}(x) = -a_i^T x + b_i
   \]
   - Scenario coefficients: $-a_i = (-A_{i,1}, \dots, -A_{i,N})$
   - Scenario offset: $\beta_{i,-} = b_i$

Total scenarios: $K = 2M$.
Because $|r_i(x)| = \max(r_i(x), -r_i(x))$, we have:
\[
\max_{i=1,\dots,M} |a_i^T x - b_i| = \max_{k \in \{s_{1,+}, s_{1,-}, \dots, s_{M,+}, s_{M,-}\}} v_k(x)
\]
Minimizing this maximum loss over unconstrained $x$ yields the exact Chebyshev solution:
- Optimal guaranteed value: $z^* = \text{RESMAX}^* \ge 0$.
- Binding scenarios: exactly those scenarios where $v_k(x^*) = z^*$. When $\text{RESMAX}^* > 0$, for each active equation $i$, exactly one of $\{s_{i,+}, s_{i,-}\}$ is binding.

---

## 10. Derived Max-Min Transformation

The contract identity for `scenario.linear.max_min_reward` is:
\[
\max_x \min_k R_k(x) = -\min_x \max_k [-R_k(x)]
\]
Defining $R_k(x) = -v_k(x)$ produces an exact algebraic transformation:
- Positive reward scenario: $R_{i,+}(x) = -v_{i,+}(x) = -a_i^T x + b_i$ (coefficients $-a_i$, offset $+b_i$).
- Negative reward scenario: $R_{i,-}(x) = -v_{i,-}(x) = a_i^T x - b_i$ (coefficients $+a_i$, offset $-b_i$).

Properties:
- **Optimal decision vector:** Identical $x^*$.
- **Optimal guaranteed value:** Exactly $-z^* = -\text{RESMAX}^* \le 0$.
- **Binding scenarios:** Identical scenario subset $\{k \mid R_k(x^*) = -z^*\} = \{k \mid v_k(x^*) = z^*\}$.
- **Status:** This is an exact algebraic derivation to validate hypograph reduction, sign handling, and result reconstruction. It is not an independent empirical reward scenario.

---

## 11. Field-by-Field Mapping to Optees Contract

The mapping into Optees public problem schema v1 (`ContinuousLinearScenarioProblem`) is deterministic and complete:

| Optees Problem Field | Source / Transformation | BP1975-LINE Example Value |
| :--- | :--- | :--- |
| `version` | Contract schema version | `"1"` |
| `problem_type` | Capability category | `"linear_scenario"` |
| `orientation` | Loss minimization or reward maximization | `"minimize_maximum_loss"` / `"maximize_minimum_reward"` |
| `variables[j].name` | Unknown index identifier | `"x1"`, `"x2"`, ... |
| `variables[j].integrality` | Continuous variable type | `"C"` |
| `variables[j].lower_bound` | Unconstrained approximation variable | `null` |
| `variables[j].upper_bound` | Unconstrained approximation variable | `null` |
| `scenarios[2i].id` | Positive residual scenario identifier | `"s0_pos"`, `"s1_pos"`, ... |
| `scenarios[2i].coefficients` | Row $i$ of matrix $A$ (or $-A$ for reward) | `[1.0, 0.0]`, `[1.0, 0.2]`, ... |
| `scenarios[2i].offset` | $-b_i$ (or $+b_i$ for reward) | `-4.501`, `-4.360`, ... |
| `scenarios[2i+1].id` | Negative residual scenario identifier | `"s0_neg"`, `"s1_neg"`, ... |
| `scenarios[2i+1].coefficients` | Negative row $-a_i$ (or $+a_i$ for reward) | `[-1.0, -0.0]`, `[-1.0, -0.2]`, ... |
| `scenarios[2i+1].offset` | $+b_i$ (or $-b_i$ for reward) | `+4.501`, `+4.360`, ... |
| `shared_constraints` | General linear constraints (none in Chebyshev) | `[]` |
| `options.tolerance` | Feasibility / bound tolerance | `1e-07` |
| `options.binding_tolerance` | Binding scenario threshold | `1e-06` |

---

## 12. Coverage and Non-Coverage

### 12.1 Capabilities and Features Covered
- **Continuous Epigraph Reduction:** Tests the exact epigraph conversion for `scenario.linear.min_max_loss`.
- **Continuous Hypograph Reduction:** Tests the exact hypograph conversion for `scenario.linear.max_min_reward`.
- **Scenario Values Recomputation:** Tests evaluation of $2M$ linear scenario functions at candidate $x^*$.
- **Worst-Case Guarantee:** Confirms that the guaranteed value matches $\max_k v_k(x^*)$ or $\min_k R_k(x^*)$.
- **Binding Set Identification:** Accurately identifies the active equioscillating Chebyshev subsets.
- **Deterministic Scenario Ordering:** Tests ordering preservation across $2M$ scenarios.
- **Independent Validation:** Generates complete, passing `ScenarioIndependentSolutionValidator` reports with status `verified`.
- **Public Surface Parity:** Executes through `create_local_optimization_service()`.

### 12.2 Features Not Covered
- **Integer / MILP Variables:** Chebyshev approximation problems are continuous; they do not test discrete routing.
- **Shared Constraints:** Unconstrained $L_\infty$ fitting has no shared linear constraints (already tested by analytic reference cases).
- **Non-symmetric Scenarios:** Residual doubling produces paired scenarios $(+r_i, -r_i)$, not arbitrary asymmetric scenario distributions.
- **Operational Uncertainty:** Chebyshev regression models geometric approximation error, not stochastic real-world regime shifts.

---

## 13. Numerical Protocol

- **Tolerances:**
  - Optimality and feasibility tolerance: $\varepsilon_{tol} = 10^{-7}$.
  - Absolute objective difference: $|z_{reported} - z_{analytic}| \le 10^{-6}$.
  - Binding scenario tolerance: $\varepsilon_{bind} = 10^{-6}$.
- **Verification Assertions:**
  1. Status must be strictly `optimal`.
  2. Candidate variables $x^*$ must match analytical values within $10^{-6}$.
  3. Reported `guaranteed_value` must match $0.115$ (min-max) and $-0.115$ (max-min) within $10^{-6}$.
  4. Binding set must deterministically equal `['s0_neg', 's2_pos', 's4_neg']`.
  5. `ScenarioIndependentSolutionValidator` must report `verified` with all 10 sub-checks passing.

---

## 14. Temporary Experimental Verification

An experimental validation script was executed in `/tmp/toms495_audit/` outside the repository using Python 3.12 and the Optees environment.

### Experimental Results:
1. **Analytical Reference Derivation:**
   - $x_1^* = 4.386$, $x_2^* = 0.155$, $\text{RESMAX}^* = 0.115$.
   - Equioscillation verified at $t \in \{0.0, 0.4, 0.8\}$.
2. **SciPy HiGHS Direct Solve:**
   - Converged to $z^* = 0.115$, $x^* = [4.386, 0.155]$ in 4 simplex iterations.
3. **Optees `scenario.linear.min_max_loss`:**
   - Status: `optimal`.
   - Guaranteed value: `0.11500000000000021`.
   - Variables: $x_1 = 4.386$, $x_2 = 0.155$.
   - Binding scenarios: `['s0_neg', 's2_pos', 's4_neg']`.
   - Independent validation: `SolutionValidationStatus.VERIFIED`.
   - All 10 validator checks passed (`orientation`, `status_coherence`, `variable_vector`, `scenario_values`, `bounds`, `constraints`, `evaluations`, `guarantee`, `binding_set`, `consistency`).
4. **Optees `scenario.linear.max_min_reward` (Derived):**
   - Status: `optimal`.
   - Guaranteed value: `-0.11500000000000021`.
   - Variables: $x_1 = 4.386$, $x_2 = 0.155$.
   - Binding scenarios: `['s0_neg', 's2_pos', 's4_neg']`.
   - Independent validation: `SolutionValidationStatus.VERIFIED` across all 10 checks.
5. **Runtime and Resources:**
   - Solve time: $< 5$ ms per invocation.
   - Memory allocation: $< 1$ MB.
   - Numerical stability: exact to within $10^{-15}$ machine precision.

---

## 15. Risks and Limitations

1. **Absence of Downloadable Data in Netlib:** The Netlib repository cannot be used as an automated download source for scenario benchmark instances because the archive contains only Fortran code.
2. **Licensing Restriction:** The Fortran source code of Algorithm 495 cannot be redistributed inside the repository due to ACM non-commercial copyright terms.
3. **Scope of Special-Case Mappings:** Chebyshev regression provides valuable cross-domain evidence for LP epigraph/hypograph reductions, but does not represent operational business scenarios with asymmetric payoffs or discrete constraints.

---

## 16. Stop Conditions Audit

| # | Stop Condition | Status | Empirical Evidence |
| :--- | :--- | :--- | :--- |
| 1 | Undetermined or restrictive redistribution license | **TRIGGERED FOR CODE; NOT TRIGGERED FOR PROBLEM SPECIFICATION** | ACM copyright restricts code redistribution to non-commercial use. Mathematical problem definitions and coefficients are uncopyrightable facts. |
| 2 | Stable primary artifact not established | **TRIGGERED AS A BULK DATASET** | Netlib provides a stable Fortran file, but contains **zero benchmark datasets or reference solution files**. |
| 3 | Verifiable published reference results not established | **TRIGGERED FOR NETLIB DOWNLOAD; RESOLVED FOR PUBLISHED INSTANCES** | Netlib archive lacks output tables. The published literature (Barrodale & Phillips 1975) contains verified analytical solutions. |
| 4 | Corpus incompatible with current capability contract | **NOT TRIGGERED** | Chebyshev residual doubling maps algebraically and identically to `scenario.linear.min_max_loss` and `scenario.linear.max_min_reward`. |
| 5 | Need to alter public capability semantics | **NOT TRIGGERED** | Frozen schema v1 and both registered capability IDs are preserved without modification. |
| 6 | Conversion dependent on assumptions absent from data | **NOT TRIGGERED** | Residual doubling ($+r_i, -r_i$) is an exact mathematical identity. No probabilities or unstated assumptions are introduced. |
| 7 | Benchmark tests only LP solver without scenario reconstruction | **NOT TRIGGERED** | Full scenario reconstruction, epigraph/hypograph bounds, binding sets, and independent validation were verified. |
| 8 | Problem dimensions or solve times unsuitable for CI | **NOT TRIGGERED** | Solve time is under 5 ms; problem sizes are compact and well within CI limits. |
| 9 | Inability to verify file integrity via checksums | **RESOLVED** | SHA-256 digests for Netlib 495 (`495.gz` and decompressed `495`) are verified and recorded. |
| 10 | Circular use of Optees to produce expected reference values | **NOT TRIGGERED** | Reference values were derived analytically and checked against HiGHS before evaluating Optees. |

---

## 17. Conclusion: `C — REFERENCE-ONLY`

Among the authorized decisions:
- `A — AUTHORIZED`: Not applicable. Netlib 495 does not provide an automated benchmark dataset with input and solution files.
- `B — CONDITIONALLY AUTHORIZED`: Mathematically valid, but requires external manual extraction of problem instances from journal text rather than automated retrieval from Netlib.
- **`C — REFERENCE-ONLY` (Selected):** The Netlib artifact is a pure algorithmic subroutine without benchmark data or solution files, and its code is governed by ACM non-commercial licensing. However, the mathematical problem formulation is an exact match for Optees linear scenario capabilities, and published test problems (e.g. `BP1975-LINE`) have certified analytical optima. Therefore, these instances are authorized exclusively as **reference cases** to be included directly in reference fixture collections (e.g. `tests/data/scenario/reference_cases.json`), rather than as an external downloadable benchmark suite.
- `D — REJECTED`: Inaccurate. The mathematical formulation is sound, exact, and experimentally verified.
- `E — INCONCLUSIVE`: Inaccurate. The artifact and its legal/technical properties were thoroughly and conclusively audited.

---

## 18. Planned Files for Future Work Unit

When incorporating literature-backed Chebyshev cases into reference suites:
- `tests/data/scenario/reference_cases.json`: Add `BP1975-LINE` (and optionally `BP1975-QUAD`) with source citation, analytical rational optimum, and binding set.
- `tests/data/scenario/test_scenario_reference_cases.py`: The existing parameterized test suite automatically covers added reference cases without new test machinery.

---

## 19. Completion Gate

- **Gate Status:** `ROBUST-BENCH-AUDIT-495` achieved.
- **Audit Findings:**
  - Netlib 495 audited at the byte level with verified SHA-256 digests.
  - License terms audited: ACM non-commercial software policy prevents Fortran code redistribution.
  - Structure audited: No input data or solution files in the Netlib archive.
  - Mathematical mapping formalised and proven exact for both min-max loss and derived max-min reward.
  - Experimental verification confirmed 100% pass rate on independent validation.
  - Conclusion `C — REFERENCE-ONLY` frozen.

---

## 20. Next Authorized Step

- **State:** `OPT-DS-ROBUST-BENCH-A` is complete.
- **Roadmaps:** Update `scientific-linear-scenario-benchmark.md`, `ROADMAP.md`, and `datasets.md` to reflect Conclusion `C — REFERENCE-ONLY`.
- **Immediate Project Priority:** Return to the case study evidence sequence (`OPT-DS-04` forecasting evidence protocol and baseline Decision Simulator experiments) or evaluate Candidate 3 (matrix games) if further scenario reference work is scheduled.
