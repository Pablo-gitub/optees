# Documentation Truth Audit

This audit compares public documentation with the implementation on the
`codex/local-agent-service` branch. It is a working record for Phase 1 of
`docs/DOCUMENTATION_WEBSITE_RELEASE_ROADMAP.md`, not a replacement for the
individual technical documents.

## Verified Baseline

- Application version: `0.9.0` from `src/optees/__init__.py`.
- Registered local-service capabilities: 12 from
  `src/optees/composition/local_agent.py`.
- Public execution surfaces: desktop GUI, headless CLI, authenticated local
  REST API, local MCP stdio server, and experimental Ollama D0 harness.
- Python console entry points: `optees`, `optees-cli`, `optees-server`,
  `optees-mcp`, and `optees-ollama-chat`.
- Native PyInstaller artifacts expose the desktop application, local REST
  service, and MCP stdio companion, but not a user-facing Ollama chat command.

## Capability Coverage

| Capability | Registered | README before audit | Algorithm catalogue before audit | Landing before audit |
| --- | --- | --- | --- | --- |
| `lp.continuous` | Yes | Yes | Yes | Yes |
| `milp.linear` | Yes | Yes | Yes | Yes |
| `knapsack.zero_one` | Yes | Yes | Yes | Yes, grouped |
| `knapsack.bounded` | Yes | Yes | Yes | Yes, grouped |
| `knapsack.unbounded` | Yes | Yes | Yes | Yes, grouped |
| `knapsack.fractional` | Yes | Yes | Yes | Yes, grouped |
| `knapsack.multi_dimensional` | Yes | Yes | Yes | Yes, grouped |
| `nlp.continuous_local` | Yes | Yes | Yes | Yes |
| `graph.shortest_path.dijkstra` | Yes | Yes | Yes | Yes |
| `ml.regression.linear` | Yes | Yes | Yes | Yes |
| `ml.classification.binary_logistic` | Yes | Yes | Yes | Yes |
| `packing.single_container_3d` | Yes | Missing | Missing | Missing |

The README and algorithm catalogue omissions are corrected in the same audit
block. Landing-page correction belongs to Phase 3 because it also requires a
new screenshot, responsive layout verification, translations, and updated
feature counts.

## Findings

### P0 - Must Be Corrected Before The Next Public Release

1. Resolved: `docs/ARCHITECTURE.md` now describes the shared desktop and local
   solver platform, current source ownership, runtime boundaries, and extension
   points.
2. The landing page omits Packing 3D and does not explain the local solver API,
   MCP integration, independent result validation, or agent workflow.
3. Agent setup was split by client. This audit resolves the entry-point problem
   with `docs/AGENTS_SERVICE_CONFIG.md`; protocol-specific implementation
   references remain separate intentionally.
4. The capability inventory was a pre-local-service snapshot whose title
   implied current truth. It is now retained explicitly as
   `docs/local-agent/pre-service-capability-inventory.md`.
5. Resolved for MCP: release CI initializes and calls capability discovery on
   the packaged companion for every native platform. Other Python entry points
   still require explicit packaging and artifact-level acceptance.

### P1 - Required For Documentation Quality

1. Resolved: README architecture and agent sections link to the unified setup
   guide and distinguish REST loopback from private MCP stdio.
2. Resolved: `docs/ARCHITECTURE.md` now documents the current runtime with
   curated Mermaid context, dependency, class, sequence, state, transport, and
   composed-workflow diagrams.
3. The website's numeric workflow count is manually maintained and already
   excludes Packing 3D. Counts should be derived from one reviewed content
   list or updated with an explicit test.
4. Website claims about benchmark validation must distinguish scientific or
   external benchmark datasets from analytic and deterministic regression
   cases.
5. Resolved: `docs/README.md` provides audience-oriented paths for end users,
   contributors, agent integrators, benchmark authors, and release maintainers.

### P2 - Public Demonstration Work

1. Existing Claude Cowork outputs prove a small vertical slice but are not a
   broad agent benchmark.
2. A visually strong company demonstration needs a deterministic data
   generator, frozen prompts, hidden review reference, run metadata, and a
   scoring rubric before its output is suitable for promotional use.
3. A second agent-focused landing page should follow reviewed evidence rather
   than precede it.

## Immediate Corrections In This Audit Block

- Add Single-container 3D Packing to the README workflow table.
- Add Single-container 3D Packing to the implemented algorithm catalogue.
- Promote the local REST/MCP solver platform and agent workflow in the README
  headline, opening explanation, value proposition, and architecture flow.
- Link this audit and its roadmap from the project roadmap.
- Replace the Claude-only entry guide with a shared agent-service guide.
- Rename the historical capability inventory and update references.
- Add an audience-oriented documentation index.

## Validation Checklist

- [x] Capability IDs checked against `composition/local_agent.py`.
- [x] Application version checked against `src/optees/__init__.py`.
- [x] Python entry points checked against `pyproject.toml`.
- [x] README, algorithm catalogue, architecture, datasets, current capability
  inventory, and landing copy inspected.
- [x] Scientific/external benchmark claims distinguished from analytic and
  deterministic reference cases in the reviewed primary documents.
- [x] Internal Markdown link targets validated after the unified agent guide
  rename.
- [ ] Native package behavior validated on final platform artifacts.
- [ ] Landing screenshots and bilingual copy validated after Phase 3.
