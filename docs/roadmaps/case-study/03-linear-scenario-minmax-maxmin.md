# Linear Scenario Min-max And Max-min Plan

## Work Unit

- **ID:** `OPT-DS-03`
- **State:** ready for `OPT-DS-03A` only
- **Type:** domain-neutral robust-scenario capability delivered through bounded micro-gates
- **Parent roadmap:** `ROADMAP.md`
- **Prerequisite:** `QP-I` and `QP-UI` satisfied by `OPT-DS-02`
- **Consumer:** Decision Simulator phase `DS-05`
- **Backend implementation owner:** Gemini
- **UI owner:** Claude, only at `OPT-DS-03F`
- **Review:** Codex after every micro-gate
- **Final integration gate:** `ROBUST-C`

## Objective

Deliver two explicit linear finite-scenario orientations:

- `minimize_maximum_loss`;
- `maximize_minimum_reward`.

They must share a frozen scenario package while remaining distinct public
semantics. Both formulations must reduce exactly to the existing LP/MILP
application capabilities where their variable domains permit it. Optees owns
the mathematical contract, reduction, execution and independent validation;
it must not acquire market, portfolio or trading concepts.

## Execution Discipline

This plan is intentionally split more finely than the QP vertical slice.

- Only one micro-gate may be assigned at a time.
- Every micro-gate starts from its accepted predecessor commit.
- Gemini must stop after its declared gate and create one atomic local commit.
- Codex independently reviews the diff, contract claims and verification
  evidence before the next prompt is written.
- A later micro-gate must not be implemented opportunistically.
- Contract fields are compared field-by-field against canonical examples.
- A failed or unavailable check prevents the gate from being declared reached.
- Material review corrections use a separate atomic commit.

## Frozen Architectural Direction

- Scenario semantics belong to dedicated domain types, not to transports.
- Reduction is an application service producing an ordinary LP or MILP model.
- Existing LP/MILP solvers remain the numerical authority; no new solver is
  introduced for the linear scenario slice.
- The public robust result retains scenario values, binding scenarios and the
  guaranteed bound instead of exposing only the delegated solver result.
- The validator recomputes the robust interpretation from the original
  scenario package and candidate.
- CLI, REST and MCP remain generic delivery surfaces.
- UI code may visualize the frozen application result but may not recompute the
  authoritative robust decision.

## Micro-gate A — Semantic And Contract Decision (`OPT-DS-03A`)

### Scope

Freeze, without production implementation:

- mathematical definitions and sign conventions for both orientations;
- scenario, decision-variable and coefficient ordering;
- shared versus scenario-specific linear terms and constants;
- continuous, integer and binary domain boundaries;
- deterministic tie handling and binding-scenario semantics;
- empty, duplicate, non-finite, dimension-invalid and unsupported inputs;
- public problem/result examples and version fields;
- job, mathematical, termination and validation status interpretation;
- exact LP/MILP epigraph reductions, including objective reconstruction;
- independent validation claims and limitations;
- size/resource limits and cancellation inheritance;
- domain-neutral terminology and Simulator ownership boundaries.

### Allowed changes

- this roadmap;
- one new canonical contract under `docs/contracts/`;
- focused contract-decision probes or documentation-link tests;
- roadmap navigation/status entries required by those documents.

### Forbidden changes

- production domain, application, adapter, composition or transport code;
- LP/MILP refactoring;
- UI, localization or graphics;
- Simulator files or market examples;
- a generic nonlinear, game-theory or probabilistic robust API;
- workflow-registry implementation.

### Required evidence

- at least one hand-checkable analytic example for each orientation;
- proof table showing the epigraph/hypograph reduction term by term;
- examples with multiple binding scenarios and negative values;
- explicit demonstration that the two orientations are not aliases;
- structural validation of every canonical JSON example;
- documentation-link and diff-whitespace checks.

### Stop conditions

Stop and request review if LP/MILP status semantics cannot represent the
robust claim honestly, if scenario probabilities become necessary, or if one
public shape cannot preserve both orientations without ambiguous fields.

**Gate `ROBUST-D`:** contract decisions and analytic probes are frozen; no
production capability exists. Only after review may `OPT-DS-03B` begin.

## Micro-gate B — Domain And Exact Reduction (`OPT-DS-03B`)

Implement only pure domain types, strict construction rules and the
application-owned reduction to existing LP/MILP models.

Required coverage:

- immutable ordered scenario packages and decision variables;
- continuous reduction to LP;
- integer/binary delegation to MILP without weakening domains;
- objective constants and original-sense reconstruction;
- deterministic generated auxiliary names without collision;
- analytic equivalence against the `ROBUST-D` examples;
- no solver, transport, composition or UI changes.

**Gate `ROBUST-K`:** every accepted contract example reduces deterministically
to the reviewed LP/MILP representation and reconstructs the robust objective.

## Micro-gate C — Use Case, Result And Independent Validation (`OPT-DS-03C`)

Add the application use case and robust result model. Execute through injected
LP/MILP application ports and independently recompute:

- candidate identity and finiteness;
- original variable domains and bounds;
- every scenario value;
- worst/binding scenario set;
- guarantee value and delegated objective consistency;
- delegated validation provenance and honest partial/not-available states.

Use fake deterministic ports first. Do not register a public capability yet.

**Gate `ROBUST-V`:** analytic and tampered-result tests prove the application
semantics independently of a concrete solver.

## Micro-gate D — Public Capability And Delivery (`OPT-DS-03D`)

Add strict codecs, descriptor, composition and generic CLI/REST/MCP delivery.
Unknown fields, non-finite values and version mismatches must fail with stable
robust-specific detail codes. Concrete execution delegates to the already
registered LP/MILP backends and preserves their diagnostics and limitations.

**Gate `ROBUST-I`:** discovery, validation, execution and normalized results
have parity across application service, CLI, REST and MCP.

## Micro-gate E — Frozen Fixtures And Simulator Handoff (`OPT-DS-03E`)

Publish domain-neutral versioned fixtures for both orientations, continuous
and discrete domains, multiple ties, infeasible input, delegated timeout or
feasible incumbent where supported, dependency failure and tampered results.
Record canonical SHA-256 hashes and the exact Optees commit/version consumed by
the Simulator. Run the appropriately broad non-GUI regression gate.

**Gate `ROBUST-C`:** the Simulator may implement expected-value and worst-case
policies against the identical frozen scenario package.

## Micro-gate F — Desktop Workflow (`OPT-DS-03F`, Claude)

Only after `ROBUST-C`, Claude may implement the bilingual, accessible UI for
scenario entry, orientation selection, result inspection, scenario-value
comparison and binding-scenario visualization. Presentation must consume the
reviewed application API and retain failures, validation and delegated solver
statuses visibly.

**Gate `ROBUST-UI`:** focused GUI and regression tests pass and Codex accepts
the separately committed UI work.

## First Authorized Implementation

Only `OPT-DS-03A` is currently authorized. Sections B–F are sequencing
constraints, not permission to implement them.
