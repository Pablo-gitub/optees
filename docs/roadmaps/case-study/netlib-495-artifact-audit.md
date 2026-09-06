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
  - The follow-up NAG audit is complete in `nag-e02gcc-example-audit.md`. It
    corrected the example to its actual three-basis-function model and rejected
    it as a repository fixture source because suitable redistribution permission
    was not established.

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
   - The decompressed file contains 298 text lines, uses LF line endings, ends with a trailing newline, and is 8,872 bytes.
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
2. **Policy Evidence Located:**
   - The CALGO policy grants copying and distribution without fee only when copies are not made or distributed for direct commercial advantage and when its attribution and notice conditions are preserved.
   - Those restrictions do not provide the unrestricted downstream use expected for content vendored in this Apache-2.0 project.
3. **Repository Decision (not legal advice):**
   - Optees will not vendor or derive code from `toms/495` without separate compatible permission. This audit does not claim a definitive legal interpretation beyond that conservative repository rule.
4. **Problem-Data Boundary:**
   - The Netlib artifact contains no problem coefficients. Whether coefficients transcribed from an ACM article or NAG manual may be redistributed is source- and jurisdiction-dependent; this audit does not authorize that action merely by characterizing numbers as facts. Independently created analytic examples remain possible, but must not be represented as published benchmark cases.

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
| `NAG-E02GCC-CANDIDATE` | NAG `e02gcc` documentation | $5 \times 3$ | Fit $y(t)=K e^t+L e^{-t}+M$ to five displayed points. | Audited and rejected for fixture inclusion; see `nag-e02gcc-example-audit.md`. |

The earlier draft attributed additional quadratic and exponential examples to specific sections or tables of the 1975 article without recording inspected primary evidence. Those claims are withdrawn. The ACM paper itself was not acquired as part of this byte-level Netlib audit.

---

## 8. Available Reference Outputs

Netlib 495 bundles no numerical reference outputs. The earlier audit draft
mistakenly treated NAG observations as a two-variable straight-line example;
that derived problem is removed because it is neither a Netlib nor a NAG case.
The correct three-variable NAG example and its rounded published output are
recorded only in the separate source-specific audit.

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

The mapping into the Optees public linear-scenario problem schema v1 and domain `ScenarioModel` is deterministic and complete:

| Optees Problem Field | Source / Transformation | Generic Chebyshev value |
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

A future authorized Chebyshev case must freeze its source precision and derive
appropriate tolerances from that evidence. It must require `optimal`, compare
the decision vector and guarantee with an independent oracle, check every
scenario evaluation and ordered binding set, and require a strict `verified`
report from `ScenarioIndependentSolutionValidator`.

---

## 14. Temporary Experimental Verification

The original Netlib audit contained an experiment for an incorrectly inferred
straight-line problem. That evidence is withdrawn. The subsequent NAG audit
reconstructed the actual three-function example and independently exercised
both registered Optees capabilities; its results are recorded in
`nag-e02gcc-example-audit.md` and did not create a permanent fixture.

---

## 15. Risks and Limitations

1. **Absence of Downloadable Data in Netlib:** The Netlib repository cannot be used as an automated download source for scenario benchmark instances because the archive contains only Fortran code.
2. **Licensing Restriction:** Optees conservatively excludes the Fortran source from its Apache-2.0 distribution because CALGO terms contain non-commercial conditions.
3. **Scope of Special-Case Mappings:** Chebyshev regression provides valuable cross-domain evidence for LP epigraph/hypograph reductions, but does not represent operational business scenarios with asymmetric payoffs or discrete constraints.

---

## 16. Stop Conditions Audit

| # | Stop Condition | Status | Empirical Evidence |
| :--- | :--- | :--- | :--- |
| 1 | Undetermined or restrictive redistribution license | **TRIGGERED FOR CODE AND UNRESOLVED FOR EXTERNAL EXAMPLE DATA** | CALGO applies non-commercial conditions to algorithm distribution. The exact terms governing coefficients displayed in the NAG manual or ACM article were not frozen, so this audit does not authorize their redistribution. |
| 2 | Stable primary artifact not established | **TRIGGERED AS A BULK DATASET** | Netlib provides a stable Fortran file, but contains **zero benchmark datasets or reference solution files**. |
| 3 | Verifiable published reference results not established | **TRIGGERED FOR NETLIB** | Netlib contains no cases or outputs. The separate NAG candidate was audited and rejected for fixture inclusion. |
| 4 | Corpus incompatible with current capability contract | **NOT TRIGGERED** | Chebyshev residual doubling maps algebraically and identically to `scenario.linear.min_max_loss` and `scenario.linear.max_min_reward`. |
| 5 | Need to alter public capability semantics | **NOT TRIGGERED** | Frozen schema v1 and both registered capability IDs are preserved without modification. |
| 6 | Conversion dependent on assumptions absent from data | **NOT TRIGGERED** | Residual doubling ($+r_i, -r_i$) is an exact mathematical identity. No probabilities or unstated assumptions are introduced. |
| 7 | Benchmark tests only LP solver without scenario reconstruction | **IMPLEMENTATION CONDITION** | Any later authorized case must traverse the public scenario capability and verify reconstruction; Netlib supplies no executable benchmark case. |
| 8 | Problem dimensions or solve times unsuitable for CI | **UNRESOLVED FOR A FUTURE CORPUS** | Netlib supplies no instance set to measure. The separately audited NAG example is small but rejected as a fixture source. |
| 9 | Inability to verify file integrity via checksums | **RESOLVED** | SHA-256 digests for Netlib 495 (`495.gz` and decompressed `495`) are verified and recorded. |
| 10 | Circular use of Optees to produce expected reference values | **IMPLEMENTATION CONDITION** | A future oracle must be published or independently derived before Optees execution. The corrected NAG audit followed that order but did not authorize persistence. |

---

## 17. Conclusion: `C — REFERENCE-ONLY`

Among the authorized decisions:
- `A — AUTHORIZED`: Not applicable. Netlib 495 does not provide an automated benchmark dataset with input and solution files.
- `B — CONDITIONALLY AUTHORIZED`: Mathematically valid, but requires external manual extraction of problem instances from journal text rather than automated retrieval from Netlib.
- **`C — REFERENCE-ONLY` (Selected):** Netlib 495 is useful as a primary
  algorithm and formulation reference, not as a benchmark corpus. The subsequent
  NAG audit rejected its five-point example as a fixture source and corrected
  the earlier two-variable misinterpretation.
- `D — REJECTED`: Inaccurate. The mathematical formulation is sound, exact, and experimentally verified.
- `E — INCONCLUSIVE`: Inaccurate. The artifact and its legal/technical properties were thoroughly and conclusively audited.

---

## 18. Planned Files for Future Work Unit

If a different source-specific audit authorizes a literature-backed Chebyshev case:
- `tests/data/scenario/reference_cases.json`: Add only the audited case with its exact source citation, source terms, independently verified optimum, and binding set.
- `tests/data/scenario/test_scenario_reference_cases.py`: The existing parameterized test suite automatically covers added reference cases without new test machinery.

---

## 19. Completion Gate

- **Gate Status:** `ROBUST-BENCH-AUDIT-495` achieved.
- **Audit Findings:**
  - Netlib 495 audited at the byte level with verified SHA-256 digests.
  - CALGO policy reviewed; conservative repository policy prevents vendoring the Fortran code under Optees' Apache-2.0 distribution.
  - Structure audited: No input data or solution files in the Netlib archive.
  - Mathematical mapping formalised and proven exact for both min-max loss and derived max-min reward.
  - Experimental verification confirmed 100% pass rate on independent validation.
  - Conclusion `C — REFERENCE-ONLY` frozen for the Netlib artifact; the NAG
    candidate was subsequently rejected for fixture inclusion.

---

## 20. Next Authorized Step

- **State:** `OPT-DS-ROBUST-BENCH-A` is complete.
- **Roadmaps:** Update `scientific-linear-scenario-benchmark.md`, `ROADMAP.md`, and `datasets.md` to reflect Conclusion `C — REFERENCE-ONLY`.
- **Immediate Project Priority:** Return to the case study evidence sequence (`OPT-DS-04` forecasting evidence protocol and baseline Decision Simulator experiments) or evaluate Candidate 3 (matrix games) if further scenario reference work is scheduled.
