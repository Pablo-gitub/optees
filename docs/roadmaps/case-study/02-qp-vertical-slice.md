# Convex QP Vertical Slice Plan

## Work Unit

- **ID:** `OPT-DS-02`
- **State:** ready
- **Type:** production capability with separately owned UI completion
- **Parent roadmap:** `ROADMAP.md`
- **Frozen contract:** `../../contracts/quadratic-programming-contract.md`
- **Prerequisite:** `QP-C` satisfied by `OPT-DS-01`
- **Consumer:** Decision Simulator phase `DS-04`
- **Integration gate:** `QP-I`
- **UI completion gate:** `QP-UI`

## Objective

Deliver `qp.continuous` as a domain-neutral, independently validated Optees
capability through the shared application core and public CLI, REST, and MCP
surfaces. Publish frozen fixtures at `QP-I` so the Decision Simulator can
integrate against real behavior. After that gate, add the educational PySide6
workflow and QP visual language without moving mathematical authority into the
presentation layer.

This work unit has two owners and two atomic implementation stages:

1. **Capability stage — Gemini:** domain, application, OSQP adapter, codecs,
   validation, registry, transports, fixtures, non-visual documentation,
   dependency and packaging evidence. Stop at `QP-I` for review.
2. **UI stage — Claude:** desktop workflow, bilingual UI, educational content,
   accessible result presentation and bounded visualizations. Start only after
   `QP-I` has been reviewed. Stop at `QP-UI` for review.

Codex reviews each stage independently. Material review corrections belong in
a separate atomic commit. The Decision Simulator may consume `QP-I`; it does
not wait for `QP-UI`.

## Frozen Boundary

Implementation must conform to the version 1 contract without silently
changing:

- capability ID `qp.continuous` and contract/problem/result version `1`;
- objective convention `1/2 x^T Q x + c^T x + alpha`;
- continuous convex minimization and concave maximization boundary;
- ordered dense variables, matrix/vector binding, relations, and null bounds;
- symmetry and curvature tolerances and detail codes;
- public job, mathematical, termination, and validation dimensions;
- OSQP as the sole v1 method token;
- advertised size, iteration, tolerance, time-limit, and cancellation limits.

If production evidence contradicts the frozen contract, stop and propose a
contract correction before adapting the code. Do not hide incompatibility with
a codec-only special case, silent matrix projection, solver fallback, or
overstated status.

## Stage A — Capability Implementation (Gemini)

### A1. Dependency and backend acceptance

- Probe OSQP using the supported Python versions and a minimal analytic QP.
- Pin a bounded OSQP dependency only after verifying import, solve, status,
  dual, iteration, time-limit, and warm-start behavior used by v1.
- Record the actual OSQP version in execution diagnostics; never treat a
  backend string as proof of reproducibility.
- Verify the dependency is importable from an installed wheel and include it
  in the existing PyInstaller analysis/spec flow before claiming packaging
  support.
- Keep Clarabel and SciPy out of runtime fallback logic. They remain documented
  evaluation alternatives only.
- Keep `supports_cancellation: false` unless an isolated, tested cancellation
  mechanism is implemented in a later contract version.

Stop if supported Python wheels, license, native loading, status evidence, or
release-target packaging cannot meet the existing Optees standard.

### A2. Domain model

Add a dedicated QP domain package following existing LP/MILP conventions where
they fit, without making QP inherit transport DTOs or mutating LP/MILP types.
Model at least:

- ordered continuous variables and bounds;
- quadratic objective, sense, matrix, linear vector, and offset;
- named linear constraints and relations;
- solver options represented without OSQP-specific objects;
- solution values, objective, dual data when available, status, and numerical
  diagnostics.

Domain construction must reject duplicate names, non-finite numbers,
dimension mismatches, invalid bounds, malformed matrices, unsupported method
tokens, asymmetry beyond tolerance, and invalid convexity/concavity. Accepted
near-symmetric matrices may be canonicalized exactly as frozen; accepted
near-PSD matrices must not be projected or have eigenvalues clamped.

### A3. Application port and use case

- Add a `QPSolverPort` owned by the application layer.
- Add a QP solve use case that accepts domain types and returns domain results.
- Keep solver selection and concrete adapter wiring in the composition root.
- Do not call OSQP from codecs, validators, transports, or presentation code.
- Preserve distinct validation errors, dependency failures, solver
  termination, and internal failures rather than collapsing them into one
  exception or status.

### A4. OSQP adapter and status mapping

Translate the frozen problem to OSQP's sparse form without changing variable
order or objective semantics. Build linear constraints and bounds explicitly,
including equality, `<=`, `>=`, and unbounded sides. For maximization, apply
the frozen sign transformation and map objective and dual information back
consistently.

Create an explicit, exhaustively tested mapping for every OSQP status observed
or documented by the pinned version. In particular:

- do not report `optimal` for an inaccurate, interrupted, iteration-limited,
  or time-limited candidate unless the public contract and independent
  evidence justify that exact claim;
- distinguish primal infeasibility from dual infeasibility/unboundedness;
- retain a finite candidate only when OSQP returned one and it passes the
  applicable independent checks;
- return `not_solved` for dependency/internal/numerical conditions that do not
  establish a mathematical conclusion;
- expose iterations, runtime, residuals, backend status, and applied limits as
  bounded diagnostics without leaking implementation objects.

Warm start may be implemented only as an explicit application option covered
by deterministic tests. It must not create hidden state across unrelated jobs.

### A5. Public codecs and descriptor

- Add the QP capability ID once in the canonical capability-ID module.
- Implement strict problem and result codecs matching the frozen examples and
  rejecting unknown or malformed values according to existing public-contract
  policy.
- Register the problem schema, result schema, defaults, limits, method token,
  status semantics, validation support, and cancellation claim in the shared
  capability descriptor.
- Register the codec, use case, adapter, and validator in the existing
  composition root rather than adding transport-specific dispatch.
- Preserve numeric finiteness and JSON compatibility at every boundary.

### A6. Independent validation

Implement `QPIndependentSolutionValidator` independently of OSQP's success
flag. It must recompute from the original accepted problem:

- variable identity, ordering, cardinality, and finiteness;
- lower/upper-bound feasibility;
- equality and inequality feasibility;
- original-sense objective including the offset;
- stationarity and complementary slackness when the required duals exist and
  their sign convention has been verified.

Report each check using the frozen detail codes and tolerances. Missing duals
must produce an honest partial/not-available claim rather than a fabricated
KKT verification. `verified` requires every check promised by that status;
infeasibility and unboundedness certificates must not be claimed as
independently verified unless the implementation actually validates them.

### A7. Shared delivery surfaces

Exercise the capability through the generic job service and verify:

- discovery exposes one coherent descriptor;
- validation rejects invalid/asymmetric/non-convex payloads before job
  submission;
- CLI returns only the public JSON envelope on stdout;
- authenticated loopback REST has descriptor, validation, submission, polling,
  and result parity;
- MCP enforces discovery and validation and returns the same normalized result;
- missing OSQP becomes a stable dependency failure and does not prevent other
  capabilities from being discovered or used.

Do not create QP-specific business logic inside CLI, HTTP, or MCP adapters.

### A8. Frozen fixtures and integration evidence

Publish versioned, deterministic problem/result/validation fixtures for:

- unconstrained interior optimum;
- constrained boundary optimum;
- concave maximization;
- equality plus inequality and finite/unbounded box sides;
- infeasible problem;
- unbounded problem;
- iteration or time limit with honest candidate semantics where reproducible;
- asymmetric, non-convex/non-concave, dimension-invalid, and non-finite input;
- tampered variable, objective, bound, constraint, and dual result.

Every successful fixture must retain capability/contract/schema versions,
backend/version diagnostics, normalized result, and validation report. Record
fixture SHA-256 hashes for the Decision Simulator parity gate. Do not call a
machine-generated result a universal golden solution when solver tolerances
permit multiple valid solutions.

### A9. Non-visual documentation and packaging evidence

- Update the frozen contract only if an explicitly reviewed correction is
  required; otherwise mark implementation status without rewriting semantics.
- Add or update domain-neutral QP reference documentation and public JSON
  examples.
- Update architecture, testing, capability, and packaging/release documentation
  where shipped behavior changes.
- Verify wheel installation and public CLI acceptance in an isolated
  environment.
- Run existing packaging smoke/static analysis relevant to dependency
  collection. If all three native release artifacts cannot be built locally,
  state the unverified targets and leave final release packaging open.

### Stage A explicit exclusions

- PySide6 views, controllers, navigation, dialogs, widgets, and screenshots;
- UI strings, visual hierarchy, contour charts, or educational graphics;
- simulator/trading formulations;
- sparse public schema v2, non-convex QP, MIQP, CVaR, robust scenarios;
- automatic fallback to another optimizer;
- unsafe thread/process cancellation claims;
- unrelated LP/MILP refactoring.

## Gate `QP-I` (Achieved)

Stage A capability implementation is complete:

- domain and application layers are domain-neutral and strictly decoupled from solver/OSQP packages;
- OSQP (`0.6.7.post3`) backend adapter registered as `osqp.direct` for `qp.continuous`;
- public DTO codecs, JSON I/O, capability descriptor match contract version 1;
- independent validation (`QPIndependentSolutionValidator`) verifies variable vector, bounds, linear constraints, objective value, and KKT stationarity / dual feasibility when duals are present;
- CLI (`optees solve qp.continuous`), REST (`/api/v1/jobs`, `/api/v1/problems/validate`), and MCP (`optees_create_job`, `optees_validate_problem`) surfaces pass parity tests;
- frozen simulator fixtures and reference cases published with SHA-256 hashes:
  - `tests/data/qp/reference_cases.json`:
    `a9e133c0064feb7ebf266ff019909bd8dde850a01a1f7612aa0eb123c6cdf805`;
  - `examples/qp_resource_allocation_2variables.json`: domain-neutral v1
    example, SHA-256
    `52f649d98aa5d60071c6d9c578b97c7dd597cc89065fa74b3392fcc2b6a3b476`;
- non-GUI regression, focused GUI regression, documentation links, editable
  installation, and the checks recorded below passed. Native release artifacts
  remain subject to the repository release gate; an editable install is not a
  wheel-installation acceptance test.

After `QP-I`, stop. Stage B (Desktop UI and Visual Design) is owned by Claude.

## Stage B — Desktop UI and Visual Design (Claude)

Start only after `QP-I` review confirms that the application use case and
public result semantics are stable.

Claude owns only the human-facing QP experience:

- navigation entry and a reusable PySide6 QP feature module;
- formulation view for ordered variables, bounds, `Q`, `c`, offset, sense,
  constraints, and solver options;
- import/export interaction through the existing codecs;
- explicit inline validation and safe handling of large matrices;
- result view separating mathematical status, termination, validation,
  objective, variables, residuals, dual availability, and limitations;
- a bounded two-variable contour/feasible-region visualization when its
  preconditions hold, with a clear alternative for higher dimensions;
- English and Italian strings kept semantically equivalent;
- educational problem/example pages and accessible explanations of the
  one-half convention, convexity, feasible versus optimal, and validation;
- keyboard navigation, focus/error behavior, readable contrast, resize
  behavior, empty/loading/failure states, and visual regression evidence where
  practical.

Views and view models/controllers must call the Stage A application API. They
must not import OSQP, recompute the authoritative solution, alter constraints,
invent a success status, or weaken validation. If a necessary application DTO
is missing, Claude must document the smallest requested backend change and
stop rather than implement solver/application logic.

### Stage B verification

- focused view/controller tests for valid, invalid, infeasible, unbounded,
  partial-validation, dependency-failure, and high-dimensional results;
- import/manual-entry parity through the same application use case;
- bilingual key parity and absence of hardcoded translatable text;
- GUI navigation and information-page tests;
- headless/offscreen test execution where supported;
- manual visual review at representative sizes, with inaccessible GUI
  environments reported honestly;
- regression run for existing LP/MILP/NLP navigation and shared widgets.

## Gate `QP-UI` (Implemented, pending review)

Stage B desktop implementation is complete:

- Home card in the Nonlinear Programming category and a toolbar
  "Nonlinear Optimization" group holding NLP and QP; `qp`, `qp_example`,
  `qp_problem`, and `qp_solution` pages registered in `MainWindow`;
- `QPView` formulates ordered variables and bounds, the objective sense,
  offset, a symmetry-preserving `Q` editor, the linear vector `c`, linear
  constraints, and solver options, and switches to a compact non-editing mode
  above 12 variables so an imported large model stays solvable and exportable;
- import and export both go through the existing `qp_json_io` codec, and a
  focused test asserts that an imported model reaches the use case with the
  same problem payload as the manually entered one;
- `QPSolutionView` reports mathematical status, an explanation per outcome,
  dependency failure, objective value and sense, the candidate vector,
  constraint activity, dual multipliers or their explicit absence, KKT
  residuals, backend execution diagnostics, and the independent validation
  report with its localized limitations;
- `QPContourPlotWidget` draws objective contours, the feasible set, and the
  candidate for exactly two variables, and names the reason when it cannot
  (`unsupported_dimension`, `no_window`, `matplotlib_unavailable`), with the
  exact tables remaining the complete answer in every dimension;
- English and Italian strings are at full key parity, and both educational
  pages (`qp_problem`, `qp_example`) ship in both languages;
- the presentation layer imports no OSQP, recomputes no authoritative result,
  and obtains validation only from the registered `QPResultCodec` and
  `QPIndependentSolutionValidator`.

### Review correction

Review found that the initial Stage A implementation used an unfrozen public
shape (`lower_bound`, `linear_coefs`, `options`, and a variable-value object)
instead of the contract's `lb`, `linear_coefficients`, `solver_options`, and
ordered result array. It also dropped `termination_reason`, treated any finite
early-stopped vector as feasible, and did not fully verify dual signs and
complementary slackness. A separate correction commit restores the frozen v1
schema, strict unknown-field rejection and option ranges, termination
propagation, primal checks for early-stopped candidates, and complete claimed
KKT checks. QP gates are accepted only after that correction passes both core
and UI regressions.

## General Stop Conditions

Stop and request a decision if:

- OSQP behavior cannot be mapped without contradicting the frozen statuses;
- maximization or dual sign conversion cannot be independently established;
- an accepted near-PSD matrix is rejected by OSQP without a contract-consistent
  treatment;
- packaging requires an unsupported license, download, or platform change;
- public fixture output is nondeterministic beyond declared tolerances;
- transport parity requires a QP-specific API branch;
- UI requirements would require presentation-owned mathematics;
- completing the work would silently broaden QP v1 or refactor unrelated
  capabilities.
