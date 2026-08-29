# Decision Simulator Capability Expansion Roadmap

## Document Status

- **State:** in progress
- **Purpose:** coordinate the bounded Optees expansion motivated by the Optees
  Decision Simulator case study
- **Product relationship:** this is a parallel evidence track; it does not
  replace the general product sequence in `project.md`
- **Latest completed detailed work unit:** `02-qp-vertical-slice.md`
- **Current detailed work unit:** `03-linear-scenario-minmax-maxmin.md`
- **Consumer roadmap:** the Decision Simulator `docs/ROADMAP.md`

## Goal

Expand Optees enough to compare meaningful forecasting and optimization
orchestrations over repeated market-data decisions, while keeping every new
capability domain-neutral and useful outside trading.

The case study is both a consumer and an evidence source. It must show where
Optees adds value, where a capability is insufficient, and which repeated
orchestrations deserve promotion into reusable registered workflows.

## Scope Boundary

Optees owns:

- mathematical domain models and solver ports;
- versioned problem and result contracts;
- solver execution and honest statuses;
- independent validation;
- capability discovery;
- optional artifacts and reports;
- registration and execution of externally supplied, validated workflows.

The Decision Simulator owns:

- market datasets and knowledge cutoffs;
- episodes, rounds, policies, and virtual accounts;
- transaction and operating-cost semantics;
- formulation choices specific to a market policy;
- scoring, replay, and policy comparison;
- evidence that motivates or rejects an Optees expansion.

Optees must not acquire trading-specific entities, price feeds, portfolio
terminology, brokerage behavior, or claims of financial performance.

## Delivery Principles

- Deliver complete vertical capabilities, not solver-only utilities.
- Freeze each public contract before the simulator implements its production
  adapter or policy.
- Use deterministic analytic references before external benchmarks.
- Treat predicted return, risk, loss, turnover, and regret as distinct
  semantics.
- Keep min-max/max-min placement explicit: linear, quadratic, robust-scenario,
  game-theory, and nonlinear forms are not one generic algorithm.
- Let case-study evidence prioritize forecasting depth; do not start deep
  learning or broad AutoML without a measured limitation.
- The Workflow Registry accepts validated definitions created externally. It
  does not preinstall or invent domain orchestrations.
- Every integration gate records the exact Optees commit/version, capability
  ID, contract versions, and fixture hashes consumed by the simulator.

## Program Sequence

### Progress overview

| Done | Work unit | Current state |
| --- | --- | --- |
| [x] | `OPT-DS-01` — Convex QP Contract Decision | `QP-C` achieved |
| [x] | `OPT-DS-02` — Convex QP Vertical Slice | `QP-I` and `QP-UI` achieved |
| [ ] | `OPT-DS-03` — Linear Scenario Min-max And Max-min | `OPT-DS-03A/B`, `OPT-DS-03C1`, and `OPT-DS-03C2A` complete after review; `OPT-DS-03C2B` next |
| [ ] | `OPT-DS-04` — Targeted Forecasting Expansion | Awaiting Simulator evidence |
| [ ] | `OPT-DS-05` — Convex MIQP | Not started |
| [ ] | `OPT-DS-06` — Workflow Registry MVP | Not started |
| [ ] | `OPT-DS-07` — Min-max Regret Reference Workflow | Not started |
| [ ] | `OPT-DS-08` — Evidence, Packaging, And Release Gate | Not started |

### OPT-DS-01 — Convex QP Contract Decision

- Freeze the mathematical convention, convexity boundary, status semantics,
  JSON shape, validation claims, and backend-selection evidence.
- Decide how QP relates to existing LP/MILP domain types without prematurely
  refactoring them.
- Define deterministic references and packaging constraints.

Detailed plan: `01-qp-contract-decision.md`.
Frozen contract: `../../contracts/quadratic-programming-contract.md`.

**Gate QP-C:** achieved; the contract is frozen and can be reviewed
independently of any GUI, transport, or trading formulation.

### OPT-DS-02 — Convex QP Vertical Slice

- Implement domain, port, adapter, use case, codecs, capability registration,
  independent validation, CLI/REST/MCP delivery, references, fixtures, and
  packaging evidence first. This capability stage is owned by Gemini and stops
  for review at `QP-I`.
- After `QP-I`, Claude exclusively owns the desktop workflow, localization,
  educational graphics, and QP visualizations. UI code consumes the reviewed
  application layer and never owns solver or validation behavior.
- Preserve exact distinctions among invalid, non-convex, infeasible,
  unbounded, numerical failure, feasible candidate, and proven optimum where
  the selected backend supports those claims.

Detailed plan: `02-qp-vertical-slice.md`.

**Gate QP-I:** achieved; frozen problem/result fixtures and capability implementation completed.

**Gate QP-UI:** achieved; the separately committed PySide6 QP workflow is
bilingual, accessible, reviewed, and still passes `QP-I`.

### OPT-DS-03 — Linear Scenario Min-max And Max-min

- Define a finite, explicit scenario package with stable identifiers and
  shared decision variables.
- Support `minimize_maximum_loss` and `maximize_minimum_reward` as distinct
  orientations.
- Start with linear scenario expressions reducible exactly to LP; reuse MILP
  only when variable domains require it.
- Return per-scenario values, the worst/binding scenarios, guarantee value,
  solver status, and independent validation.

Detailed plan: `03-linear-scenario-minmax-maxmin.md`.
Frozen contract: `../../contracts/linear-scenario-optimization-contract.md`.

**Gate ROBUST-D:** achieved after review correction; mathematical formulation,
epigraph/hypograph reductions, envelope-compatible JSON schemas, non-aliasing
semantics, and analytical probes are frozen.

**Gate ROBUST-K:** achieved after review correction; pure domain models and exact epigraph/hypograph reductions
to LPModel and MILPModel implemented and structurally verified against all reference cases.

**Gate ROBUST-R:** achieved; pure result reconstruction (`ScenarioResult`) from real `LPSolution`/`MILPSolution`
with strict consistency checks and deterministic ordering verified.

**Gate ROBUST-VS:** achieved; structural independent validation (`ScenarioIndependentSolutionValidator`) verified
with stable detail codes, orientation/order/status/type checks, and honest `not_available`.

**Gate ROBUST-V:** achieved; complete mathematical validation (`ScenarioIndependentSolutionValidator`) verified
with bounds, discrete domain integrality, shared constraints, scenario evaluations, worst-case guarantee,
deterministic binding set, and auxiliary/objective consistency. Review corrections bind classification to
the model tolerance and prevent malformed numerical or binding fields from escaping the validation contract.

`ROBUST-V` completion evidence:

- [x] Preserve explicit original-variable and scenario ordering.
- [x] Keep the robust domain independent from application contracts.
- [x] Recompute and cross-check scenario guarantee, auxiliary value, and delegated objective.
- [x] Preserve LP/MILP status and diagnostics through deeply immutable snapshots.
- [x] Reject mismatched reductions and malformed candidate payloads.
- [x] Reject objective or variable payloads for no-candidate statuses.
- [x] Pass focused reconstruction, codec, validator, and LP/MILP use-case regressions.
- [x] Implement structural independent-validation foundation in `OPT-DS-03C2A`.
- [x] Review malformed no-candidate reporting and prevent duplicate violations.
- [x] Complete original-domain feasibility and robust-semantic validation in the medium gate `OPT-DS-03C2B`.
- [x] Review model-tolerance fidelity and malformed-candidate failure containment.
- [ ] Implement application orchestration and fake-port use case in `OPT-DS-03C3`.

**Gate ROBUST-C:** the simulator can run expected-value and worst-case policies
against the identical frozen scenario package.

### OPT-DS-04 — Targeted Forecasting Expansion

Prioritize this phase using evidence from baseline simulator episodes. Candidate
increments are:

- random walk with drift;
- return rather than only level forecasting;
- transparent autoregression and bounded ARIMA;
- rolling or exponentially weighted volatility estimates;
- calibrated intervals, quantiles, or finite scenarios;
- chronological model comparison without future leakage.

The detailed roadmap must select the smallest coherent subset that unlocks the
next decision experiments. Deep neural forecasting, large search spaces, and
opaque automatic model selection remain deferred.

**Gate FC-E:** every added output has chronological evaluation, independent
validation, and a documented downstream interpretation.

### OPT-DS-05 — Convex MIQP

- Extend the frozen quadratic semantics with continuous, integer, and binary
  variables plus linear constraints.
- Select a maintained backend whose license, wheels, native dependencies,
  time limits, incumbents, bounds, gaps, and PyInstaller behavior meet the
  Optees release standard.
- Preserve feasible incumbents without misreporting optimality.
- Add references for cardinality, fixed activation, minimum quantity, and
  quadratic-risk structures without introducing trading-specific contracts.

**Gate MIQP-I:** simulator fixtures cover optimal, feasible-with-gap,
infeasible, timeout, and validation-failure outcomes.

### OPT-DS-06 — Workflow Registry MVP

- Accept a candidate workflow definition created by an agent, user, or program.
- Validate its DAG, capability versions, mappings, allowlisted transforms,
  parameters, failure rules, and approval points.
- Register an immutable version only after validation and explicit promotion.
- Expose discovery and execution through application services, then thin
  CLI/REST/MCP adapters.
- Preserve deprecated and retired versions for audit and replay.
- Execute a registered workflow later without requiring the original agent.

Reference orchestrations may be used as acceptance fixtures, but they are not
preinstalled product workflows. Detailed lifecycle and security constraints
remain in `optimization-workflows.md`.

**Gate WF-R:** the same externally defined workflow can be validated,
registered, recalled, and executed with retained provenance.

### OPT-DS-07 — Min-max Regret Reference Workflow

- Solve the benchmark optimum for each scenario using atomic capabilities.
- Compute a validated regret matrix through allowlisted mappings.
- Minimize maximum regret and retain every intermediate result and receipt.
- Compare direct program orchestration, agent orchestration, and registered
  workflow execution.

This phase validates the Registry with a genuinely composite mathematical
process; it does not make regret a hidden transport concern.

### OPT-DS-08 — Evidence, Packaging, And Release Gate

- Run scientific and analytic gates for every new capability.
- Run installed-package acceptance through the public interfaces.
- Pin the Optees version consumed by each publishable simulator experiment.
- Publish negative results and limitations alongside improvements.
- Decide the next expansion only after reviewing case-study evidence.

## Cross-Repository Integration Gates

| Gate | Optees output | Simulator action |
| --- | --- | --- |
| `QP-C` | Reviewed QP contract decision | May prepare fake DTOs, not a production adapter |
| `QP-I` | Frozen QP descriptor and fixtures | Implement QP policy and MCP/REST parity |
| `ROBUST-C` | Frozen scenario contract | Implement worst-case policy comparison |
| `FC-E` | Evaluated forecast outputs | Consume only outputs with explicit semantics |
| `MIQP-I` | Frozen MIQP fixtures | Implement discrete-risk policies |
| `WF-R` | Registry API and lifecycle | Register previously validated simulator workflows |

## Deferred Until Evidence Justifies Them

- non-convex QP or MIQP;
- generic nonlinear robust optimization;
- CVaR before loss, confidence, and scenario-probability semantics are frozen;
- deep learning and large-scale hyperparameter search;
- DP, MDP, bandit, reinforcement-learning, or adaptive-policy engines;
- arbitrary executable workflow steps;
- trading-specific capability contracts;
- expansion of unrelated mathematical families solely for this case study.

## Program Success Criteria

This track succeeds when the simulator can compare baseline, linear,
quadratic, worst-case, discrete-quadratic, and registered-workflow policies
over identical information; every decision remains reproducible and validated;
Optees capabilities remain domain-neutral; and the evidence shows both where
the new mathematics adds value and where it does not.
