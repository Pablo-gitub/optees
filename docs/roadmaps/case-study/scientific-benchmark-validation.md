# Scientific Benchmark Validation of Continuous Convex QP

## Document Status

- **Work Unit:** `OPT-DS-QP-BENCH`
- **Capability ID:** `qp.continuous`
- **State:** completed
- **Parent roadmaps:** `docs/roadmaps/case-study/ROADMAP.md` and `docs/roadmaps/project.md`
- **Contract reference:** `docs/contracts/quadratic-programming-contract.md`
- **Prerequisites:** `QP-I` and `QP-UI` completed; `OPT-DS-QP-H` handoff completed

## Objective

Provide reproducible, scientifically grounded benchmark evidence for the `qp.continuous`
capability in Optees using a verified, dimensionally compatible subset of the historical
convex Quadratic Programming collection of István Maros and Csaba Mészáros (1999).

This validation hardens the scientific credibility of the Optees QP implementation against
standard peer-reviewed literature benchmarks while strictly adhering to:
- existing public JSON schema v1 (`ContinuousConvexQPProblem` / `schema_version: "1"`);
- production solver execution via `create_local_optimization_service()`;
- independent post-solve solution validation (`QPIndependentSolutionValidator`);
- zero network activity during regular pytest runs or module imports;
- clean offline isolation and strict path-traversal protection for downloaded datasets.

This work unit is independent of `optees-decision-simulator` and does not introduce
MIQP, forecasting, workflow registries, new public contracts, or UI modifications.

---

## 1. Scientific Context and Primary Provenance

### 1.1 Peer-Reviewed Literature Foundation

The benchmark suite originates from the canonical publication:

> István Maros and Csaba Mészáros,
> *"A repository of convex quadratic programming problems"*,
> **Optimization Methods and Software**, Vol. 11 & 12 (1999), pp. 671–681.
> DOI: 10.1080/10556789908805769.

The authors compiled 138 challenging convex quadratic programs from diverse sources:
- **CUTE library** (76 problems): constrained and unconstrained test problems contributed by
  Ingrid Bongartz, Andy Conn, Nick Gould, and Philippe Toint;
- **Brunel Optimization Group** (46 problems): applied optimization models contributed by
  Helen Jones and Gautam Mitra;
- **Miscellaneous contributors** (16 problems): including contributions from Piet Groeneboom
  (University of Washington), Hans D. Mittelmann (Arizona State University), Athanassia
  Chalimourda (Ruhr University), Don Boyd (Rensselaer Polytechnic Institute), James McNames
  (Stanford University), and Henry Wolkowitz (University of Waterloo).

### 1.2 Mathematical Formulation Convention

In the Maros–Mészáros repository, problems are posed as:

$$\operatorname{minimize}_{x \in \mathbb{R}^n} \quad f(x) = c_0 + c^T x + \frac{1}{2} x^T Q x$$
$$\text{subject to} \quad A x = b, \quad l \le x \le u$$

where $Q \in \mathbb{R}^{n \times n}$ is symmetric positive semidefinite ($Q \succeq 0$).
General linear inequalities ($\le$ and $\ge$) and range constraints are expressed via standard
MPS/QPS row senses and slack transformations.

**Key Mathematical Alignment:**
The objective function in the Maros–Mészáros repository uses the identical explicit
$\frac{1}{2}$ factor in front of the quadratic Hessian $Q$ as frozen in Optees
`docs/contracts/quadratic-programming-contract.md`:
$$f(x) = \frac{1}{2} x^T Q x + c^T x + \alpha$$
In QPS files, the quadratic section (`QUADOBJ` or `QSECTION`) specifies entries of $Q$
(where off-diagonal elements define $Q_{ij} = Q_{ji}$). When an objective offset $c_0$ is
present in the QPS file, it appears as an entry in the `RHS` section for the objective row
(with $c_0 = -\text{RHS}[\text{obj\_row}]$).

### 1.3 Distribution Sources and Checksum Integrity

The primary authoritative source is István Maros's department page at Imperial College London:
- URL: `http://www.doc.ic.ac.uk/~im/`
- Documentation: `http://www.doc.ic.ac.uk/~im/00README.QP`
- Archive 1 (CUTE problems): `http://www.doc.ic.ac.uk/~im/QPDATA1.ZIP`
- Archive 2 (Brunel problems): `http://www.doc.ic.ac.uk/~im/QPDATA2.ZIP`
- Archive 3 (Miscellaneous): `http://www.doc.ic.ac.uk/~im/QPDATA3.ZIP`

The raw files and archives possess the following immutable SHA-256 digests:

| File | Content | Bytes | SHA-256 Digest |
| --- | --- | --- | --- |
| `00README.QP` | Author problem catalog and reference optima | 14,354 | `cde81a616bbcb6379190ce845295be034c6676ca247e4484d5d8b7ead0daf4ce` |
| `QPDATA1.ZIP` | 76 CUTE QP instances (.qps) | 7,569,247 | `1a851ba04d002c1e623367dd78a4c7d71730fc58f1296e7f83afa41e412b2323` |
| `QPDATA2.ZIP` | 46 Brunel QP instances (.qps) | 1,838,823 | `8e96a76e3fcdac1999626926f3fa629fa7476b01a51b8d6cd312cc539e79994f` |
| `QPDATA3.ZIP` | 16 miscellaneous QP instances (.qps) | 18,827,023 | `bc60bb823783ba10301ad48e4e8cca4d4af2a743ea739551ecb1c0ce40e21ed5` |

Secondary community mirrors (e.g., `https://github.com/optimizers/maros-meszaros-mirror`
and CUTEst/Netlib distributions) mirror these identical problem definitions.

---

## 2. Stop Conditions Audit

Prior to implementation, all six mandatory stop conditions were evaluated against empirical
evidence:

| # | Stop Condition | Status | Empirical Evidence |
| --- | --- | --- | --- |
| 1 | Incompatible / unclear redistribution terms under Apache-2.0 | **PASS FOR EXTERNAL ACQUISITION** | The collection is publicly distributed by its author, but this work does not infer or claim an Apache-compatible redistribution licence. No corpus bytes are committed or packaged: users and CI acquire the checksummed files from the author's host into an external cache. Redistribution remains explicitly unapproved. |
| 2 | Inability to obtain stable, verifiable SHA-256 checksums from an authoritative source | **PASS** | Checksums verified against primary Imperial College London host and recorded in this specification. |
| 3 | QPS format requires semantics not representable without loss in `qp.continuous` v1 | **PASS** | Continuous variables, lower/upper bounds, linear equalities/inequalities, range constraints, symmetric PSD Hessians, linear costs, and constant offsets map 100% losslessly into public schema v1. |
| 4 | Need to modify public schema v1, solver adapter, UI, REST, MCP, or mathematical semantics | **PASS** | Solver, schemas, capability registration, and delivery surfaces remain completely unmodified. |
| 5 | Lack of reliable published reference optima in original scientific literature | **PASS** | Exact reference optima for all instances are documented in `00README.QP` and Maros & Mészáros (1999) using BPMPD. |
| 6 | Selected instances violate v1 dimension limits ($n \le 500$, $m \le 1000$) or convexity | **PASS** | 57 instances satisfy $n \le 500, m \le 1000$; 14 strictly convex/PSD instances have been selected and tested. |

**Conclusion:** Zero stop conditions are triggered. Implementation is fully authorized.

---

## 3. Selected Instances Matrix

Fourteen representative instances were selected across size scales, structural forms,
and difficulty characteristics:

| Instance | Archive | M (rows) | N (vars) | NZ (nonzeros) | QN | QNZ | Published Optimum (BPMPD) | Characteristics & Structure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `HS21` | QPDATA1 | 1 | 2 | 2 | 2 | 0 | `-9.9960000e+01` | Strictly convex diagonal Hessian, box bounds, linear inequality, objective offset ($c_0 = -100$). |
| `QPTEST` | QPDATA3 | 2 | 2 | 4 | 2 | 1 | `4.3718750e+00` | Tutorial 2D problem from section 2 of Maros & Mészáros (1999); non-diagonal Hessian. |
| `TAME` | QPDATA1 | 1 | 2 | 2 | 2 | 1 | `0.0000000e+00` | Positive semidefinite rank-1 Hessian matrix ($Q_{11}=1, Q_{22}=1, Q_{12}=-1$), optimum at origin. |
| `ZECEVIC2` | QPDATA1 | 2 | 2 | 4 | 1 | 0 | `-4.1250000e+00` | Mixed linear-quadratic objective ($x_1^2$ quadratic, $x_2$ purely linear), 2 linear constraints. |
| `HS35` | QPDATA1 | 1 | 3 | 3 | 3 | 2 | `1.1111111e-01` | Hock–Schittkowski 35; coupled off-diagonal Hessian, active linear inequality, offset ($c_0 = 9$). |
| `HS76` | QPDATA1 | 3 | 4 | 10 | 4 | 2 | `-4.6818182e+00` | Hock–Schittkowski 76; 4 variables, 3 linear inequalities, coupled quadratic terms. |
| `HS51` | QPDATA1 | 3 | 5 | 7 | 5 | 2 | `0.0000000e+00` | Hock–Schittkowski 51; 5 free variables, 3 linear equality constraints, offset ($c_0 = 6$). |
| `HS52` | QPDATA1 | 3 | 5 | 7 | 5 | 2 | `5.3266476e+00` | Hock–Schittkowski 52; 5 free variables, 3 linear equality constraints, offset ($c_0 = 6$). |
| `GENHS28` | QPDATA1 | 8 | 10 | 24 | 10 | 9 | `9.2717369e-01` | Generalized HS28; tridiagonal quadratic Hessian, 8 linear equality constraints. |
| `LOTSCHD` | QPDATA1 | 7 | 12 | 54 | 6 | 0 | `2.3984159e+03` | Lot-scheduling problem; positive semidefinite Hessian with 6 zero-diagonal variables. |
| `HS118` | QPDATA1 | 17 | 15 | 39 | 15 | 0 | `6.6482045e+02` | Hock–Schittkowski 118; 15 variables, 17 linear constraints, box bounds. |
| `QAFIRO` | QPDATA2 | 27 | 32 | 83 | 3 | 3 | `-1.5907818e+00` | Netlib AFIRO with quadratic objective on 3 variables; dense linear constraint structure. |
| `CVXQP2_S` | QPDATA1 | 25 | 100 | 74 | 100 | 286 | `8.1209405e+03` | Small CUTEst CVXQP2; 100 variables, 25 constraints, 286 quadratic coupling terms. |
| `CVXQP3_S` | QPDATA1 | 75 | 100 | 222 | 100 | 286 | `1.1943432e+04` | Small CUTEst CVXQP3; 100 variables, 75 constraints, 286 quadratic coupling terms. |

---

## 4. Architectural Boundary and QPS Adapter Design

### 4.1 Component Placement

The QPS adapter is placed strictly inside the utility data-adapters boundary:
- Path: `src/optees/utility/data_adapters/qps_adapter.py`
- Co-located with existing domain-neutral benchmark loaders: `lpnetlib_adapter.py`, `orlib_mknap_adapter.py`, `miplib_solu.py`.
- **Isolation Guarantee**: The adapter is NOT exposed as a public API or CLI entrypoint. It exists exclusively to translate benchmark files into `ContinuousConvexQPProblem` dictionaries for solver evaluation and testing.

### 4.2 Adapter Capabilities and Robustness

1. **Format Compliance**:
   - Parses the legacy indented QPS records used by the selected corpus (`NAME`, `ROWS`, `COLUMNS`, `RHS`, `RANGES`, `BOUNDS`, `QUADOBJ`, `QSECTION`, `ENDATA`). It does not claim general free-format MPS/QPS compatibility.
   - Accepts both CRLF (`\r\n`) and LF (`\n`) line terminators.
   - Ignores comment lines (`*`) and empty whitespace lines.
2. **Mathematical Faithful Mapping**:
   - `ROWS`: Handles `N` (objective row), `E` ($=$), `L` ($\le$), `G` ($\ge$).
   - `COLUMNS`: Binds linear cost coefficients $c$ and constraint matrix entries $A_{ij}$ to ordered variables.
   - `RHS`: Extracts constraint right-hand sides $b_i$. If the objective row appears in `RHS`, extracts $c_0 = -\text{RHS}[\text{obj\_row}]$ as the objective `offset`.
   - `RANGES`: Translates two-sided range constraints $[b_{min}, b_{max}]$ into paired $\ge$ and $\le$ linear constraints.
   - `BOUNDS`: Implements `LO`, `UP`, `FX`, `FR`, `MI`, `PL`, with standard MPS default $0 \le x_j < +\infty$ when bounds are omitted.
   - `QUADOBJ` / `QSECTION`: Symmetrizes entries without duplicate doubling, directly matching the Hessian matrix $Q = \nabla^2 f(x)$ in $\frac{1}{2} x^T Q x$.
3. **Fail-Closed Principle**:
   - Rejects integer/discrete variable markers (e.g. `MARKER 'INTORG'`) with `ValueError("Discrete variables are not supported by continuous QP adapter")`.
   - Rejects non-finite values (`NaN`, `Inf`).
   - Rejects unsupported sections.

---

## 5. Acquisition and Caching Strategy

To ensure zero network requests during normal automated testing, acquisition is isolated
in a dedicated script:

- Path: `scripts/fetch_maros_meszaros_benchmark.py`
- Target directory: `~/.cache/optees/benchmarks/maros_meszaros/` (outside the Git repository).
- Security controls:
  - 30-second socket timeout;
  - Per-download compressed-size limits, a 175 MB uncompressed-archive limit, and a 5 MB selected-instance limit;
  - SHA-256 verification of every archive and every selected instance before atomic extraction;
  - Path traversal protection: rejects archive members with leading slashes, `..`, or symlinks;
  - `--check-only` mode to audit cache integrity without downloading.

---

## 6. Numerical Comparison Rules and Tolerances

When comparing Optees OSQP solutions against the published BPMPD reference values:

1. **Algorithm Discrepancy**:
   BPMPD is an interior-point method with high convergence precision on primal-dual barriers;
   OSQP is an operator-splitting first-order ADMM method. Small differences on the order of
   $10^{-6}$ to $10^{-4}$ in objective values are expected and scientifically standard across
   solver literature.
2. **Assertion Criteria**:
   - Status check: `mathematical_status == "optimal"`;
   - Objective match: `pytest.approx(expected, rel=1e-4, abs=1e-4)`;
   - Feasibility checks: Primal candidate satisfies declared bounds and linear constraints within $10^{-7}$;
   - Validation report: `QPIndependentSolutionValidator` must return `verified`; every case must pass the independent KKT-stationarity check in addition to variable, bound, constraint, and objective checks.

---

## 7. Testing Strategy

1. **Unit tests (`tests/utility/test_qps_adapter.py`)**:
   - Tested in default fast test suite (`not benchmark and not gui and not tcp`).
   - Covers synthetic QPS strings with CRLF, ranges, bounds, offsets, symmetry, repeated-record summation, zero-coefficient constraints, resource limits, and fail-closed structural rejections.
   - `tests/utility/test_maros_meszaros_acquisition.py` verifies selected-file hashes, atomic repair, duplicate-name rejection, and archive traversal protection without network access.
2. **Benchmark integration tests (`tests/utility/test_qp_maros_meszaros_benchmark.py`)**:
   - Marked with `@pytest.mark.benchmark`.
   - Resolves files from `~/.cache/optees/benchmarks/maros_meszaros/`.
   - A direct local invocation skips cleanly if the cache is unpopulated and prints the acquisition command. Scheduled CI and tagged-release gates run acquisition plus `--check-only` before pytest, so those authoritative gates cannot pass merely by skipping an absent corpus.
   - Solves all 14 instances through `create_local_optimization_service().solve("qp.continuous", payload)`.
   - Rechecks each selected instance SHA-256, parsed dimensions, published objective, strict `verified` validation status, and passing KKT stationarity.
3. **Packaging & Regressions**:
   - No modifications to existing reference cases in `tests/data/qp/reference_cases.json`.
   - Existing QP regression suites remain unchanged; the repository gates recorded for this work unit are the source of current pass counts.

---

## 8. Non-Goals and Explicit Exclusions

- No QPLIB integration.
- No MIQP or mixed-integer quadratic extensions.
- No modifications to public schemas, REST API, CLI, MCP, or UI.
- No automatic network downloads during `pytest` or module imports.
- No committing external multi-megabyte archives into Git.
