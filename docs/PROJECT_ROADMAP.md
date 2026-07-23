# Optees Project Roadmap

This is the authoritative implementation roadmap for Optees. Specialized
documents keep the detail for a single family, while this page decides the
order in which the product grows.

Related documents:

- `docs/MILP_ROADMAP.md` for MILP-specific completion work;
- `docs/NLP_FEATURE_PLAN.md` for the Phase 1 nonlinear-programming delivery
  checklist;
- `docs/PACKING_LOADING_ROADMAP.md` for the geometric packing and container
  loading horizontal expansion;
- `docs/LOCAL_AGENT_SERVICE_ROADMAP.md` for the shared headless execution
  platform, local API, and future agent-facing contracts;
- `docs/RESULT_ARTIFACTS_REPORTING_ROADMAP.md` for optional result charts,
  tables, 3D exports, and local Markdown/PDF report composition;
- `docs/RESULT_ARTIFACTS_CONTRACT.md` for the frozen artifact inventory,
  lifecycle, limits, errors, and report schema that implementation follows;
- `docs/NATIVE_DISTRIBUTION_ROADMAP.md` for native installers, release CI,
  platform update handoff, and packaged acceptance testing;
- `docs/AGENT_BENCHMARKS.md` for paired experiments measuring whether agents
  formulate and solve synthetic business problems better with Optees;
- `docs/DOCUMENTATION_WEBSITE_RELEASE_ROADMAP.md` for the post-refactoring
  documentation audit, architecture diagrams, landing refresh, release
  coordination, and public demonstration sequence;
- `docs/DATASETS.md` for included scientific datasets;
- `docs/TESTING.md` for the test strategy;
- `docs/RELEASING.md` for build, signing, and tag verification;
- `docs/ALGORITHMS.md` for the concise algorithm catalogue.

## Product Standard

An algorithm family is considered complete enough to be exposed in the
application only when it has:

1. a precise domain model and documented mathematical formulation;
2. a use case and a solver adapter behind a stable port;
3. a versioned JSON format when a structured formulation is appropriate;
4. formulation and solution views that explain both the data and the result;
5. examples, an educational problem-description page, and localized UI text;
6. unit, integration, and presentation tests scaled to the risk of the
   implementation;
7. small reproducible reference cases before exposure in the application;
   external scientific benchmarks when they are available and suitable, and
   before presenting a solver as robust beyond its documented scope.

Exact solvers must distinguish a proven optimum from a feasible incumbent.
Heuristic methods must explicitly state that they return a best-found solution,
not a proof of optimality.

## Delivery Strategy

Optees will use a **vertical-first, benchmark-hardening, then coordinated-depth**
strategy.

- Every new algorithm first receives a usable vertical slice and mandatory
  deterministic reference tests. A screen without a verified solver is never
  considered an MVP.
- Deliver one complete vertical slice for each major product section:
  Nonlinear Programming, Graph Theory, educational AI & Machine Learning, and
  Heuristics & Metaheuristics.
- After those slices, run a benchmark-hardening pass: add external scientific
  datasets where a redistributable corpus and published outcomes are suitable,
  retain checksums and provenance, and separate routine CI cases from slow
  performance cases.
- Only then expand established families horizontally, adding comparable depth
  to LP/MILP, NLP, Graphs, and Heuristics.

This avoids three bad outcomes: an application with only a very deep Linear
Programming section, many empty categories, or attractive workflows that have
no regression evidence. Existing, low-friction benchmark integrations may be
added during a vertical slice; a difficult external corpus does not block an
otherwise tested first workflow, but it remains an explicit hardening item.

Packing & Loading is a deliberate exception to the default sequencing. A
concrete operational use case justifies one focused horizontal expansion before
the Heuristics slice and generic MILP minimax work. The exception does not lower
the product standard: the first geometric workflow still requires an exact
contract, deterministic references, benchmark evidence, and honest solver
status reporting.

## Current Baseline

### Linear Programming

- Continuous LP model with variables, bounds, objective, and constraints.
- SciPy/HiGHS adapter, JSON import/export, and core statuses.
- Multiple-optima analysis through optimal-face auxiliary LPs.
- Educational pages, solution charts, synthetic tests, and LP Netlib cases.

### Mixed-Integer Linear Programming

- Continuous, integer, and binary variables with binary normalization to
  bounds `[0, 1]`.
- OR-Tools adapter, JSON import/export, time limit, MIP gap, and `Feasible`
  versus `NotSolved` status.
- Formulation UI, educational pages, threshold/piecewise examples, and MIPLIB
  regression data.
- Remaining family-specific work is tracked in `docs/MILP_ROADMAP.md`.

### Knapsack

- 0/1, Bounded, Unbounded, Fractional, and Multi-dimensional variants.
- Variant-aware formulation UI, JSON import, dedicated solvers, solution
  summaries, tables, charts, Burkardt 0/1 cases, OR-Library multi-dimensional
  benchmark cases, and documented Bounded/Unbounded reference cases.

### Modeling Assistant

- Fully local, deterministic, rule-based solver recommendation.
- English and Italian natural-language prompts, including expert and beginner
  wording for Regression and Binary Classification.
- Conservative LP, MILP, Knapsack, Regression, and Binary Classification JSON
  drafting validated by the existing importers before the UI may load a draft.
  Regression and Classification require explicitly named columns and
  pipe-separated rows; prose-only descriptions are recommendation-only.

### Nonlinear Programming

- Continuous scalar objectives with a safe expression language, optional box
  bounds, an explicit feasible initial point, and BFGS, Nelder-Mead, or
  L-BFGS-B as appropriate.
- Numerical solution view with candidate status, objective history, and
  bounded 2D/3D objective visualizations.
- Analytic reference cases for Rosenbrock, Himmelblau, bounded quadratic, and
  nonlinear maximization. These verify a documented local-search contract,
  not global optimality.

### Graph Theory

- Directed or undirected finite weighted graph model with JSON import/export.
- Deterministic Dijkstra shortest path for non-negative weights, including
  route reconstruction, settled-node trace, and highlighted graph result.
- Deterministic graph regressions and a reusable delivery-route example;
  external graph benchmark integration remains a hardening item.

### Educational AI & Machine Learning

- Local numeric linear regression with OLS and Ridge estimators.
- Explicit reproducible train/test split, coefficients, MAE/MSE/RMSE/R-squared,
  residual table, one-feature fit visualization, and versioned JSON import.
- Analytic affine reference cases verify the numerical contract. This workflow
  teaches a predictive fit and its limits; it does not claim causality or
  future performance.
- Local binary classification with logistic regression, stratified train/test
  splits, training-only feature standardization, accuracy/precision/recall/F1,
  confusion matrices, and an optional 2D decision-boundary visualization.

### Product Delivery

- Desktop release workflow and packaged-build update checks through GitHub
  Releases.
- React/Vite website lives under `apps/website/` and remains a separate
  deployment track within this repository. Firebase Hosting configuration is
  prepared; the Firebase project association and canonical production domain
  remain local deployment choices.

## Phased Implementation Plan

### Phase 0 - Consolidate The Current Baseline

**Completed for `0.4.0`.** The Modeling Assistant baseline is committed;
Knapsack coverage now includes documented reference cases and OR-Library
regression data; release metadata, runtime dependencies, bundle assets, and
documentation were verified together.

The macOS bundle was built from the repository, checked for its versioned
`Info.plist`, i18n/document/icon assets, ad-hoc signature, and an offscreen
startup. The GitHub workflow remains responsible for clean builds on the other
two supported platforms and for Developer ID signing/notarization when secrets
are configured.

### Phase 1 - Nonlinear Programming: First Vertical Slice

**Released in `0.5.0`.** The full test suite, macOS bundle asset inspection,
code-signature check, and offscreen application startup passed for this slice.

The sequential implementation contract, safety rules, test matrix, and commit
boundaries are maintained in `docs/NLP_FEATURE_PLAN.md`.

- Domain model for continuous variables, bounds, a nonlinear objective, and
  safe structured function representation. Do not evaluate arbitrary Python
  expressions entered by users.
- Unconstrained and bound-constrained minimization using maintained SciPy
  methods such as BFGS, Nelder-Mead, and L-BFGS-B where applicable.
- Formulation view for variables, bounds, initial point, method, and stopping
  options.
- Solution view showing status, candidate point, objective, iterations,
  termination reason, and convergence history.
- Bounded educational visualization: contour map and 3D objective surface for
  two variables, and an honest candidate-centred 2D slice for three variables.
- Educational examples and benchmark tests: Rosenbrock, Himmelblau, and small
  nonlinear quadratics.

The included NLP cases are analytic references. A redistributable external NLP
benchmark corpus remains a benchmark-hardening item before global-search or
broader robustness claims are introduced.

**Explicitly deferred:** nonlinear constraints, least squares, quadratic
programming, nonlinear minimax, and global optimization.

### Phase 2 - Graph Theory: First Vertical Slice

**Implemented and verified locally.** The first graph workflow is Dijkstra
shortest path because it has a clear model, a visual result, and a concise
correctness argument.

- Directed/undirected weighted graph model and versioned JSON import/export.
- Graph editor with vertices, arcs, weights, source, and destination.
- Local deterministic Dijkstra for non-negative weights, with path
  reconstruction and explanation of settled nodes and total cost.
- Solution view that highlights the selected route over the input graph.
- Domain, JSON, use-case, and presentation tests for directed, undirected,
  reachable, unreachable, and invalid-weight cases.

An external graph benchmark corpus is intentionally deferred to Phase 3.5.
The current hand-built cases are deterministic regressions, not a claim of
scientific benchmark coverage.

**Explicitly deferred:** negative weights, all-pairs shortest paths, spanning
trees, flow, matching, and TSP.

### Phase 3 - AI & Machine Learning: Educational Foundations

Educational machine learning is a separate local-learning section: it must not
be presented as AutoML, an LLM provider, or a replacement for the Modeling
Assistant.

The delivery order is deliberately sequential.

**Regression and binary classification are implemented and verified locally.**
The regression workflow provides OLS and Ridge for finite numeric tabular data, a deterministic
train/test split, fixed random seed, selected feature and target names,
MAE/MSE/RMSE/R-squared, residuals, a one-feature fit chart, localized teaching
pages, versioned JSON import, and analytic affine reference cases. The result
view explicitly separates training from held-out test observations and does
not present a predictive fit as a causal conclusion. The headless result now
has an independent arithmetic validator for parameters, predictions, residuals,
split accounting, and metrics. This does not make the current random split
valid for time-ordered forecasting.

The binary-classification workflow provides local logistic regression for
finite numeric features and exactly two labels, a deterministic stratified
split, training-only standardization, accuracy/precision/recall/F1, confusion
matrices, per-row probabilities, an optional 2D decision boundary, localized
teaching pages, versioned JSON import, deterministic reference cases, and
matched English/Italian assistant prompts. The assistant can draft a dataset
only from explicitly declared columns and pipe-separated rows, validates it
through the importer, and never invents observations from prose. This workflow
must not be treated as a fairness, causality, or deployment claim.

The remaining work is:

1. **Forecasting as a separate capability:** define a versioned time-series
   contract with ordered timestamps, chronological or rolling-origin
   evaluation, explicit forecast horizon, uncertainty intervals, residual
   diagnostics, and leakage safeguards. Do not silently reinterpret the
   existing tabular regression contract as forecasting.
2. **Repeated-model ergonomics:** design bounded batch/fan-out execution for
   the same validated capability over multiple groups while preserving one
   result and validation report per model.
3. **Clustering within the AI family:** local unsupervised clustering with k-means,
   user-selected `k`, reproducible seed, feature scaling made visible, inertia
   and silhouette diagnostics, and 2D/3D plots only for the selected displayed
   dimensions.
4. **Classification hardening:** add a suitable redistributable external
   benchmark only after its source, evaluation protocol, expected properties,
   license, and CI budget are reviewed. Keep this distinct from claims about
   fairness or production readiness.

Every workflow must keep the same product standard as an optimizer: a domain
model, a stable port and adapter, versioned structured import when appropriate,
localized formulation/result pages, examples, and deterministic tests. The
first data sources should be small, redistributable reference datasets with
documented expected properties; larger benchmark suites are a later hardening
activity. Model training remains entirely local.

**Explicitly deferred:** arbitrary model selection, neural networks, LLM
providers, automatic feature engineering, opaque scoring, and claims that a
single metric is sufficient for a real decision.

### Phase 3.25 - Packing & Loading Priority Expansion

A concrete operational use case makes Packing & Loading the next focused
horizontal expansion before generic MILP minimax work. It remains an educational
Optees family with dedicated formulation and solution views, while its first
exact implementations explicitly teach their underlying MILP model.

The implementation starts with orthogonal Single-container 3D Packing, then
adds Multi-container 3D Packing, human-guided re-optimization, industrial
constraints and heuristic comparators, and finally non-geometric
Multi-container Capacity Allocation. The eventual UI orders the simpler
capacity workflow before the geometric workflows even though it is implemented
later.

The complete mathematical scope, JSON contracts, UI requirements, solver
status semantics, performance policy, and sequential checklist are maintained
in `docs/PACKING_LOADING_ROADMAP.md`.

The declared Phase 1 orthogonal single-container scope is implemented: exact
MILP solving, optional simple-gravity post-processing, interactive 3D results,
cooperative cancellation, structural complexity warnings, and an OR-Library
benchmark source with a bounded CI subset. Physical stability and full-size
benchmark performance remain explicitly outside that first-phase contract.

### Phase 3.4 - Local Solver Platform

Before adding another major algorithm family, expose the capabilities already
implemented through a stable application facade, headless CLI, and optional
authenticated localhost service. This is a cross-cutting refactoring and
product capability: it reuses existing domain models, JSON importers, use cases,
ports, adapters, and tests rather than creating a second solver backend.

The MVP first inventories current contracts, defines versioned result codecs,
adds a capability registry, proves Qt-independent execution, migrates existing
capabilities, and only then adds the job API and desktop server controls.
Independent result validation, semantic modeling safeguards, agent-oriented
documentation, MCP, and composite optimization workflows follow in explicit
post-MVP phases.

An early local-agent proof is intentionally inserted after the first complete
LP validator instead of waiting for the final MCP phase. A small Ollama harness
will exercise discovery, validation, asynchronous execution, independent result
validation, and explanation as one reproducible loop. A minimal MCP vertical
slice follows over the same allowlisted tool facade; the later MCP phase remains
responsible for hardening, complete capability coverage, packaging, guidance,
and client compatibility.

The sequential checklist and API boundaries are maintained in
`docs/LOCAL_AGENT_SERVICE_ROADMAP.md`.

The next product-facing step is a packaged Local Agent desktop module using
Ollama on the same computer. Source checkouts and normal Python installations
already expose the experimental `optees.ollama_chat` harness, but native
PyInstaller releases do not expose that console entry point. The desktop module
will reuse the validated application services directly, add model discovery
and bounded background execution, and make the workflow available without a
terminal, REST token, or source tree. OpenAI GPT client configuration and a
matching capability-discovery test remain a later compatibility task until a
specific supported local integration surface has been selected and verified.

After stable capability contracts and agent-facing adapters exist, paired
experimental benchmarks will compare the same frozen synthetic-company
scenarios under unaided and Optees-assisted conditions. They will report model
validity, feasibility, objective quality, unsupported assumptions, tool use,
and explanation accuracy separately. The protocol and repository organization
are maintained in `docs/AGENT_BENCHMARKS.md`.

### Phase 3.45 - Native Distribution And Update Hardening

After the local solver platform is merged, release engineering takes priority
over another functional expansion. Windows must gain a real per-user installer;
macOS and Linux must retain explicit native or portable contracts; and the
updater must distinguish a verified download, an installation handoff, and a
confirmed installed update.

The work also introduces a test-gated release workflow, pinned packaging inputs,
final-artifact solver smoke tests, fail-closed checksum verification, and a
recorded clean-machine acceptance matrix. Implementation starts from `main` on
`codex/native-installers`. The sequential plan and platform exit criteria are
maintained in `docs/NATIVE_DISTRIBUTION_ROADMAP.md`.

### Phase 3.5 - Heuristics & Metaheuristics: First Vertical Slice

Heuristics deserves its own product section. It is a family of search methods,
not a mathematical-programming model, and it must make approximation and
reproducibility visible to the user.

The first vertical slice should use TSP after the Graph foundation exists:

- graph-tour model and a small TSP formulation view;
- deterministic constructive baseline: Nearest Neighbour;
- local improvement baseline: 2-opt;
- solution view with route, total distance, iterations, elapsed time, and
  best-so-far trace;
- fixed random seed and explicit run budget for every non-deterministic method;
- comparison against an exact result only for small instances where an exact
  baseline is practical.

The first true metaheuristic should be Simulated Annealing. Genetic Algorithm,
Tabu Search, Ant Colony Optimization, and other methods follow only after the
common run-reporting contract is stable.

**Explicitly deferred:** a generic "one metaheuristic for every problem"
abstraction. Each supported problem needs a valid encoding, neighbourhood,
feasibility repair, and objective evaluation contract.

### Phase 4 - Scientific Benchmark Hardening

After the first AI/ML and Heuristics workflows exist, consolidate scientific
benchmark evidence before broadening the families further.

- Keep the LPnetlib, MIPLIB, Burkardt, and OR-Library adapters reproducible.
- Evaluate and document a redistributable external corpus for continuous NLP;
  local methods must be assessed against their intended basin or local-search
  contract, not falsely graded as global optimizers.
- Add Graph and TSP sources with known outcomes, source metadata, checksums
  where applicable, and a clearly bounded CI selection.
- Keep toy and analytic cases in normal CI; mark heavier scientific regression
  and performance cases explicitly.

### Phase 5 - Coordinated Family Expansion

Once the current vertical slices have one complete workflow, deepen them in an
order that reuses the new foundations.

| Family | Next capabilities |
| --- | --- |
| LP / MILP | Dedicated `MILPSolutionView`, MPS import adapter, threshold-model wizard, linear minimax/maximin, Chebyshev goal programming, and min-max regret where the model is linear. |
| Knapsack | Multiple-choice Knapsack, additional benchmark suites, and heuristic-versus-exact comparison for instances where DP or MILP becomes expensive. |
| Packing & Loading | Orthogonal single- and multi-container 3D packing, interactive refinement, industrial constraints, heuristic comparison, and capacity-only allocation. |
| NLP | Nonlinear constraints, least squares, quadratic programming, nonlinear minimax, and global methods such as differential evolution. |
| Graph Theory | Bellman-Ford, minimum spanning tree, max flow/min cut, matching, and exact/heuristic TSP comparison. |
| AI & Machine Learning | Regularization and validation improvements after regression and binary classification, then clustering diagnostics; each expansion keeps local, reproducible data handling. |
| Heuristics | Simulated Annealing, then problem-specific Genetic Algorithm or Tabu Search; every result keeps seed, budget, incumbent trace, and feasibility diagnostics. |
| Scheduling | Parallel-machine makespan first, using a MILP formulation and later heuristic comparators; time-indexed and sequence-dependent models follow only with dedicated visualizations. |
| Robust & Stochastic Optimization | Explicit scenario model, min-max regret, then newsvendor and revenue-management workflows with uncertainty assumptions visible in the UI. |

### Phase 6 - Modeling Assistant: Structured Guidance

Extend the assistant only after the target formulation pages exist. Regression
and Binary Classification already accept conservative, importer-validated
drafts from explicit table notation; this phase must retain that safety bar.

- Ask targeted follow-up questions instead of guessing omitted data.
- Draft and validate structured JSON for the newly implemented families.
- Explain optimal, infeasible, unbounded, and best-found heuristic results.
- Suggest modeling corrections while preserving the rule that no user model is
  overwritten without confirmation.
- Evaluate optional local or cloud LLM providers only through a benchmark suite
  that measures classification, drafting validity, safety, and reproducibility.
  No LLM provider is required for Optees.

### Website Delivery

- Use the website to document real released capabilities, benchmark evidence,
  screenshots, downloads, and algorithm limitations; it must not advertise
  unfinished families as available.
- Publish the static React/Vite build through Firebase Hosting only after a
  preview deploy verifies the selected canonical URL, SEO files, language
  switching, and release download links.

## Cross-Family Concepts

### Min-Max, Max-Min, And Regret

Min-max is not a standalone solver category. It belongs to the family that
defines the objective and constraints:

| Context | Correct placement |
| --- | --- |
| Linear continuous or mixed-integer models | LP/MILP, often through an epigraph variable or a Chebyshev goal-programming formulation. |
| Nonlinear objective or constraints | NLP. |
| Uncertain scenarios and regret | Robust Optimization models, initially documented within the Modeling Assistant and later exposed as a dedicated family/workflow. |
| Game trees | Graph Theory / AI, using minimax and alpha-beta pruning. |

Max-min follows the same rule: it is a modelling objective, not an algorithm
family by itself.

## Benchmark And Documentation Policy

- Every imported dataset records source, license or usage notes, file format,
  expected result, and the tests that consume it in `docs/DATASETS.md`.
- Small deterministic cases belong in the standard suite; large scientific cases
  may use `slow` markers.
- Each educational page must distinguish exact algorithms, numerical local
  optimization, and heuristics.
- `docs/PROJECT_ROADMAP.md` owns sequencing; specialized documents own detailed
  implementation checklists.

## Website Delivery Track

The website remains under `apps/website/`, built with React and Vite. It has a
separate publication workflow from the desktop application, but it follows the
same release evidence: localized content, tested screenshots, accurate download
links, SEO metadata, and no claims for features that have not shipped.
