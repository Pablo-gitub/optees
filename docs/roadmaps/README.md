# Optees Roadmaps

[Project roadmap](project.md) is authoritative for product sequencing.
Specialized roadmaps own detailed delivery checklists. Their location remains
stable when delivery state changes.

## Delivery States

- **Planned:** accepted scope that has not started.
- **In progress:** active implementation remains.
- **Closing:** the principal implementation is shipped, with bounded handoff or
  product-completion work remaining.
- **Maintenance:** the baseline is shipped and the document primarily tracks
  hardening or later extensions.
- **Completed:** no active delivery work remains; historical plans may then be
  moved to the archive.
- **Superseded:** replaced by another authoritative document.

## Current Register

| Roadmap | State | Current boundary |
| --- | --- | --- |
| [Project](project.md) | In progress | Authoritative sequencing across all families |
| [Forecasting](forecasting.md) | Closing | Engine and desktop workflow shipped; final handoff and desktop reporting remain |
| [Local agent platform](local-agent-platform.md) | In progress | MVP shipped; validator breadth, semantic guidance, desktop agent work, and evidence remain |
| [Result artifacts and reporting](result-artifacts-and-reporting.md) | In progress | Headless workflow shipped; remaining product and scalability work continues |
| [Native distribution](native-distribution.md) | In progress | Native packaging exists; acceptance, signing, self-test, and updater hardening remain |
| [Packing and loading](packing-and-loading.md) | In progress | Existing vertical slice with later expansion tracked |
| [MILP](milp.md) | In progress | Family completion and hardening work remains |
| [NLP](nlp.md) | Maintenance | First vertical slice shipped; deferred extensions remain |
| [Graph](graph.md) | Maintenance | First vertical slice shipped; deferred algorithms remain |
| [Composite optimization workflows](optimization-workflows.md) | Planned | Contract decisions before any application-owned workflow executor |
| [Decision Simulator case-study expansion](case-study/ROADMAP.md) | In progress | Parallel evidence track: QP, robust scenarios, forecasting depth, MIQP, and Registry |
| [Convex QP contract decision](case-study/01-qp-contract-decision.md) | Completed | Contract decision frozen; gate QP-C achieved |
| [Documentation, website, and release](documentation-website-release.md) | In progress | Coordinated public documentation and release work |

The register is a navigation summary. When it conflicts with a roadmap's
detailed checklist, update both in the same work unit rather than treating this
table as a substitute for the roadmap.
