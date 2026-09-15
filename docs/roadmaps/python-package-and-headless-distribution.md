# Python Package And Headless Distribution Roadmap

## Document Status

- **State:** planned
- **Workstream:** `DIST-PY`
- **Evidence source:** operational use of the Classification capability from
  Python, the CLI, and a native Optees installation
- **Current limitation:** PySide6 is a mandatory base dependency, Python
  distributions are not published as release assets or on PyPI, and native
  packages omit `optees-cli`
- **Implementation authorization:** none; this document freezes sequence and
  gates, not package publication
- **Related roadmap:** `native-distribution.md`

## Goal

Make the same versioned Optees core usable in headless Python environments and
native installations without forcing an unused Qt dependency or a source-tree
checkout. Preserve one product version across Python distributions and native
applications while testing each installation profile independently.

## Product Boundary

This track changes distribution, dependency profiles, entry points, release
assets, and documentation. It must not fork the mathematical core, create a
second capability registry, or make headless and desktop installations expose
different solver semantics.

The first publication target is a wheel and source distribution attached to a
GitHub release. PyPI publication follows only after package-name ownership,
trusted publishing, metadata, rollback/yank procedure, and clean-install
evidence are reviewed.

## Target Installation Profiles

| Profile | Required content | Excluded unless requested |
| --- | --- | --- |
| Core Python | domain, application, codecs, solver adapters, CLI | PySide6, FastAPI, MCP SDK |
| Desktop | core plus PySide6 and graphical runtime | REST and MCP dependencies |
| Local service | core plus FastAPI, Pydantic and Uvicorn | PySide6 |
| MCP | core plus MCP SDK | PySide6 and REST server |
| Plotting | core plus headless Matplotlib rendering | PySide6 |
| Development | selected runtime profiles plus tests and lint | release tooling unless explicitly installed |

Optional extras must compose. Installing desktop, local service, MCP, and
plotting together must produce the same complete environment used by native
release builds.

## Phase 0 — Dependency And Import Audit (`DIST-PY-C`)

- [ ] Inventory imports reachable from `import optees`, `optees-cli`,
  `optees-server`, `optees-mcp`, and the desktop entry point.
- [ ] Prove that headless capability discovery and one small solve do not
  import PySide6.
- [ ] Freeze base dependencies and the `desktop`, `local-service`, `mcp`,
  `plot`, `test`, and `dev` extras.
- [ ] Decide whether convenience extras such as `all` are justified without
  becoming the documented default.
- [ ] Record platform wheel availability and Python constraints for every
  compiled numerical dependency.
- [ ] Reject a split that changes capability IDs, schemas, defaults, result
  codecs, or validation behavior between installation profiles.

**Gate `DIST-PY-C`:** the dependency graph and installation-profile contract
are reviewed before `pyproject.toml` changes.

## Phase 1 — Buildable Python Distributions (`DIST-PY-W`)

- [ ] Move PySide6 out of mandatory base dependencies and into the reviewed
  desktop extra.
- [ ] Build wheel and source distribution from a clean checkout using the
  canonical version from `optees.__version__`.
- [ ] Inspect wheel contents for assets, schemas, licenses, accidental caches,
  credentials, absolute paths, and generated development files.
- [ ] Install the wheel into isolated core, desktop, local-service, MCP, and
  combined environments.
- [ ] Exercise capability discovery, CLI JSON discipline, one validated solve,
  optional imports, and explicit missing-extra diagnostics in each profile.
- [ ] Add a test that the core wheel does not depend on or import PySide6.
- [ ] Verify that the source distribution can reproduce the wheel without a
  repository checkout.

**Gate `DIST-PY-W`:** inspected wheel and source distribution install and pass
their bounded acceptance matrix in clean environments.

## Phase 2 — Native CLI Companion (`DIST-CLI`)

- [ ] Add a dedicated PyInstaller CLI entry selected by source path rather than
  positional analysis-table assumptions.
- [ ] Package `optees-cli.exe` on Windows and `optees-cli` inside macOS and
  Linux payloads.
- [ ] Register the Debian launcher and define an explicit AppImage dispatch
  argument without changing normal GUI startup.
- [ ] Preserve stdout as one JSON document and stderr as bounded diagnostics.
- [ ] Smoke-test capability discovery, validation, and one file-backed solve
  against every final native artifact.
- [ ] Verify exit codes for invalid input, unavailable capability, infeasible,
  unbounded, cancelled, and technical failure outcomes.

**Gate `DIST-CLI`:** a user without Python can execute the same CLI contract
from every supported native package.

## Phase 3 — Release Assets And PyPI Decision (`DIST-PUBLISH`)

- [ ] Attach wheel and source distribution to a release only after the tagged
  commit passes Python-distribution acceptance.
- [ ] Add their hashes to the release checksum inventory.
- [ ] Verify installation by downloading the published assets rather than
  reusing local build output.
- [ ] Audit ownership and possible naming confusion before reserving or using
  the `optees` PyPI project name.
- [ ] Configure PyPI Trusted Publishing with a narrowly scoped release
  environment; do not store long-lived upload tokens in the repository.
- [ ] Publish a release candidate first and verify version, metadata, files,
  dependencies, CLI entry points, and import behavior from the index.
- [ ] Document yank and recovery behavior without reusing or silently replacing
  an immutable version.

**Gate `DIST-PUBLISH`:** GitHub assets are reproducible and verified; PyPI is
optional until the separate ownership and trusted-publishing gate passes.

## Phase 4 — Documentation And Handoff (`DIST-DOC`)

- [ ] Add Python installation and supported public-library examples to the
  README without presenting internal modules as stable API.
- [ ] Document each extra and show minimal headless, desktop, REST, and MCP
  installations.
- [ ] Add a complete CLI file example and native executable locations.
- [ ] Add a full REST validate/submit/poll/result example.
- [ ] Make `optees-mcp --help` return bounded command help before starting the
  stdio protocol; normal MCP stdout remains protocol-only.
- [ ] Keep English and Italian user-visible documentation aligned where both
  variants exist.

**Gate `DIST-DOC`:** a clean user can choose an installation profile and run
its first validated operation without reading source code.

## Stop Conditions

Stop and return to contract review if dependency splitting creates different
capability behavior, the wheel omits runtime assets, an entry point imports Qt
in a headless profile, a package name is not demonstrably controlled, or a
release would require mutable replacement of an existing published version.

## Completion Standard

This roadmap is complete when clean environments install the declared profiles,
the core profile excludes PySide6, native packages include the CLI, published
Python artifacts match the application version and checksums, and documentation
describes only tested public entry points.
