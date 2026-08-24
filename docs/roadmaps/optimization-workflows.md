# Composite Optimization Workflows Roadmap

## Document Status

- **State:** planned
- **Prerequisite baseline:** stable versioned atomic capabilities, validation,
  jobs, artifacts, and reports are already shipped
- **First design gate:** freeze workflow identity, step mappings, audit records,
  restart semantics, and approval boundaries before adding an executor
- **External consumer:** [Optees Decision Simulator](https://github.com/Pablo-gitub/optees-decision-simulator)
- **MVP dependency:** the Decision Simulator MVP does not require this roadmap;
  it can orchestrate released Forecasting and LP/MILP capabilities externally

## Purpose

Optees currently executes atomic mathematical capabilities. A caller may use a
Forecasting result to formulate a MILP or follow capacity allocation with 3D
packing, but the caller owns that composition, its state, and its audit trail.

This roadmap defines the later point at which reviewed compositions may become
versioned Optees workflows. It does not move experiment scheduling, virtual
accounts, dataset time, policy competition, or scoring into Optees.

## Ownership Boundary

| Concern | Owner |
| --- | --- |
| Mathematical problem and result contracts | Optees atomic capability |
| Independent solution validation | Optees capability validator |
| Declarative capability-to-capability mapping | Future Optees workflow layer |
| Step lifecycle, retry, approval, and workflow audit | Future Optees workflow layer |
| Dataset event and knowledge time | Decision Simulator |
| Episode, round, policy, and virtual account state | Decision Simulator |
| Evaluation, scoring, replay, and policy comparison | Decision Simulator |
| Real-world side effects | Out of scope for both MVPs |

The workflow layer must depend on the application contracts and capability
registry. It must not make HTTP, MCP, Qt, or a database transport the owner of
composition semantics.

## Product Rules

- A workflow references immutable capability IDs and supported contract
  versions; it never selects a solver from an unversioned display name.
- Every step validates its exact canonical payload before execution.
- Input mappings are declarative and allowlisted. Arbitrary Python, shell,
  templates with code execution, and unrestricted expressions are forbidden.
- Mathematical status, independent validation status, step lifecycle, and
  workflow lifecycle remain separate facts.
- A downstream failure never silently mutates and retries an upstream model.
- Retries are bounded and permitted only for operations declared idempotent.
- Material changes to objectives, constraints, assumptions, or accepted input
  require a recorded human approval or a new workflow run.
- Intermediate payloads, results, validation receipts, versions, and hashes are
  retained according to an explicit bounded policy.
- A workflow may be deterministic without producing byte-identical numerical
  results across different solver versions; compatibility and tolerances must
  be stated explicitly.

## Phase 0 - Contract Decisions

- [ ] Define workflow, step, edge, input mapping, condition, approval, and run
  schemas with independent version numbers.
- [ ] Define canonical JSON and hashing for workflow definitions and run input.
- [ ] Define step and workflow states, including cancellation, timeout,
  validation failure, infeasibility, partial result, and incompatible version.
- [ ] Define idempotency keys, bounded retry rules, resume points, and terminal
  failure behavior.
- [ ] Define the minimum audit record and retention limits.
- [ ] Threat-model report injection, mapping confusion, capability substitution,
  resource exhaustion, secret leakage, and replay ambiguity.
- [ ] Freeze the boundary between deterministic workflow execution and
  agent-assisted workflow authoring.

**Exit criterion:** a workflow can be reviewed as data without executing it or
depending on a transport-specific object.

## Phase 1 - Application-Owned Workflow Registry

- [ ] Add an immutable registry of reviewed workflow definitions.
- [ ] Resolve every referenced capability and contract version at registration.
- [ ] Reject cycles in the first release; support directed acyclic workflows
  only.
- [ ] Validate all mappings against source result and destination problem
  schemas before accepting a definition.
- [ ] Add a fake-capability test harness with analytic success and failure cases.
- [ ] Expose registry discovery through the existing composition root without
  changing atomic capability registration.

## Phase 2 - Bounded Executor And Audit

- [ ] Implement one application-owned executor over existing job services.
- [ ] Persist immutable step inputs, results, validation receipts, hashes, and
  transitions behind a workflow-run repository port.
- [ ] Add bounded cancellation, timeout, restart, and resume behavior.
- [ ] Stop on incompatible contracts, invalid mappings, failed validation, or
  undeclared partial results according to the frozen workflow policy.
- [ ] Support explicit approval checkpoints before material model changes.
- [ ] Add deterministic replay diagnostics that report divergence instead of
  rewriting prior run history.

## Phase 3 - First Reference Workflows

- [ ] Forecasting to production-planning MILP using a synthetic, versioned
  dataset and explicit transformation rules.
- [ ] Capacity allocation to single-container 3D packing verification, with a
  visible downstream infeasibility path and no silent capacity adjustment.
- [ ] Add one analytic happy path, one invalid mapping, one unavailable
  capability, one infeasible downstream model, and one cancellation reference.
- [ ] Produce optional artifacts and a report from retained step provenance.

These examples prove composition mechanics. They do not establish that the
workflow represents every business context correctly.

## Phase 4 - Delivery Surfaces

- [ ] Add CLI workflow validation and execution over canonical JSON.
- [ ] Add authenticated REST endpoints as thin adapters over the same services.
- [ ] Add MCP metadata tools without returning large intermediate payloads or
  binary artifacts by default.
- [ ] Add desktop discovery and run inspection only after the headless contract
  and replay behavior are stable.
- [ ] Add packaged acceptance tests on every supported platform.

## Phase 5 - Decision Simulator Handoff

- [ ] Publish a compatibility matrix covering Optees version, workflow contract
  version, capability contracts, and supported transports.
- [ ] Provide fixtures that the simulator can execute through fake, MCP, and
  REST adapters with the same normalized outcome.
- [ ] Preserve simulator ownership of episode time, policy state, virtual
  accounting, and scoring.
- [ ] Define import of a reviewed workflow definition without arbitrary code or
  implicit access to simulator datasets.
- [ ] Verify restart and replay behavior across an interrupted simulator round.

## Explicitly Deferred

- arbitrary user-authored executable steps;
- distributed workflow workers or external queues;
- automatic LLM-driven mutation during an official run;
- public or multi-user workflow hosting;
- real transactions or external operational side effects;
- DP, MDP, bandit, or adaptive-policy semantics inside the generic workflow
  layer;
- robust, stochastic, QP, and MIQP decisions until their atomic capability
  contracts are implemented and independently validated.

## Completion Gate

The first workflow release is complete only when a reviewed definition can be
validated before execution, run through at least two atomic capabilities,
retain every intermediate contract and validation receipt, stop safely on
failure, resume only from a declared idempotent boundary, reproduce or explain
replay divergence, and behave equivalently through its supported transports.
