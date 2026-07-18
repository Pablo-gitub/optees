# Documentation Truth Audit

This audit compares public documentation with the implementation on the
`codex/local-agent-service` branch. It is a working record for Phase 1 of
`docs/DOCUMENTATION_WEBSITE_RELEASE_ROADMAP.md`, not a replacement for the
individual technical documents.

## Verified Baseline

- Application version: `0.8.0` from `src/optees/__init__.py`.
- Registered local-service capabilities: 12 from
  `src/optees/composition/local_agent.py`.
- Public execution surfaces: desktop GUI, headless CLI, authenticated local
  REST API, local MCP stdio server, and experimental Ollama D0 harness.
- Python console entry points: `optees`, `optees-cli`, `optees-server`,
  `optees-mcp`, and `optees-ollama-chat`.
- Native PyInstaller artifacts currently expose the desktop application and
  its internal local-server dispatch, but not a user-facing Ollama chat
  command.

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

1. `docs/ARCHITECTURE.md` still describes the original desktop-oriented layout,
   calls it a six-layer model while showing additional runtime boundaries, and
   contains an obsolete `Actually folders` section.
2. The landing page omits Packing 3D and does not explain the local solver API,
   MCP integration, independent result validation, or agent workflow.
3. Agent setup was split by client. This audit resolves the entry-point problem
   with `docs/AGENTS_SERVICE_CONFIG.md`; protocol-specific implementation
   references remain separate intentionally.
4. The capability inventory was a pre-local-service snapshot whose title
   implied current truth. It is now retained explicitly as
   `docs/local-agent/pre-service-capability-inventory.md`.
5. Public release claims must be checked against final PyInstaller artifacts;
   Python entry points available after `pip install` are not automatically
   available in native installers.

### P1 - Required For Documentation Quality

1. README architecture and agent sections need links to one unified setup
   guide and a concise explanation of REST versus MCP security boundaries.
2. The architecture needs curated Mermaid context, dependency, class,
   sequence, state, and composed-workflow diagrams.
3. The website's numeric workflow count is manually maintained and already
   excludes Packing 3D. Counts should be derived from one reviewed content
   list or updated with an explicit test.
4. Website claims about benchmark validation must distinguish scientific or
   external benchmark datasets from analytic and deterministic regression
   cases.
5. Documentation lacks one audience-oriented index separating end-user,
   contributor, agent-integration, benchmark, and release-maintainer paths.

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
