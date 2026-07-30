# Sequential Decision Policy Benchmark Roadmap

## Purpose

This roadmap defines a domain-neutral benchmark for comparing repeatable
decision policies under changing observations and uncertainty.

Every policy starts with the same virtual resources, receives the same
information at the same knowledge time, uses frozen rules or Optees workflows,
and produces decisions that are evaluated only after later observations become
available. The primary score is the final value of the resources expressed in
one declared reference unit. Additional metrics explain how that value was
obtained; they do not silently alter the winner.

The benchmark is an Optees demonstration and validation environment, not a
domain-specific product. Concrete datasets and execution rules belong to
replaceable adapters. Public documentation must describe the mathematical
experiment rather than imply operational advice for any particular industry.

## Questions The Benchmark Must Answer

- Can atomic Optees capabilities be composed into useful sequential policies?
- Does uncertainty-aware optimization outperform point-estimate decisions?
- When does a conservative policy sacrifice value, and when does it prevent
  severe loss?
- How much do transaction or transition costs change the preferred decision?
- Can a frozen workflow be executed repeatedly by a simple client without a
  frontier model?
- Can every decision be reproduced from the information available at that
  moment?
- Do lower predictive errors result in better decisions, or only in better
  forecasts?

## Product Boundary

### Optees Responsibilities

Optees provides:

- versioned forecasting, optimization, and validation capabilities;
- point forecasts and, when implemented, calibrated uncertainty outputs;
- deterministic LP/MILP and uncertainty-aware optimization;
- result artifacts, reports, and provenance;
- later, registered workflows, an experiment ledger, and ex-post evaluation.

### Benchmark Harness Responsibilities

The harness provides:

- a replaceable dataset adapter;
- virtual resource accounts and domain execution rules;
- a deterministic clock and observation schedule;
- application of decisions to later observed values;
- reference-unit valuation;
- leaderboards, comparisons, and benchmark exports;
- isolation between competing policies.

### Agent Responsibilities

An optional agent may:

- design a candidate policy;
- propose mappings between capability contracts;
- explain results and assumptions;
- propose a new workflow version after an explicit review trigger.

Routine benchmark execution must not require an agent once a policy is frozen.
An agent never performs authoritative accounting, scoring, or mathematical
validation.

## Core Concepts

### Policy

A policy is an immutable, versioned decision procedure. It declares:

- required observations and their schemas;
- forecasting method and parameters, when applicable;
- transformations into a decision model;
- capability identifiers and contract versions;
- objective priorities and risk treatment;
- allowed decisions and hard constraints;
- behavior when data, validation, or solving fails.

### Episode

An episode is one complete competition over a frozen time interval, dataset,
initial state, and rule set. All policies in an episode receive identical
eligible information.

### Decision Round

A round contains:

1. the state before the decision;
2. observations available at the knowledge cutoff;
3. capability calls, mappings, and validations;
4. the proposed and accepted decision;
5. the later observation used to evaluate it;
6. the resulting state and reference value.

### Virtual Resources

Resources are generic quantities held by a policy. An adapter defines how they
are acquired, exchanged, consumed, produced, or valued. All policies begin with
the same declared resources.

### Primary Score

At round \(t\), the harness computes:

\[
V_t = C_t + \sum_i q_{i,t} p_{i,t} - K_t
\]

where:

- \(C_t\) is unallocated value in the reference unit;
- \(q_{i,t}\) is the quantity of resource \(i\);
- \(p_{i,t}\) is its declared valuation at time \(t\);
- \(K_t\) contains realized transition and operating costs.

The primary final score is \(V_T\), or equivalently its return relative to the
common initial value. Daily valuation is mark-to-model under the frozen adapter
rules; it does not imply forced liquidation or transition at every round.

## Candidate Policy Families

The benchmark should begin with policies that isolate one modeling decision at
a time:

1. **Static baseline**: retain the initial allocation.
2. **Reactive baseline**: use the most recent observation without forecasting.
3. **Point forecast and net-value optimization**.
4. **Point forecast with a hard transition-count limit**.
5. **Point forecast with explicit transition costs and an additional
   sparsity penalty**.
6. **Risk-adjusted point forecast** using a declared uncertainty proxy.
7. **Robust max-min policy** over bounded scenarios.
8. **Expected-value and CVaR policy** over weighted scenarios.

Not all families are currently implementable. A policy may enter an official
episode only after all of its required Optees contracts and validators are
available and frozen.

## Fairness And Anti-Leakage Rules

Every episode freezes:

- initial resources and reference unit;
- observation universe and time interval;
- knowledge cutoff and decision deadline;
- execution and valuation rules;
- transition costs and capacity limits;
- divisibility, borrowing, and negative-position rules;
- missing-data and failed-decision behavior;
- all policy versions and parameters.

Every record distinguishes:

- **event time**: when an observation occurred;
- **knowledge time**: when a policy could use it;
- **execution time**: when the policy ran;
- **effective time**: when its decision took effect.

No policy may be tuned on the private evaluation interval. Exploratory,
calibration, public test, private holdout, and forward episodes remain separate.

## Metrics

### Primary Ranking

- final reference value;
- total return from the common initial value.

### Explanatory Metrics

- maximum drawdown;
- value volatility;
- worst round result;
- number and total cost of transitions;
- turnover or resource churn;
- constraint violations and rejected decisions;
- forecast MAE, RMSE, MASE, and interval coverage where applicable;
- decision regret against a declared comparator;
- runtime, tool calls, token use, and validation failures.

Explanatory metrics must not be combined into an undocumented synthetic score.
Separate leaderboards may compare value, risk-adjusted performance, forecast
quality, or operational cost.

## Missing Optees Foundations

The first simple benchmark can use the existing forecasting and generic MILP
capabilities. More complete comparisons depend on:

- [ ] calibrated forecast intervals, quantiles, or scenario generation;
- [ ] scenario-aware robust max-min optimization;
- [ ] expected-value and CVaR optimization contracts;
- [ ] generic ex-post forecast and decision evaluation;
- [ ] the Workflow Registry and Experiment Ledger defined in
  `docs/OPTIMIZATION_WORKFLOWS_ROADMAP.md`.

Game theory, deep learning, distributed big-data processing, and domain-specific
execution are not prerequisites for the benchmark MVP.

## Delivery Plan

### Phase 0 - Protocol And Threat Model

- [ ] Freeze terminology, boundaries, and the reference-unit score.
- [ ] Define episode, policy, round, observation, decision, and state schemas.
- [ ] Define event, knowledge, execution, and effective time rules.
- [ ] Define allowed dataset licenses and provenance requirements.
- [ ] Threat-model temporal leakage, cross-policy contamination, malformed
  adapters, resource exhaustion, and result cherry-picking.
- [ ] Define when an episode is exploratory or publishable.

### Phase 1 - Deterministic Harness MVP

- [ ] Implement a domain-neutral adapter port.
- [ ] Implement isolated virtual-resource accounts.
- [ ] Apply frozen transitions and valuation rules deterministically.
- [ ] Persist round inputs, accepted decisions, costs, and resulting states.
- [ ] Add a static baseline and a reactive baseline.
- [ ] Export a machine-readable episode record and a human-readable summary.

This phase belongs to the benchmark harness. It must not add domain simulation
logic to the Optees solver core.

### Phase 2 - Existing Optees Vertical Slice

- [ ] Add a point-forecast policy using the released forecasting capability.
- [ ] Add a generic MILP decision policy with explicit transition costs.
- [ ] Add hard transition-count and penalized-transition variants.
- [ ] Record every capability descriptor, payload, result, and validation.
- [ ] Verify identical behavior through direct application use, REST, and MCP.
- [ ] Run frozen analytic cases before any volatile public dataset.

### Phase 3 - Uncertainty-Aware Forecasting

- [ ] Define calibrated interval, quantile, and scenario contracts.
- [ ] Add chronological calibration and coverage evaluation.
- [ ] Distinguish model error, scenario assumptions, and decision risk.
- [ ] Add forecast-fan and calibration artifacts.
- [ ] Freeze deterministic scenario-generation seeds and policies.

### Phase 4 - Robust And Stochastic Decisions

- [ ] Add a robust max-min policy over common scenarios.
- [ ] Add expected-value optimization over weighted scenarios.
- [ ] Add CVaR with declared confidence level and loss semantics.
- [ ] Verify each formulation independently on analytic reference cases.
- [ ] Compare policies using the same scenario package and hard constraints.

### Phase 5 - Workflow Registry And Ledger Integration

- [ ] Register each policy once as an immutable workflow.
- [ ] Execute policies without frontier-model reasoning.
- [ ] Record all rounds in the Experiment Ledger.
- [ ] Add idempotent restart, replay, comparison, promotion, and rollback.
- [ ] Link later observations to prior forecasts and decisions.

### Phase 6 - Benchmark Reporting

- [ ] Produce a leaderboard based on final reference value.
- [ ] Show value trajectories and explanatory risk/cost metrics separately.
- [ ] Display each policy graph, assumptions, validations, and failures.
- [ ] Generate compact PDF/Markdown reports and XLSX/CSV companion data.
- [ ] Produce optional safe static web reports through validated templates.
- [ ] Publish complete episode manifests and checksums.

### Phase 7 - Multi-Dataset And Forward Evaluation

- [ ] Add adapters for multiple structurally different domains.
- [ ] Run growing, declining, stable, seasonal, and highly volatile regimes.
- [ ] Separate public calibration data from private evaluation data.
- [ ] Add a forward episode using observations not available at policy-design
  time.
- [ ] Repeat episodes across different windows and report variance.
- [ ] Publish negative and inconclusive results alongside successful ones.

### Phase 8 - Optional Policy Revision Study

- [ ] Define deterministic degradation triggers.
- [ ] Compare frozen policies with agent-proposed revisions.
- [ ] Validate and approve every new version before it competes.
- [ ] Measure whether revision improves later decisions without retrospective
  leakage.
- [ ] Compare token-heavy redesign with token-free frozen workflow execution.

## Dataset Adapter Requirements

An adapter must declare:

- domain-neutral observation and resource schemas;
- source, license, checksum, and retrieval timestamp;
- calendar and missing-observation policy;
- reference-unit conversion and valuation semantics;
- transition feasibility and cost rules;
- whether values are observed, estimated, delayed, or corrected;
- deterministic handling of unavailable future values.

Domain names may appear in private or illustrative adapters, but core benchmark
contracts, policy identifiers, metrics, and documentation remain generic.

## Verification Strategy

- Analytic accounting cases with hand-computed expected states.
- Property tests for resource conservation and bounded transitions.
- Temporal tests proving no observation is visible before its knowledge time.
- Replay tests producing identical round and final hashes.
- Isolation tests proving one policy cannot read another policy's state.
- Adapter contract tests for missing, duplicated, corrected, and late data.
- Capability contract and independent-validation tests for every Optees call.
- Failure tests for unavailable solvers, invalid decisions, timeouts, and
  incomplete rounds.
- Cross-surface tests for REST and MCP orchestration.
- Visual and tabular regression tests for benchmark reports.

## Publication Standard

An episode may be presented publicly only when:

1. policies, parameters, rules, data provenance, and time cutoffs are frozen;
2. all competitors received identical eligible observations;
3. primary and explanatory metrics are clearly separated;
4. unsuccessful decisions and operational failures remain visible;
5. the benchmark can be replayed from versioned records and checksums;
6. claims are limited to the measured episode and do not imply universal
   superiority or domain-specific operational advice.

## Completion Gate

The benchmark is complete enough for an Optees demonstration when:

1. at least one baseline and three materially different Optees policies run
   over the same frozen episode;
2. the harness maintains isolated virtual resources and computes final value
   deterministically;
3. every forecast and optimization result retains its validation receipt;
4. temporal leakage tests pass;
5. the complete episode can be replayed without an LLM;
6. reports explain value, uncertainty, costs, risk, failures, and assumptions;
7. replacing the dataset adapter does not require changing Optees capability
   implementations or benchmark accounting.
