# Linear Scenario Min-max And Max-min Plan

## Work Unit

- **ID:** `OPT-DS-03`
- **State:** `OPT-DS-03A` and `OPT-DS-03B` complete after review; `OPT-DS-03C` remains unstarted
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

**Gate `ROBUST-D` (Achieved after review correction):** contract decisions, mathematical formulations,
non-aliasing proof, analytical examples, epigraph/hypograph reductions, JSON
schemas, and analytical probes are frozen in
`docs/contracts/linear-scenario-optimization-contract.md` and
`tests/utility/test_linear_scenario_contract_decision_probes.py`. No
production capability exists. This decision gate has passed independent review.

## Micro-gate B — Domain And Exact Reduction (`OPT-DS-03B`)

Implement only pure robust-scenario domain types, strict construction rules,
and an application-owned reduction to the existing `LPModel` and `MILPModel`.
This gate must not solve a problem or create a second LP/MILP representation.

### Required pre-implementation comparison

Before editing, record in the implementation report how the proposed types and
reduction reuse or differ from all of these existing sources:

- `domain/models/lp/lp_model.py` and its variable, objective, constraint,
  bounds, relation, and sense value objects;
- `domain/models/milp/milp_model.py` and `Integrality`;
- `utility/lp_json_io.py` and `utility/milp_json_io.py` for field and option
  semantics;
- the reviewed public contract in
  `docs/contracts/linear-scenario-optimization-contract.md`.

No copied contract schema or parallel generic linear algebra model is allowed.

### Authorized implementation

- Add immutable ordered robust problem/value types under one focused domain
  package. Preserve declared variable and scenario order.
- Validate non-empty unique variable names and scenario IDs, exact coefficient
  dimensions, finite coefficients/offsets/options, legal bounds, binary domain
  semantics, constraint dimensions, positive tolerances, and generated-name
  collisions at construction time.
- Implement one pure reducer returning a typed reduction record containing the
  delegated `LPModel` or `MILPModel`, orientation, original variable order,
  scenario order, and auxiliary-variable identity needed for later result
  reconstruction.
- Use the reviewed epigraph/hypograph signs exactly. Preserve shared objective
  coefficients and offsets, all shared constraints, bounds, labels, and
  integrality. The auxiliary variable is continuous and unbounded.
- Route an all-continuous problem to `LPModel`; route any integer or binary
  decision variable to `MILPModel`. Preserve only solver options already
  representable by the delegated model; do not invent backend options.
- Generate the auxiliary name deterministically and collision-safely without
  mutating user names.

### Required tests

- Direct structural assertions against real `LPModel`/`MILPModel` instances,
  not dictionaries copied from documentation.
- Both reviewed analytical examples and the binary example, checking every
  delegated objective coefficient, offset, relation, right-hand side, bound,
  integrality token, and ordering position.
- Shared-objective and non-zero-offset cases for both orientations.
- Auxiliary-name collision and deterministic repeatability cases.
- Rejection tests for duplicate identities, dimension mismatch, NaN/infinity,
  invalid bounds/integrality, empty scenarios, and invalid tolerances.
- Regression tests proving the reducer does not mutate inputs and produces the
  same canonical delegated representation on repeated calls.

Tests must import production types and reducers. A test that only validates a
schema or formula duplicated inside the test is not gate evidence.

### Explicit exclusions

- no concrete solver invocation or SciPy/OR-Tools dependency in new production code;
- no result model, independent validator, codec, capability ID, descriptor,
  registry/composition, CLI, REST, MCP, artifact, report, or UI change;
- no edits to existing LP/MILP public contracts unless a genuine incompatibility
  is found and work stops for review.

### Stop conditions

Stop without improvising if the reviewed robust contract cannot be represented
losslessly by the existing LP/MILP models, if a required solver option has no
existing owner, if the auxiliary variable cannot remain continuous in the
MILP path, or if an existing public contract would need to change.

Required coverage:

- immutable ordered scenario packages and decision variables;
- continuous reduction to LP;
- integer/binary delegation to MILP without weakening domains;
- objective constants and original-sense reconstruction;
- deterministic generated auxiliary names without collision;
- analytic equivalence against the `ROBUST-D` examples;
- no solver, transport, composition or UI changes.

**Gate `ROBUST-K` (Achieved after review correction):** every accepted contract example reduces deterministically
to actual Optees LP/MILP domain models; focused tests in
`tests/domain/test_scenario_model.py` and
`tests/application/services/test_scenario_reduction_service.py` prove full structural
equivalence, rejection behavior, immutability, auxiliary collision safety, and deterministic ordering.
No solver, transport, composition, or UI capability was introduced. Only after review may `OPT-DS-03C` begin.

## Micro-gate C — Use Case, Result And Independent Validation (`OPT-DS-03C`)

This stage is split into three separately reviewed implementation units. Do not
combine them. Existing LP/MILP solutions, result codecs, validators, status
enums, and `SolutionValidation` are sources of truth rather than templates to
copy.

### Micro-gate C1 — Result Reconstruction (`OPT-DS-03C1`)

Implement only an immutable robust result model and a pure reconstruction
service that receives the original `ScenarioModel`, its reviewed
`ScenarioReductionResult`, and an already produced `LPSolution` or
`MILPSolution`. It does not invoke a solver and does not perform independent
validation yet.

Before editing, compare and report the exact candidate, status, diagnostics,
ordering, and no-candidate shapes of `LPSolution`, `MILPSolution`,
`LPResultCodec`, and `MILPResultCodec`.

The reconstructed result must:

- expose only original decision variables in `original_variable_order`; never
  expose the generated auxiliary variable as a user decision;
- retain orientation and `scenario_order`, recompute every scenario value from
  the original model, derive the guarantee and deterministic binding set using
  the frozen tolerance, and preserve negative guarantees;
- compare the recomputed guarantee with both the auxiliary value and delegated
  objective using an explicit finite tolerance; record inconsistency as a
  reconstruction failure rather than silently replacing values;
- carry the delegated LP/MILP domain solution or a typed, lossless reference to
  its status and diagnostics so later layers do not invent backend metadata;
- preserve `optimal`, `feasible`, `infeasible`, `unbounded`, and `not_solved`
  distinctions. Only optimal/feasible outcomes may contain a candidate;
- return an explicit no-candidate robust result for infeasible, unbounded, and
  not-solved outcomes, with no fabricated zero objective, variables, scenario
  values, or binding set.

Required tests use real domain `LPSolution`/`MILPSolution` objects and cover both
orientations, continuous and discrete candidates, multiple binding ties,
negative guarantees, non-zero shared offsets, reordered solver mappings,
missing/unknown/duplicate/non-finite variables, missing/wrong auxiliary value,
objective mismatch, and all no-candidate statuses. Tests must not copy codec
schemas or use concrete numerical solvers.

Explicit exclusions: no solver/port invocation, no independent
`SolutionValidation`, no new public JSON codec/schema, capability registration,
composition, transport, artifact, report, or UI.

Stop if LP and MILP domain solutions cannot support one lossless reconstruction
contract, if their status meanings conflict, or if preserving diagnostics would
require changing an existing public codec.

**Gate `ROBUST-R` (Achieved after review correction):** pure reconstruction produces a deterministic, lossless
robust domain result (`ScenarioResult`) from real delegated `LPSolution` and `MILPSolution` types
via `ScenarioReconstructionService`, preserves explicit immutable variable/scenario order without a
domain-to-application dependency, and rejects mismatched reductions as well as missing, non-finite,
unknown, or tampered candidate/guarantee cases.
No solver, validator, codec, transport, or UI capability was introduced. Only after review may `OPT-DS-03C2` begin.

### Micro-gate C2 — Independent Robust Validation (`OPT-DS-03C2`)

After `ROBUST-R` review, add `ScenarioIndependentSolutionValidator` using the
existing `SolutionValidation`, `ValidationCheck`, and `ValidationViolation`
contracts. Recompute original vector identity, finiteness, bounds, integrality,
shared constraints, every scenario value, guarantee, binding set, auxiliary
consistency, and delegated objective consistency without trusting diagnostics.
Optimality remains a mathematical status, not a validation claim. Infeasible,
unbounded, and no-candidate results return honest `not_available`.

**Gate `ROBUST-V`:** analytic and tampered-result tests prove robust semantics
independently of a concrete solver.

### Micro-gate C3 — Application Orchestration (`OPT-DS-03C3`)

After `ROBUST-V` review, add the application use case. Reuse
`ScenarioReductionService`, `SolveLPUseCase`, and `SolveMILPUseCase` through
injected application dependencies, then reconstruct and validate exactly once.
Use deterministic fake solver ports. Do not duplicate LP/MILP mapping or invoke
concrete adapters.

**Gate `ROBUST-A`:** fake-port tests prove routing, status/diagnostic
preservation, reconstruction, validation, and failure propagation end to end.

The parent `OPT-DS-03C` is complete only when `ROBUST-R`, `ROBUST-V`, and
`ROBUST-A` are all reviewed.

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

## Next implementation boundary

`OPT-DS-03A/B` are complete after review. `OPT-DS-03C1` is the only next
implementation authorized here. C2–F remain separately reviewed work units.
