# Documentation, Website, Release, And Demonstration Roadmap

This roadmap coordinates the documentation and product work required after the
local solver platform refactoring. It keeps four concerns separate:

1. describe the implementation truthfully;
2. explain the architecture clearly;
3. distribute the same behavior through tested native artifacts;
4. demonstrate agent-assisted workflows with reproducible evidence.

Detailed solver, local-service, installer, packing, and benchmark requirements
remain authoritative in their dedicated roadmaps. This document defines their
integration order and the release gates between them.

## Working Rules

- Documentation claims must be derived from registered capabilities, tested
  contracts, and verified packaged behavior.
- A feature implemented only from source must not be advertised as available
  in a native installer.
- Mermaid source in Markdown is authoritative for architecture diagrams.
- Screenshots and benchmark outputs must come from reproducible scenarios, not
  hand-authored mock data presented as solver evidence.
- Large documentation changes, website changes, installer changes, and
  benchmark artifacts use separate commits and review gates.
- When a requirement or platform behavior is uncertain, stop and verify it
  before updating public claims.

## Phase 1 - Documentation Truth Audit

- [x] Create this cross-project roadmap.
- [x] Compare the 12 registered local-service capabilities with `README.md`,
  `docs/ALGORITHMS.md`, `docs/DATASETS.md`, `docs/ARCHITECTURE.md`, and the
  landing-page catalogue.
- [x] Record the initial findings in `docs/DOCUMENTATION_AUDIT.md`.
- [x] Add the omitted single-container 3D Packing workflow to the README and
  concise algorithm catalogue.
- [x] Reframe the README around Optees' dual identity: a desktop workbench for
  people and a local solver platform for scripts and compatible AI agents.
- [x] Replace agent-specific entry documents with one
  `docs/AGENTS_SERVICE_CONFIG.md` configuration guide containing shared setup
  and separate Claude, Ollama, and future OpenAI GPT sections.
- [x] Update every reference to `docs/CLAUDE_CONFIG.md`, then remove the old
  entry document without deleting protocol-specific technical references.
- [x] Reclassify `docs/local-agent/current-capability-inventory.md` as a
  historical pre-service baseline or replace it with a generated/current
  inventory; do not leave a historical snapshot named as current truth.
- [x] Verify source capability counts, application version, entry points,
  status distinctions, and benchmark classifications across the primary
  documentation.
- [ ] Verify source-versus-native-package availability against the final
  Windows, macOS, and Linux artifacts during the distribution acceptance gate.
- [x] Add a compact documentation index with a clear path for users,
  contributors, agent integrators, and release maintainers.
- [x] Run local Markdown link-target validation. External-link availability
  remains a release-network check rather than a local documentation check.

**Exit criterion:** known discrepancies are recorded, immediate capability
omissions and broken internal links are corrected, and every remaining
architecture, website, or native-package discrepancy is assigned to a later
phase with an explicit verification gate.

## Phase 2 - Architecture Documentation And Mermaid

- [x] Rewrite `docs/ARCHITECTURE.md` around the current source tree and runtime
  boundaries instead of the original desktop-only structure.
- [x] Add a system-context diagram covering the user, desktop GUI, CLI, REST,
  MCP, local LLM harness, application services, solver adapters, and external
  numerical engines.
- [x] Add a Clean Architecture dependency diagram with explicit ports and
  adapters.
- [x] Add a curated UML class diagram for `CapabilityRegistry`,
  `OptimizationService`, `LocalJobService`, serializers, validators, and
  registered capability adapters.
- [x] Add the discovery, validation, asynchronous execution, independent
  result validation, and result-retrieval sequence.
- [x] Add a job-state diagram that keeps transport lifecycle separate from
  mathematical status.
- [x] Add REST, MCP stdio, and direct desktop-service runtime diagrams.
- [x] Add a composed-workflow diagram such as forecasting to MILP planning to
  3D Packing, clearly marking agent orchestration as external to atomic solver
  correctness.
- [ ] Verify every Mermaid block through GitHub-compatible rendering or a
  reviewed local Mermaid toolchain. All nine blocks passed local structural
  review; no Mermaid renderer is currently installed in the repository.

**Exit criterion:** a contributor can identify ownership, dependency direction,
execution flow, status boundaries, and extension points without reading the
entire source tree.

## Phase 3 - First Landing-Page Refresh

- [ ] Add single-container 3D Packing to the algorithm catalogue and capture a
  readable application screenshot with non-trivial placements.
- [ ] Present the local solver platform as a primary product capability:
  discovery, versioned schemas, exact validation, asynchronous jobs,
  independent result checks, and local execution.
- [ ] Explain REST loopback and MCP stdio without implying that arbitrary
  hosted agents can access the user's localhost.
- [ ] Distinguish the deterministic Modeling Assistant from optional external
  or local LLM agents.
- [ ] Add a concise `Discover -> Inspect -> Validate -> Solve -> Verify` visual
  flow.
- [ ] Update English and Italian copy, feature counts, screenshots, SEO
  metadata, structured data, `llms.txt`, and sitemap content together.
- [ ] Mark source-only or preview integrations honestly until native-package
  acceptance tests pass.
- [ ] Verify desktop and mobile layouts, accessibility, reduced motion, links,
  and production build output.

**Exit criterion:** the single-page site accurately represents the desktop
workflows and local solver platform available at the intended release commit.

## Phase 4 - Main Integration And Native Distribution

- [ ] Complete the local-service branch documentation and test gates.
- [ ] Merge the stable local solver platform into `main`.
- [ ] Create `codex/native-installers` from the updated `main`.
- [ ] Complete the P0 items in `docs/NATIVE_DISTRIBUTION_ROADMAP.md`, including
  test-gated releases, final-artifact smoke tests, checksum behavior, Windows
  Inno Setup, and truthful macOS/Linux update handoff.
- [ ] Verify that installed artifacts can run a solver and start the packaged
  local service.
- [ ] Merge native-distribution work into `main` only after the acceptance
  matrix is recorded.
- [ ] Publish an application release from the verified commit.
- [ ] Publish the matching landing deployment only after release assets and
  download links are live.

**Exit criterion:** public documentation and downloads describe the same tested
artifact behavior on every supported platform.

## Phase 5 - Local Agent Desktop Continuation

- [ ] Create `codex/local-agent-desktop` from the released `main`; do not
  continue long-lived work on an already merged branch.
- [ ] Implement the Local Ollama desktop module defined in
  `docs/LOCAL_AGENT_SERVICE_ROADMAP.md`.
- [ ] Test and document OpenAI GPT integration only against a verified local
  client or MCP surface, including transport and localhost limitations.
- [ ] Maintain one shared agent-service configuration guide while keeping
  protocol internals in focused technical documents.

## Phase 6 - Complex Synthetic-Company Demonstration

- [ ] Define one coherent fictional company and business decision rather than
  unrelated large worksheets.
- [ ] Generate hundreds of reproducible rows where scale is meaningful, using
  a fixed seed and a checked-in generator.
- [ ] Include a public input workbook with demand history, products, orders,
  resources, inventory, capacities, and packing data as required by the frozen
  scenario.
- [ ] Keep the reviewed formulation, expected invariants, and ground truth out
  of the evaluated agent's working directory during each run.
- [ ] Freeze a direct-solver prompt and a composed-workflow prompt.
- [ ] Record client, model, version, tool configuration, run timestamp,
  transcript policy, and Optees commit.
- [ ] Require the agent to generate an executive presentation and an
  auditable technical report from Optees results.
- [ ] Score mathematical correctness, data fidelity, assumption disclosure,
  tool discipline, reproducibility, and presentation quality separately.
- [ ] Compare an unaided condition with an Optees-assisted condition using the
  same scenario and evaluation rubric.
- [ ] Keep selected outputs only; do not commit every exploratory binary file.

**Exit criterion:** another evaluator can rerun the scenario and distinguish
correct solver use from merely attractive presentation.

## Phase 7 - Agent Integration Page And Public Evidence

- [ ] Add a second landing route only after the complex benchmark has passed
  review.
- [ ] Explain supported clients, local security boundaries, setup, discovery,
  validation, and composed workflows.
- [ ] Publish selected prompt excerpts, result summaries, presentation images,
  architecture diagrams, and methodology links.
- [ ] Avoid presenting a single successful agent run as a general reliability
  claim.
- [ ] Reuse optimized visual assets in the README, landing page, release notes,
  and any public project article.

## Branch And Commit Sequence

1. `codex/local-agent-service`: documentation audit, architecture, first
   landing refresh, and service completion.
2. `main`: merge only after focused and full release gates pass.
3. `codex/native-installers`: installer and update hardening from updated
   `main`.
4. `main`: merge, tag, publish application, then deploy landing.
5. `codex/local-agent-desktop`: packaged local-agent UX.
6. `codex/agent-demo-benchmark`: complex synthetic benchmark and selected
   public evidence.

Recommended commit boundaries:

1. documentation audit and capability corrections;
2. unified agent configuration guide;
3. architecture and Mermaid diagrams;
4. landing content and assets;
5. landing tests and deployment metadata;
6. each native-platform packaging change separately;
7. benchmark generator and protocol before generated artifacts.
