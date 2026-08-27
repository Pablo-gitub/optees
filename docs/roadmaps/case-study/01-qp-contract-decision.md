# Convex QP Contract Decision Plan

## Work Unit

- **ID:** `OPT-DS-01`
- **State:** ready
- **Type:** contract and backend decision; no production implementation
- **Parent roadmap:** `ROADMAP.md`
- **Next gate:** `QP-C`

## Objective

Produce a reviewed, implementation-ready version 1 contract for a general
convex Quadratic Programming capability. The work unit must resolve the
mathematical, numerical, architectural, validation, dependency, packaging, and
public-JSON decisions before domain or solver code is added.

## Required Formulation Decision

Evaluate and freeze one canonical convention equivalent to:

\[
\operatorname{minimize}_x
\quad \frac{1}{2}x^TQx + c^Tx + \alpha
\]

subject to linear equalities, linear inequalities, and variable bounds.

The decision must state:

- whether version 1 supports minimization only or also safely represents
  concave maximization;
- whether callers provide the full symmetric `Q` or another unambiguous form;
- how asymmetry is rejected or normalized;
- whether `Q` coefficients use the explicit `1/2` convention;
- how positive-semidefinite convexity is assessed and with which tolerances;
- how sparse and dense representations are scoped for version 1;
- how variable ordering and names bind every matrix/vector entry;
- which non-finite, malformed, dimensionally inconsistent, or non-convex inputs
  are rejected before execution.

## Decisions To Produce

### Mathematical scope

- Convex objective boundary and any explicitly supported concave-max form.
- Linear relation and bound semantics reused from LP where appropriate.
- Status semantics for invalid, infeasible, unbounded, numerical failure,
  iteration/time limit, feasible candidate, and optimal.
- Meaning and availability of primal objective, dual information, residuals,
  iterations, and backend diagnostics.

### Backend evidence

Compare maintained candidate engines using primary documentation and a local
proof where practical. Record:

- algorithm and convexity assumptions;
- license compatibility;
- Python 3.12 support and supported platforms;
- wheel and native-library availability;
- deterministic behavior and tolerances;
- infeasible/unbounded/status fidelity;
- time-limit and cancellation behavior;
- dual/KKT information;
- warm-start support, if relevant but not required;
- PyInstaller implications and expected bundle-size impact.

Do not select a backend merely because it solves one example. If no candidate
meets the release standard, record the blocker and propose a smaller honest
version 1 rather than weakening status claims.

### Public contract

Specify:

- proposed stable capability ID and problem type;
- contract, problem-schema, and result-schema version 1;
- complete valid problem and result examples;
- default options and bounded limits;
- stable error codes;
- descriptor metadata and backend availability semantics;
- compatibility rules for future sparse matrices, warm starts, and MIQP.

### Independent validation

Define checks that do not merely repeat a backend success flag:

- complete finite vector and dimension checks;
- variable bounds;
- equality and inequality feasibility;
- objective recomputation from the declared convention;
- optional stationarity, dual feasibility, and complementary slackness only
  when required data is independently available;
- named absolute, relative, feasibility, symmetry, and PSD tolerances;
- explicit limitations: feasibility/KKT checks are not an independent proof
  that the business model is correct.

### Product surface

Define the minimum educational vertical slice:

- formulation fields and JSON import;
- solution facts and diagnostics;
- canonical result table;
- one useful visualization only if semantically justified;
- English/Italian concepts that must remain synchronized;
- deterministic analytic references and one suitable external benchmark path.

## Required Repository Outputs

The implementing agent should create or update only documentation and bounded
decision evidence:

- create `docs/contracts/quadratic-programming-contract.md`;
- update this plan with every resolved decision and mark `QP-C` complete only
  when no blocking ambiguity remains;
- update `docs/roadmaps/case-study/ROADMAP.md`, `docs/roadmaps/project.md`,
  `README.md`, and
  `docs/roadmaps/README.md` only where the accepted decision changes navigation
  or status;
- add a small decision script or test fixture only if needed to reproduce
  numerical/backend evidence; do not add production QP domain or adapter code.

## Explicitly Out Of Scope

- production domain entities, ports, adapters, codecs, services, GUI, REST, or
  MCP changes;
- MIQP or integer variables;
- non-convex quadratic optimization;
- trading, portfolio, covariance, or asset-specific models;
- workflow registration;
- unrelated LP/MILP refactoring;
- adding a runtime dependency before the decision is accepted.

## Verification

- Validate every JSON example structurally against the proposed schema.
- Recompute every analytic example independently.
- Probe at least one feasible optimum, one boundary optimum, one infeasible
  model, one unbounded model where supported, one asymmetric matrix, and one
  non-PSD matrix.
- Record any check that cannot run because a candidate dependency or platform
  is unavailable.
- Run the repository Markdown-link test and `git diff --check`.

## Stop Conditions

Stop and request a decision instead of guessing if:

- backend candidates imply materially different public statuses or scope;
- supporting maximization would admit non-convex models;
- PSD tolerance cannot be specified honestly;
- a new dependency conflicts with Python, SciPy, packaging, or license bounds;
- the proposed contract would force an incompatible LP/MILP refactor;
- sparse versus dense representation changes the version 1 viability.

## Completion Gate `QP-C`

This work unit is complete only when the formula and coefficient convention are
unambiguous, version 1 scope and limits are frozen, a backend direction is
supported by evidence, all public statuses and validator claims are defined,
valid and invalid examples are reproducible, future MIQP compatibility is
addressed without implementing it, documentation links pass, and the result is
one reviewable atomic commit.
